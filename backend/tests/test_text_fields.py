from app.matching.text import LabelText
from app.matching.text_fields import check_text
from app.schemas import Status


def check(lines: list[str], expected: str):
    return check_text(LabelText(lines), "brand_name", "Brand name", expected)


def test_capitalisation_difference_is_a_match():
    result = check(["STONE'S THROW", "London Dry Gin"], "Stone's Throw")
    assert result.status is Status.MATCH
    assert result.found == "STONE'S THROW"
    assert "capitalisation" in result.note


def test_identical_text_is_reported_as_exact():
    result = check(["Old Tom Distillery"], "Old Tom Distillery")
    assert result.status is Status.MATCH
    assert "exactly" in result.note


def test_brand_split_across_lines_with_dropped_spaces():
    # OCR often returns "OLDTOM" for "OLD TOM" and puts each line separately.
    assert check(["OLDTOM", "DISTILLERY"], "Old Tom Distillery").status is Status.MATCH


def test_curly_apostrophe_and_accents():
    assert check(["STONE’S THROW"], "Stone's Throw").status is Status.MATCH
    assert check(["CHÂTEAU LUMIÈRE"], "Chateau Lumiere").status is Status.MATCH


def test_near_miss_goes_to_review_with_what_the_label_says():
    result = check(["BLUE HERRON", "Small Batch Rum"], "Blue Heron")
    assert result.status is Status.REVIEW
    assert result.found == "BLUE HERRON"


def test_different_brand_is_not_found():
    assert check(["SILVER CREEK", "Vodka"], "Old Tom Distillery").status is Status.NOT_FOUND


def test_text_claimed_by_one_field_cannot_satisfy_another():
    # The brand on the front is wrong; the correct name only appears in the address.
    label = LabelText(["BLUE HERRON", "Bottled by Blue Heron Rum Company, Charleston"])
    bottler = check_text(label, "bottler", "Bottler", "Blue Heron Rum Company, Charleston")
    brand = check_text(label, "brand_name", "Brand name", "Blue Heron")
    assert bottler.status is Status.MATCH
    assert brand.status is Status.REVIEW
