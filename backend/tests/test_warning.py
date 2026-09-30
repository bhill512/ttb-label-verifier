from app.matching.text import LabelText
from app.matching.warning import STATEMENT, check_warning
from app.schemas import Status


def check(text: str) -> dict:
    return {result.key: result for result in check_warning(LabelText(text.split("\n")))}


def test_exact_statement_passes():
    results = check("OLD TOM\n" + STATEMENT)
    assert results["warning_wording"].status is Status.MATCH
    assert results["warning_capitals"].status is Status.MATCH


def test_line_breaks_and_dropped_spaces_do_not_matter():
    ocr = (
        "GOVERNMENTWARNING:(1)According to theSurgeon General,women\n"
        "shouldnot drink alcoholicbeveragesduring pregnancybecauseof theriskof\n"
        "birth defects.(2) Consumption of alcoholicbeverages impairs your ability to\n"
        "drivea car oroperatemachinery.and may cause health problems."
    )
    assert check(ocr)["warning_wording"].status is Status.MATCH


def test_statement_printed_entirely_in_capitals_passes():
    assert check(STATEMENT.upper())["warning_wording"].status is Status.MATCH


def test_title_case_heading_is_rejected():
    results = check(STATEMENT.replace("GOVERNMENT WARNING", "Government Warning"))
    assert results["warning_capitals"].status is Status.MISMATCH
    assert results["warning_capitals"].found == "Government Warning"
    assert results["warning_wording"].status is Status.MATCH


def test_changed_wording_is_rejected_and_located():
    result = check(STATEMENT.replace("should not drink", "should limit"))["warning_wording"]
    assert result.status is Status.MISMATCH
    assert "not drink" in result.note


def test_missing_sentence_is_rejected():
    shortened = STATEMENT.split(" (2)")[0]
    assert check(shortened + "\nBottled in Kentucky")["warning_wording"].status is Status.MISMATCH


def test_single_character_difference_goes_to_review():
    result = check(STATEMENT.replace("machinery", "machinory"))["warning_wording"]
    assert result.status is Status.REVIEW
    assert "machinery" in result.note


def test_missing_warning():
    results = check("HARBOR LIGHT\nIndia Pale Ale\n12 FL OZ")
    assert list(results) == ["warning_wording"]
    assert results["warning_wording"].status is Status.NOT_FOUND


def test_text_after_the_statement_is_ignored():
    assert check(STATEMENT + "\nCONTAINS SULFITES")["warning_wording"].status is Status.MATCH
