import pytest

from app.matching.net_contents import check_net_contents, parse_quantities
from app.schemas import Status


@pytest.mark.parametrize(
    ("text", "milliliters"),
    [
        ("750 mL", 750),
        ("750ML", 750),
        ("75 cL", 750),
        ("1 L", 1000),
        ("1.75 Liters", 1750),
        ("1 Litre", 1000),
        ("0,7 l", 700),
        ("12 FL OZ", 354.882),
        ("12 fl. oz.", 354.882),
        ("1 Pint", 473.176),
    ],
)
def test_units_convert_to_milliliters(text, milliliters):
    assert parse_quantities(text)[0].milliliters == pytest.approx(milliliters)


def test_numbers_without_a_volume_unit_are_not_quantities():
    text = "45% Alc./Vol. (90 Proof) (1) According to the Surgeon General (2) Consumption"
    assert parse_quantities(text) == []


def test_same_volume_same_units():
    result = check_net_contents("OLD TOM 750mL", "750 mL")
    assert result.status is Status.MATCH
    assert result.note == "Net contents match."


def test_same_volume_different_units():
    result = check_net_contents("750 mL", "75 cL")
    assert result.status is Status.MATCH
    assert "different units" in result.note


def test_metric_and_us_measures_within_rounding():
    assert check_net_contents("25.4 FL OZ", "750 mL").status is Status.MATCH


def test_different_volume():
    result = check_net_contents("700 mL", "750 mL")
    assert result.status is Status.MISMATCH
    assert result.found == "700 mL"


def test_no_volume_on_label():
    assert check_net_contents("OLD TOM DISTILLERY", "750 mL").status is Status.NOT_FOUND
