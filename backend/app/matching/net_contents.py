import re
from dataclasses import dataclass

from ..schemas import FieldResult, Status

KEY, TITLE = "net_contents", "Net contents"

# Unit pattern -> millilitres. Litre comes last so "l" never shadows a longer unit.
_UNITS = [
    (r"ml|millilit(?:er|re)s?", 1.0),
    (r"cl|centilit(?:er|re)s?", 10.0),
    (r"fl\.?\s*oz\.?|fluid\s*ounces?|oz\.?", 29.5735),
    (r"pints?|pt\.?", 473.176),
    (r"quarts?|qt\.?", 946.353),
    (r"gallons?|gal\.?", 3785.41),
    (r"lit(?:er|re)s?|l", 1000.0),
]
_QUANTITY = re.compile(
    r"(?<![\d.,])(\d+(?:[.,]\d+)?)\s*(" + "|".join(unit for unit, _ in _UNITS) + r")(?![a-z])",
    re.IGNORECASE,
)

# Allows for rounding between metric and US measures (750 mL is 25.4 fl oz).
_TOLERANCE = 0.01


@dataclass(frozen=True)
class Quantity:
    text: str
    millilitres: float


def parse_quantities(text: str) -> list[Quantity]:
    quantities = []
    for match in _QUANTITY.finditer(text):
        per_unit = next(
            ml for unit, ml in _UNITS if re.fullmatch(unit, match.group(2), re.IGNORECASE)
        )
        amount = float(match.group(1).replace(",", "."))
        quantities.append(Quantity(" ".join(match.group(0).split()), amount * per_unit))
    return quantities


def _result(status: Status, expected: str, note: str, found: str | None = None) -> FieldResult:
    return FieldResult(
        key=KEY, title=TITLE, status=status, expected=expected, found=found, note=note
    )


def check_net_contents(label_text: str, expected: str) -> FieldResult:
    """Compare the volume on the label with the application, converting units."""
    wanted = parse_quantities(expected)
    if not wanted:
        return _result(
            Status.REVIEW, expected, "Could not read a volume from the application value."
        )
    target = wanted[0]

    on_label = parse_quantities(label_text)
    if not on_label:
        return _result(Status.NOT_FOUND, expected, "No volume found on the label.")

    for quantity in on_label:
        if abs(quantity.millilitres - target.millilitres) <= _TOLERANCE * target.millilitres:
            same_units = quantity.text.replace(" ", "").lower() == target.text.replace(" ", "").lower()
            note = "Net contents match." if same_units else "Same volume in different units."
            return _result(Status.MATCH, expected, note, quantity.text)

    shown = ", ".join(quantity.text for quantity in on_label)
    return _result(
        Status.MISMATCH,
        expected,
        f"Label shows {shown} but the application says {target.text}.",
        found=shown,
    )
