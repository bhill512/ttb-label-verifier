# Matching rules

Statuses: `match`, `review`, `mismatch`, `not_found`. Blank application fields
are skipped. The warning is always checked.

## Text fields: brand, class/type, bottler, country

`matching/text.py`, `text_fields.py`

- Both sides are "squashed": lowercase letters and digits, accents removed.
- Squashed value found on the label: `match`.
- Else found after folding `SPELLING_VARIANTS` (flavour/flavor,
  whisky/whiskey...) on both sides: `match`, with a note. Lenient by design;
  ask the user before making it `review`.
- Else RapidFuzz partial ratio of 80+ (`REVIEW_SCORE`): `review`.
- Else `not_found`.
- A matched span is **claimed** and cannot satisfy another field. Fields run
  longest first, so the bottler's address is claimed before the brand searches.

## Alcohol content

`matching/alcohol.py`

- The percentage on each side must be equal.
- Prefers percentages next to "alc", "vol" or "abv"; "100% Agave" is ignored.
- Label proof differs from the application's: `mismatch`.
- Label proof is not twice the percentage: `review`.

## Net contents

`matching/net_contents.py`: converts to milliliters, 1% tolerance, so 750 mL
matches 75 cL.

## Government warning

`matching/warning.py`, `bold.py`. Up to three results.

- **Wording:** Levenshtein distance from the squashed 27 CFR 16.21 text.
  0 is `match`; 1–4 is `review`; more is `mismatch`. No warning at all is
  `not_found`, and the other two results are omitted.
- **Capitals:** lowercase letters in the heading. 0 is `match`; 1–2 is
  `review`; more is `mismatch`.
- **Bold:** heading stroke thickness versus body text on the same line.
  Ratio of 1.25+ is `match`; otherwise `review`. It never fails a label.

## Changing a rule

Update a unit test, then run the suite: every sample must keep its verdict.
