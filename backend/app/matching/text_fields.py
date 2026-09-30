from ..schemas import FieldResult, Status
from .text import LabelText


def check_text(label: LabelText, key: str, title: str, expected: str) -> FieldResult:
    """Check a free-text field (brand, class/type, bottler, country) against the label."""
    expected = " ".join(expected.split())
    hit = label.find(expected)

    if hit is None:
        return FieldResult(
            key=key,
            title=title,
            status=Status.NOT_FOUND,
            expected=expected,
            note="Not found on the label.",
        )

    label.claim(hit)
    if not hit.exact:
        return FieldResult(
            key=key,
            title=title,
            status=Status.REVIEW,
            expected=expected,
            found=hit.text,
            note="Close to the application but not the same. Please compare.",
        )

    note = (
        "Matches the application exactly."
        if hit.text == expected
        else "Same wording as the application. Only capitalisation, spacing or punctuation differs."
    )
    return FieldResult(
        key=key, title=title, status=Status.MATCH, expected=expected, found=hit.text, note=note
    )
