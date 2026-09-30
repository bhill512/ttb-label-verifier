import os

import pytest

from app.ocr import rapid


@pytest.fixture
def cgroup(monkeypatch, tmp_path):
    """A 16-core host with no pinning and no container limit; returns the
    directory holding the (initially absent) fake cgroup files."""
    monkeypatch.delenv("OCR_THREADS", raising=False)
    monkeypatch.setattr(os, "cpu_count", lambda: 16)
    monkeypatch.setattr(os, "sched_getaffinity", lambda _: set(range(16)), raising=False)
    monkeypatch.setattr(rapid, "_CGROUP_V2_CPU_MAX", tmp_path / "cpu.max")
    monkeypatch.setattr(rapid, "_CGROUP_V1_QUOTA", tmp_path / "cpu.cfs_quota_us")
    monkeypatch.setattr(rapid, "_CGROUP_V1_PERIOD", tmp_path / "cpu.cfs_period_us")
    return tmp_path


def test_unrestricted_host_leaves_the_default(cgroup):
    assert rapid.cpu_limit() is None


def test_unlimited_container_leaves_the_default(cgroup):
    (cgroup / "cpu.max").write_text("max 100000\n")
    assert rapid.cpu_limit() is None
    (cgroup / "cpu.max").unlink()
    (cgroup / "cpu.cfs_quota_us").write_text("-1\n")
    (cgroup / "cpu.cfs_period_us").write_text("100000\n")
    assert rapid.cpu_limit() is None


@pytest.mark.parametrize(
    ("cpu_max", "expected"),
    [("200000 100000", 2), ("150000 100000", 2), ("10000 100000", 1)],
)
def test_cgroup_v2_quota_is_honored(cgroup, cpu_max, expected):
    (cgroup / "cpu.max").write_text(cpu_max + "\n")
    assert rapid.cpu_limit() == expected


def test_cgroup_v1_quota_is_honored(cgroup):
    (cgroup / "cpu.cfs_quota_us").write_text("200000\n")
    (cgroup / "cpu.cfs_period_us").write_text("100000\n")
    assert rapid.cpu_limit() == 2


def test_cpu_pinning_is_honored(cgroup, monkeypatch):
    monkeypatch.setattr(os, "sched_getaffinity", lambda _: {0, 1, 2, 3}, raising=False)
    assert rapid.cpu_limit() == 4


def test_environment_override_wins(cgroup, monkeypatch):
    (cgroup / "cpu.max").write_text("200000 100000\n")
    monkeypatch.setenv("OCR_THREADS", "6")
    assert rapid.cpu_limit() == 6
