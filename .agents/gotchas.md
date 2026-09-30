# Gotchas

Things that cost time once already.

## OCR

- **Spaces go missing.** RapidOCR returns "OLDTOM" and
  "KentuckyStraightBourbon". Never compare on words or whitespace; use the
  squashed form from `matching/text.py`. Regexes on raw text must allow `\s*`.
- **Punctuation is unreliable.** Commas become periods. Nothing fails on
  punctuation; warning punctuation is deliberately not checked.
- **The 180° classifier is off** (`use_cls=False` in `ocr/rapid.py`). Turned
  on, it misjudges long lines of small print and whole lines of the warning
  vanish. Upside-down images are therefore unsupported.
- **Timing is noisy.** About 2 seconds typically, spikes to 4–5 on a busy
  machine. The first call is slow, so `main.py` warms the model up.

## Matching

- **Whole-label search.** Fields are found anywhere on the label, not by
  position. Claiming is what stops a wrong brand passing because the right
  name appears in the bottler line. Keep the longest-first order.
- **Alcohol context stops at the next "%".** Widening it makes "100% Agave"
  count as alcohol content.
- **Bold needs body text on the heading's line.** A heading alone on its line
  gives no ratio and the result is `review`.
- **Liter is last in `_UNITS`** so a bare "l" never shadows a longer unit.
- **Spelling variants never apply to the warning.** It has one legal wording.

- **Spelling folding works on squashed text,** so a variant can match across
  a word boundary. Keep `SPELLING_VARIANTS` to distinctive stems.

## Known gaps

Only synthetic labels have been tested. Type size, placement and
beverage-specific rules are not checked. Read "Trade-offs and limitations" in
the root README before claiming anything works on real labels.
