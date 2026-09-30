import pytest

from app.matching.alcohol import check_alcohol
from app.schemas import Status


@pytest.mark.parametrize(
    "label",
    [
        "45% Alc./Vol. (90 Proof)",
        "45%Alc.Vol. (90 Proof)",  # OCR dropped the spaces and the slash
        "ALC. 45% BY VOL.",
        "45.0 % ABV",
    ],
)
def test_matching_percentage(label):
    assert check_alcohol(label, "45% Alc./Vol. (90 Proof)").status is Status.MATCH


def test_application_value_can_be_a_bare_number():
    assert check_alcohol("13.5% Alc./Vol.", "13.5").status is Status.MATCH


def test_different_percentage_is_a_mismatch():
    result = check_alcohol("40% Alc./Vol. (80 Proof)", "45% Alc./Vol. (90 Proof)")
    assert result.status is Status.MISMATCH
    assert result.found == "40%"


def test_decimal_difference_is_a_mismatch():
    assert check_alcohol("13.5% Alc./Vol.", "13%").status is Status.MISMATCH


def test_missing_percentage():
    assert check_alcohol("OLD TOM DISTILLERY 750 mL", "45%").status is Status.NOT_FOUND


def test_other_percentages_on_the_label_are_ignored():
    label = "100% Blue Agave  40% Alc./Vol."
    assert check_alcohol(label, "40%").status is Status.MATCH
    assert check_alcohol(label, "100%").status is Status.MISMATCH


def test_proof_inconsistent_with_percentage_goes_to_review():
    assert check_alcohol("45% Alc./Vol. (80 Proof)", "45%").status is Status.REVIEW


def test_proof_differs_from_application():
    assert check_alcohol("45% Alc./Vol. (80 Proof)", "45% (90 Proof)").status is Status.MISMATCH


def test_unparseable_application_value_goes_to_review():
    assert check_alcohol("45% Alc./Vol.", "forty-five").status is Status.REVIEW
