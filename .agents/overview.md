# Overview

A take-home prototype for the TTB (US alcohol label regulator). A compliance
agent supplies the application data and a label image; the app reports, field by
field, whether the label matches.

## Constraints from the brief

These came from stakeholder interviews and drive most design choices. Do not
trade them away without asking the user.

- **About 5 seconds per label.** A previous tool at 30–40 seconds was abandoned.
- **No outbound calls.** The agency firewall blocks ML endpoints, so the core
  path uses no cloud APIs. The OCR models ship inside a Python package.
- **Usable by non-technical staff.** One screen, large type, plain words, no
  jargon in the UI or in error messages.
- **Judgment, not rigid matching.** "STONE'S THROW" equals "Stone's Throw",
  and British and American spellings are the same word. Uncertain cases go to
  the agent as "Check by eye", not as failures.
- **The government warning is strict.** Word-for-word, heading in capitals and bold.
- **Batch.** Importers submit 200–300 labels at once.
- **Nothing stored.** Images are processed in memory and discarded.

## What it is not

- There is no LLM and no custom-trained model. Reading the image uses an
  off-the-shelf OCR model (RapidOCR / PP-OCR); the comparison is plain code.
- There is no COLA integration, sign-in, database or audit trail.

## Status

- Runs locally and as a Docker container; both verified.
- Not pushed to GitHub and not deployed yet. Both are required deliverables.
- Tested only on the synthetic labels in `samples/`, never on real labels.

## Deliverables

Public GitHub repo (`bhill512/ttb-label-verifier`), a README covering setup,
approach, assumptions and limitations, and a deployed URL.
