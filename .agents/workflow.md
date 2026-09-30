# Workflow

Requires `uv` and Node.js 20+. Commands run from the repo root unless noted.

## Run

```bash
cd frontend && npm install && npm run build && cd ..
uv run --project backend uvicorn app.main:app --app-dir backend --port 8000
```

Open http://localhost:8000. The server has no auto-reload: restart it after
backend changes. Frontend changes need `npm run build`, or run `npm run dev` in
`frontend/` for hot reload (it proxies `/api` and `/samples` to port 8000).

## Test

```bash
cd backend && uv run pytest
```

About 35 seconds. `test_api.py` runs real OCR over every sample and asserts the
verdict and a sub-5-second time. The frontend has no tests; `npm run build`
type-checks it.

## Docker

```bash
docker build -t ttb-label-verifier .
docker run -p 8000:8000 ttb-label-verifier
```

Published as `bhill512/ttb-label-verifier` on Docker Hub (pushed by hand).

## Samples

```bash
uv run --project backend python tools/generate_samples.py
```

Rewrites the images and `samples/applications.csv`. To add a case, append a
`Sample` to `SAMPLES` in that script with its `expected_verdict`; the tests and
the UI dropdown pick it up automatically. Fonts come from the OS, so images
differ slightly between Windows and Linux.

## Conventions

- American spelling in everything we write: UI text, docs, comments, names.
  (Labels themselves may use either; the matcher accepts both.)
- UI and error text is plain English for non-technical users.
- Python: type hints, small modules, comments only where the reason is not
  obvious. Thresholds are named constants at the top of each module.
- Commit with a `Co-Authored-By` line when an AI agent wrote the change.
- Do not push or deploy without the user asking.
