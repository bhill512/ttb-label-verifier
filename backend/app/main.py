import csv
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.staticfiles import StaticFiles

from .ocr import RapidOcrExtractor, UnreadableImage, load_image
from .schemas import ApplicationData, VerificationResult
from .verify import verify_label

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLES_DIR = REPO_ROOT / "samples"
FRONTEND_DIR = REPO_ROOT / "frontend" / "dist"

MAX_UPLOAD_BYTES = 15 * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    extractor = RapidOcrExtractor()
    # The first run loads the models; do it now so no agent waits for it.
    extractor.extract(np.full((64, 256, 3), 255, np.uint8))
    app.state.extractor = extractor
    yield


app = FastAPI(title="TTB Label Verifier", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/verify")
def verify(
    request: Request,
    image: Annotated[UploadFile, File()],
    brand_name: Annotated[str, Form()],
    class_type: Annotated[str, Form()] = "",
    alcohol_content: Annotated[str, Form()] = "",
    net_contents: Annotated[str, Form()] = "",
    bottler: Annotated[str, Form()] = "",
    country_of_origin: Annotated[str, Form()] = "",
) -> VerificationResult:
    """Check one label image against the application data entered for it."""
    if not brand_name.strip():
        raise HTTPException(422, "Enter the brand name from the application.")

    data = image.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "This image is too large. The limit is 15 MB.")
    try:
        pixels = load_image(data)
    except UnreadableImage:
        raise HTTPException(
            400, "This file could not be opened as an image. Use a JPG or PNG of the label."
        ) from None

    application = ApplicationData(
        brand_name=brand_name,
        class_type=class_type,
        alcohol_content=alcohol_content,
        net_contents=net_contents,
        bottler=bottler,
        country_of_origin=country_of_origin,
    )
    return verify_label(pixels, application, request.app.state.extractor)


@app.get("/api/samples")
def samples() -> list[dict]:
    """The bundled test labels, each with the application data to check it against."""
    manifest = SAMPLES_DIR / "applications.csv"
    if not manifest.exists():
        return []
    with open(manifest, newline="", encoding="utf-8") as f:
        return [
            {
                "filename": row["filename"],
                "url": f"/samples/{row['filename']}",
                "description": row["description"],
                "application": {key: row[key] for key in ApplicationData.model_fields},
            }
            for row in csv.DictReader(f)
        ]


if SAMPLES_DIR.exists():
    app.mount("/samples", StaticFiles(directory=SAMPLES_DIR), name="samples")
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
