# Architecture

One FastAPI process serves the API, samples and the built React UI.

## Layout

```
backend/app/main.py      Endpoints, upload validation, static mounts
backend/app/verify.py    Runs the checks, decides the verdict
backend/app/schemas.py   Status, Verdict, FieldResult, VerificationResult
backend/app/ocr/         Image loading, TextExtractor, RapidOCR wrapper
backend/app/matching/    One module per kind of check
backend/tests/           Unit tests per rule, end-to-end over samples
frontend/src/            SingleCheck, BatchCheck, ResultView, api, types
samples/                 10 labels + applications.csv (the golden set)
tools/                   generate_samples.py
```

## Endpoints

- `POST /api/verify`: multipart `image` plus form fields `brand_name`
  (required), `class_type`, `alcohol_content`, `net_contents`, `bottler`,
  `country_of_origin`.
- `GET /api/samples`: the manifest, for the "Try an example" dropdown.
- `GET /api/health`; `/samples/*` and `/` are static mounts.

## Request flow

1. `load_image` decodes, applies EXIF rotation, scales to 1600 px max.
2. `extractor.extract` runs OCR, returns `TextLine`s in reading order.
3. `verify._check_fields` builds a `LabelText` and runs each check.
4. `_verdict`: any mismatch or not-found is `fail`; else any review is
   `review`; else `pass`. Thin or low-confidence OCR is `unreadable`.

## Things to know

- One extractor is created at startup on `app.state`. It holds a lock, so OCR
  runs one label at a time.
- Batch has no server endpoint. The browser parses the CSV and calls
  `/api/verify` per row, two at a time.
- `frontend/src/types.ts` mirrors `schemas.py` by hand. Change both together.
- To swap OCR engines, implement `TextExtractor` (`ocr/base.py`).
