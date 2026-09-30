import math
import os
import threading
from pathlib import Path

import numpy as np
from rapidocr_onnxruntime import RapidOCR

from .base import TextLine
from .layout import reading_order

_CGROUP_V2_CPU_MAX = Path("/sys/fs/cgroup/cpu.max")
_CGROUP_V1_QUOTA = Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
_CGROUP_V1_PERIOD = Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us")


def _container_cpu_quota() -> float | None:
    """The CPU allowance set on this container (e.g. `docker run --cpus 2`), if any."""
    try:
        quota, period = _CGROUP_V2_CPU_MAX.read_text().split()
    except (OSError, ValueError):
        try:
            quota, period = _CGROUP_V1_QUOTA.read_text(), _CGROUP_V1_PERIOD.read_text()
        except OSError:
            return None
    try:
        return int(quota) / int(period) if int(quota) > 0 else None
    except ValueError:  # cgroup v2 writes "max" for no limit
        return None


def cpu_limit() -> int | None:
    """How many CPUs this process is restricted to, or None if unrestricted.

    ONNX Runtime sizes its thread pool from the host's core count. In a
    container limited to fewer CPUs, those threads fight over the allowance and
    OCR runs up to ten times slower, so the limit is worked out here and passed
    on. `OCR_THREADS` overrides the detection.
    """
    override = os.environ.get("OCR_THREADS", "")
    if override.isdigit() and int(override) > 0:
        return int(override)

    total = os.cpu_count() or 1
    allowed = total
    if hasattr(os, "sched_getaffinity"):  # Linux: honors CPU pinning
        allowed = len(os.sched_getaffinity(0))
    quota = _container_cpu_quota()
    if quota is not None:
        allowed = min(allowed, max(1, math.ceil(quota)))
    return allowed if allowed < total else None


class RapidOcrExtractor:
    """Local OCR (PP-OCR models on ONNX Runtime).

    The models ship inside the Python package and run on CPU, so reading a
    label makes no network calls.
    """

    def __init__(self) -> None:
        threads = cpu_limit()
        thread_options = (
            {} if threads is None else {"intra_op_num_threads": threads, "inter_op_num_threads": 1}
        )
        # The 180-degree classifier is off: it misjudges long lines of small
        # print (such as the government warning) and they are then dropped.
        self._engine = RapidOCR(use_cls=False, **thread_options)
        self._lock = threading.Lock()

    def extract(self, image: np.ndarray) -> list[TextLine]:
        with self._lock:
            result, _ = self._engine(image)
        lines = [
            TextLine(
                text=text.strip(),
                confidence=float(score),
                box=tuple((float(x), float(y)) for x, y in box),
            )
            for box, text, score in result or []
            if text.strip()
        ]
        return reading_order(lines)
