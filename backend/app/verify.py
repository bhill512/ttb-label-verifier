import time

import numpy as np

from .matching.alcohol import check_alcohol
from .matching.bold import check_heading_bold
from .matching.net_contents import check_net_contents
from .matching.text import LabelText, squash
from .matching.text_fields import check_text
from .matching.warning import check_warning
from .ocr import TextExtractor, TextLine
from .schemas import ApplicationData, FieldResult, Status, VerificationResult, Verdict

# Below these the OCR output is too thin to trust, and a "mismatch" would
# really mean "couldn't read it".
MIN_CONFIDENCE = 0.6
MIN_CHARACTERS = 15

_TEXT_FIELDS = [
    ("brand_name", "Brand name"),
    ("class_type", "Class / type"),
    ("bottler", "Bottler / producer"),
    ("country_of_origin", "Country of origin"),
]
_DISPLAY_ORDER = [
    "brand_name",
    "class_type",
    "alcohol_content",
    "net_contents",
    "bottler",
    "country_of_origin",
    "warning_wording",
    "warning_capitals",
    "warning_bold",
]


def _check_fields(
    image: np.ndarray, lines: list[TextLine], application: ApplicationData
) -> list[FieldResult]:
    label = LabelText([line.text for line in lines])

    results = check_warning(label)
    if len(results) > 1:  # a warning was found, so its heading can be measured
        results.append(check_heading_bold(image, lines))

    # Longest first, so the bottler's address claims its text before the brand
    # name (which it often contains) goes looking.
    provided = [(key, title, getattr(application, key).strip()) for key, title in _TEXT_FIELDS]
    provided = [field for field in provided if field[2]]
    for key, title, expected in sorted(provided, key=lambda f: len(squash(f[2])[0]), reverse=True):
        results.append(check_text(label, key, title, expected))

    if application.alcohol_content.strip():
        results.append(check_alcohol(label.raw, application.alcohol_content.strip()))
    if application.net_contents.strip():
        results.append(check_net_contents(label.raw, application.net_contents.strip()))

    return sorted(results, key=lambda result: _DISPLAY_ORDER.index(result.key))


def _verdict(fields: list[FieldResult]) -> tuple[Verdict, str]:
    problems = sum(f.status in (Status.MISMATCH, Status.NOT_FOUND) for f in fields)
    reviews = sum(f.status is Status.REVIEW for f in fields)
    if problems:
        return Verdict.FAIL, f"{problems} problem{'s' if problems != 1 else ''} found."
    if reviews:
        return Verdict.REVIEW, f"{reviews} item{'s' if reviews != 1 else ''} to check by eye."
    return Verdict.PASS, "Everything on the label matches the application."


def verify_label(
    image: np.ndarray, application: ApplicationData, extractor: TextExtractor
) -> VerificationResult:
    started = time.perf_counter()
    lines = extractor.extract(image)
    characters = sum(len(squash(line.text)[0]) for line in lines)
    confidence = sum(line.confidence for line in lines) / len(lines) if lines else 0.0

    fields = _check_fields(image, lines, application)
    if characters < MIN_CHARACTERS or confidence < MIN_CONFIDENCE:
        verdict = Verdict.UNREADABLE
        summary = "The label could not be read clearly. Ask for a better image."
    else:
        verdict, summary = _verdict(fields)

    return VerificationResult(
        verdict=verdict,
        summary=summary,
        fields=fields,
        extracted_text=[line.text for line in lines],
        ocr_confidence=round(confidence, 3),
        elapsed_ms=round((time.perf_counter() - started) * 1000),
    )
