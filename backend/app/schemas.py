from enum import Enum

from pydantic import BaseModel


class Status(str, Enum):
    MATCH = "match"
    REVIEW = "review"
    MISMATCH = "mismatch"
    NOT_FOUND = "not_found"


class Verdict(str, Enum):
    PASS = "pass"
    REVIEW = "review"
    FAIL = "fail"
    UNREADABLE = "unreadable"


class ApplicationData(BaseModel):
    """What the applicant entered on the form. Blank fields are not checked."""

    brand_name: str
    class_type: str = ""
    alcohol_content: str = ""
    net_contents: str = ""
    bottler: str = ""
    country_of_origin: str = ""


class FieldResult(BaseModel):
    key: str
    title: str
    status: Status
    expected: str
    found: str | None = None
    note: str


class VerificationResult(BaseModel):
    verdict: Verdict
    summary: str
    fields: list[FieldResult]
    extracted_text: list[str]
    ocr_confidence: float
    elapsed_ms: int
