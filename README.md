# TTB Label Verifier

A prototype that checks an alcohol label image against its application data and
tells a compliance agent, field by field, what matches, what doesn't, and what
they should look at themselves.

**Deployed URL:** not deployed yet (runs locally; see below).

## What it does

- **Check one label.** Type in the application details, choose the label image,
  press one button. The result is a checklist: brand name, class/type, alcohol
  content, net contents, bottler, country of origin, and the government warning.
- **Check many labels.** Choose a CSV of applications and all the label images
  at once. Labels are checked one after another with a progress bar; results can
  be filtered to the problems and downloaded as a CSV.
- **Try an example.** Ten sample labels are bundled, covering passes, failures
  and borderline cases, so the tool can be tried without any files to hand.

Each item gets one of four outcomes:

| Outcome | Meaning |
|---|---|
| Matches | The label agrees with the application (or the regulation). |
| Check by eye | Close, but not certain. The agent decides. |
| Does not match | The label says something different. |
| Not found | The item could not be found on the label. |

## Running it locally

You need [uv](https://docs.astral.sh/uv/) and Node.js 20 or newer.

```bash
cd frontend
npm install
npm run build
cd ..
uv run --project backend uvicorn app.main:app --app-dir backend --port 8000
```

Then open http://localhost:8000. The first start takes a few seconds while the
OCR models load.

To work on the UI with hot reload, keep the server above running and start
`npm run dev` in `frontend/` (it proxies API calls to port 8000).

### Tests

```bash
cd backend
uv run pytest
```

The suite covers the matching rules on their own and runs the real OCR over
every sample label, asserting both the verdict and that it came back in under
five seconds.

### Docker

A `Dockerfile` is included for deployment. It has not been built and tested yet.

```bash
docker build -t ttb-label-verifier .
docker run -p 8000:8000 ttb-label-verifier
```

## Approach

The design follows what the stakeholders said in the discovery notes.

| What they said | What the prototype does |
|---|---|
| "If we can't get results back in about 5 seconds, nobody's going to use it." | Text is read by a local OCR model on CPU. Sample labels take 1–3 seconds each on a 2017 8-core desktop. The time taken is shown with every result. |
| "Our network blocks outbound traffic to a lot of domains." | No cloud APIs. The OCR models ship inside the Python package and the app makes no outbound calls at run time. |
| "'STONE'S THROW' on the label but 'Stone's Throw' in the application... it's obviously the same thing." | Text is compared ignoring capitalisation, spacing, punctuation and accents. Near misses go to "Check by eye" instead of being failed. |
| "The warning statement... has to be exact. Word-for-word, and 'GOVERNMENT WARNING:' has to be in all caps and bold." | The warning is checked against the statutory text; the heading must be in capitals; bold is estimated from the image. |
| "Something my mother could figure out." | One screen, numbered steps, large type, one main button. Results use words and symbols as well as colour, and problems are listed first. |
| "Big importers dump 200, 300 label applications on us at once." | Batch mode: a CSV plus the images, with progress, filters and a CSV export. |
| "Images that aren't perfectly shot." | Photos are auto-rotated from camera metadata and tilted text is handled. A label that can't be read is reported as "Could not read the label", not as a failure. |
| "We're not storing anything sensitive." | Nothing is stored. Images are processed in memory and discarded. |

### How a label is checked

1. **Read.** The image is decoded, turned upright and scaled down, then passed
   to [RapidOCR](https://github.com/RapidAI/RapidOCR) (PP-OCR models on ONNX
   Runtime). Lines are put in reading order, allowing for a tilted photo.
2. **Compare.** Each field has its own rule in `backend/app/matching/`:
   - *Brand, class/type, bottler, country* — searched for anywhere on the label,
     ignoring case, spacing and punctuation. An identical match passes; a close
     one (80% similar or better) goes to the agent. Text that satisfies one field
     can't satisfy another, so a misspelt brand doesn't pass just because the
     right name appears in the bottler's address.
   - *Alcohol content* — the percentage is parsed from both sides and must be
     equal. If a proof is shown it must agree with the application and be twice
     the percentage.
   - *Net contents* — quantity and unit are parsed and converted, so 750 mL
     matches 75 cL.
   - *Government warning* — compared character by character with the text in
     27 CFR 16.21. Up to four differing characters is treated as a possible
     misread and sent to the agent, with the affected words named; more is a
     failure. The heading must be in capitals. Bold is estimated by comparing
     the stroke thickness of the heading with the body text beside it.
3. **Decide.** Any mismatch or missing item makes the label "Problems found";
   otherwise any "Check by eye" item makes it "Needs a closer look"; otherwise
   it passes.

The OCR engine sits behind a small interface (`TextExtractor`), so it can be
replaced, for example by a vision model hosted inside the agency's own Azure
tenant, without touching the rules.

## Tools used

- **Backend:** Python 3.12, FastAPI, RapidOCR (ONNX Runtime), OpenCV, RapidFuzz
- **Frontend:** React, TypeScript, Vite, PapaParse
- **Tests:** pytest
- **Test labels:** generated with Pillow by `tools/generate_samples.py`
- Built with the help of Claude Code.

## Project layout

```
backend/app/main.py        API endpoints
backend/app/verify.py      Runs the checks and decides the verdict
backend/app/ocr/           Image loading and text extraction
backend/app/matching/      One module per kind of check
backend/tests/             Unit tests and end-to-end tests over the samples
frontend/src/              React UI (single check, batch check, result view)
samples/                   Test labels and applications.csv
tools/generate_samples.py  Regenerates the samples
```

### Batch CSV format

One row per application. `filename` and `brand_name` are required; the rest are
optional and skipped when blank. `samples/applications.csv` is a working example.

```
filename,brand_name,class_type,alcohol_content,net_contents,bottler,country_of_origin
```

## Assumptions

- The application data is typed in or supplied as a CSV; there is no connection
  to COLA.
- A field left blank in the application is not checked. The government warning
  is always checked.
- The warning may be printed entirely in capitals; only the heading's
  capitalisation is enforced.
- "Matches" for text fields means the same letters and digits in the same order.
  Differences in capitalisation, spacing and punctuation are noted but accepted.
- Bold can't be determined with certainty from an image, so a heading that
  doesn't look bold is sent to the agent instead of being rejected.

## Trade-offs and limitations

- **Tested on synthetic labels only.** The samples are clean renders plus one
  simulated photo. Real labels with decorative fonts, curved bottles or busy
  artwork have not been tried and will read less reliably.
- **OCR drops some spaces.** The "On the label" text can show words run together
  ("OLDTOM"). Matching ignores spacing, so results are unaffected, but it looks
  odd.
- **Warning punctuation is not checked.** OCR confuses commas and full stops too
  often to fail a label on them.
- **Type size and placement are not checked.** Only wording, capitals and bold.
- **Upside-down images are not handled.** The OCR's 180° detector was dropping
  lines of small print, so it is switched off. Sideways phone photos with
  orientation metadata are fine.
- **The search is not layout-aware.** It confirms the brand name appears on the
  label, not that it is the most prominent text.
- **No beverage-specific rules.** For example, the alcohol content exemptions
  for some wines and beers are not modelled.
- **Batch speed.** Labels are read one at a time at about 2–3 seconds each, so
  300 labels take roughly 10–15 minutes. The batch runs from the browser;
  closing the tab stops it.
- **Prototype only.** No sign-in, no audit trail, no stored history.
