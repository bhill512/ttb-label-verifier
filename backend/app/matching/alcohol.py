import re

from ..schemas import FieldResult, Status

KEY, TITLE = "alcohol_content", "Alcohol content"

_NUMBER = r"(\d{1,3}(?:[.,]\d{1,2})?)"
_PERCENT = re.compile(_NUMBER + r"\s*%")
_BARE_NUMBER = re.compile(r"\s*" + _NUMBER + r"\s*")
_PROOF = re.compile(r"(\d{2,3}(?:\.\d+)?)\s*proof", re.IGNORECASE)
_ALCOHOL_WORDS = re.compile(r"alc|vol|abv", re.IGNORECASE)
_CONTEXT = 15


def _number(text: str) -> float:
    return float(text.replace(",", "."))


def _label_percentages(text: str) -> list[float]:
    """Percentages stated as alcohol content, or failing that any percentage."""
    found = []
    for m in _PERCENT.finditer(text):
        # Words either side of the figure, stopping short of any other percentage
        # so "100% Agave 40% Alc./Vol." credits "Alc." to the 40 only.
        before = text[max(0, m.start() - _CONTEXT) : m.start()].rpartition("%")[2]
        after = text[m.end() : m.end() + _CONTEXT].partition("%")[0]
        found.append((_number(m.group(1)), bool(_ALCOHOL_WORDS.search(before + " " + after))))
    stated_as_alcohol = [value for value, is_alcohol in found if is_alcohol]
    return stated_as_alcohol or [value for value, _ in found]


def _proofs(text: str) -> list[float]:
    return [float(m.group(1)) for m in _PROOF.finditer(text)]


def _result(status: Status, expected: str, note: str, found: str | None = None) -> FieldResult:
    return FieldResult(
        key=KEY, title=TITLE, status=status, expected=expected, found=found, note=note
    )


def check_alcohol(label_text: str, expected: str) -> FieldResult:
    """Compare the alcohol percentage (and proof, when shown) with the application."""
    match = _PERCENT.search(expected) or _BARE_NUMBER.fullmatch(expected)
    if match is None:
        return _result(
            Status.REVIEW, expected, "Could not read a percentage from the application value."
        )
    expected_abv = _number(match.group(1))

    on_label = _label_percentages(label_text)
    if not on_label:
        return _result(Status.NOT_FOUND, expected, "No alcohol percentage found on the label.")
    if expected_abv not in on_label:
        shown = ", ".join(f"{value:g}%" for value in on_label)
        return _result(
            Status.MISMATCH,
            expected,
            f"Label shows {shown} but the application says {expected_abv:g}%.",
            found=shown,
        )

    found = f"{expected_abv:g}%"
    label_proofs = _proofs(label_text)
    if not label_proofs:
        return _result(Status.MATCH, expected, "Alcohol percentage matches.", found)

    found += f" ({label_proofs[0]:g} proof)"
    expected_proofs = _proofs(expected)
    if expected_proofs and expected_proofs[0] not in label_proofs:
        return _result(
            Status.MISMATCH,
            expected,
            f"Percentage matches, but the label shows {label_proofs[0]:g} proof "
            f"and the application says {expected_proofs[0]:g} proof.",
            found,
        )
    if expected_abv * 2 not in label_proofs:
        return _result(
            Status.REVIEW,
            expected,
            f"Percentage matches, but {label_proofs[0]:g} proof is not twice {expected_abv:g}%.",
            found,
        )
    return _result(Status.MATCH, expected, "Alcohol percentage and proof match.", found)
