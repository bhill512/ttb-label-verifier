"""End-to-end checks: real OCR over the bundled sample labels."""

import csv

import pytest
from fastapi.testclient import TestClient

from app.main import SAMPLES_DIR, app
from app.schemas import ApplicationData

TARGET_SECONDS = 5

with open(SAMPLES_DIR / "applications.csv", newline="", encoding="utf-8") as f:
    SAMPLES = list(csv.DictReader(f))


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as client:
        yield client


def post_sample(client, row):
    form = {key: row[key] for key in ApplicationData.model_fields}
    with open(SAMPLES_DIR / row["filename"], "rb") as image:
        return client.post("/api/verify", data=form, files={"image": (row["filename"], image)})


@pytest.mark.parametrize("row", SAMPLES, ids=[row["filename"] for row in SAMPLES])
def test_sample_label_reaches_expected_verdict(client, row):
    response = post_sample(client, row)
    assert response.status_code == 200
    result = response.json()
    assert result["verdict"] == row["expected_verdict"], result["fields"]
    assert result["elapsed_ms"] < TARGET_SECONDS * 1000


def test_wrong_abv_is_reported_on_the_alcohol_field(client):
    row = next(r for r in SAMPLES if r["filename"] == "old_tom_wrong_abv.png")
    fields = {f["key"]: f for f in post_sample(client, row).json()["fields"]}
    assert fields["alcohol_content"]["status"] == "mismatch"
    assert fields["brand_name"]["status"] == "match"


def test_blank_application_fields_are_not_checked(client):
    with open(SAMPLES_DIR / "old_tom_bourbon.png", "rb") as image:
        response = client.post(
            "/api/verify", data={"brand_name": "Old Tom Distillery"}, files={"image": image}
        )
    keys = [f["key"] for f in response.json()["fields"]]
    assert keys == ["brand_name", "warning_wording", "warning_capitals", "warning_bold"]


def test_non_image_upload_gets_a_plain_error(client):
    response = client.post(
        "/api/verify",
        data={"brand_name": "Old Tom"},
        files={"image": ("notes.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400
    assert "could not be opened" in response.json()["detail"]


def test_blank_image_is_unreadable_not_a_failure(client):
    from io import BytesIO

    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", (600, 800), "white").save(buffer, "PNG")
    response = client.post(
        "/api/verify",
        data={"brand_name": "Old Tom"},
        files={"image": ("blank.png", buffer.getvalue(), "image/png")},
    )
    assert response.json()["verdict"] == "unreadable"


def test_samples_endpoint_lists_the_manifest(client):
    listed = client.get("/api/samples").json()
    assert len(listed) == len(SAMPLES)
    assert listed[0]["application"]["brand_name"] == SAMPLES[0]["brand_name"]
