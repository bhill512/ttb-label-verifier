"""The Government Health Warning Statement (27 CFR 16.21).

Unlike the other fields this is not compared with the application: every label
must carry this exact wording, with the heading in capital letters and bold.
"""

from rapidfuzz.distance import Levenshtein

from ..schemas import FieldResult, Status
from .text import Hit, LabelText, squash

HEADING = "GOVERNMENT WARNING:"
STATEMENT = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not "
    "drink alcoholic beverages during pregnancy because of the risk of birth "
    "defects. (2) Consumption of alcoholic beverages impairs your ability to "
    "drive a car or operate machinery, and may cause health problems."
)

# A handful of differing characters is more likely a misread than a rewrite,
# so it goes to the agent instead of being failed outright.
MISREAD_CHARACTERS = 4
MISREAD_CAPITALS = 2

_HEADING_SCORE = 85.0
_WORDS = STATEMENT.split()
_SQUASHED = squash(STATEMENT)[0]
_ENDING = squash("health problems")[0]


def _word_at(position: int) -> int:
    """Index of the required word that a squashed character position falls in."""
    end = 0
    for i, word in enumerate(_WORDS):
        end += len(squash(word)[0])
        if position < end:
            return i
    return len(_WORDS) - 1


def _differing_phrases(on_label: str) -> list[str]:
    """The parts of the required statement that the label does not reproduce."""
    changed: set[int] = set()
    for op in Levenshtein.opcodes(_SQUASHED, on_label):
        if op.tag == "equal":
            continue
        last = max(op.src_start, op.src_end - 1)
        changed.update(range(_word_at(op.src_start), _word_at(last) + 1))

    phrases: list[list[int]] = []
    for i in sorted(changed):
        if phrases and i == phrases[-1][-1] + 1:
            phrases[-1].append(i)
        else:
            phrases.append([i])
    return [" ".join(_WORDS[i] for i in run) for run in phrases]


def _check_wording(label: LabelText, heading: Hit) -> tuple[FieldResult, Hit]:
    ending = label.squashed.find(_ENDING, heading.start)
    if 0 <= ending - heading.start <= 1.5 * len(_SQUASHED):
        end = ending + len(_ENDING)
    else:
        end = min(len(label.squashed), heading.start + len(_SQUASHED))
    on_label = label.squashed[heading.start : end]
    found = label.raw_span(heading.start, end, whole_words=True)
    span = Hit(100.0, heading.start, end, found)

    distance = Levenshtein.distance(_SQUASHED, on_label)
    if distance == 0:
        status, note = Status.MATCH, "Word-for-word match with the required statement."
    else:
        phrases = _differing_phrases(on_label)
        where = "; ".join(f'"{phrase}"' for phrase in phrases[:3])
        if len(phrases) > 3:
            where += "; and more"
        if distance <= MISREAD_CHARACTERS:
            status = Status.REVIEW
            note = f"Almost word-for-word. Please check the label at: {where}."
        else:
            status = Status.MISMATCH
            note = f"Wording differs from the required statement at: {where}."

    result = FieldResult(
        key="warning_wording",
        title="Government warning wording",
        status=status,
        expected=STATEMENT,
        found=found,
        note=note,
    )
    return result, span


def _check_capitals(heading_text: str) -> FieldResult:
    lowercase = sum(ch.islower() for ch in heading_text)
    if lowercase == 0:
        status, note = Status.MATCH, "Heading is in capital letters."
    elif lowercase <= MISREAD_CAPITALS:
        status = Status.REVIEW
        note = "Heading looks mostly capitalised. Please check it is all capital letters."
    else:
        status = Status.MISMATCH
        note = 'Heading must be in capital letters: "GOVERNMENT WARNING:".'
    return FieldResult(
        key="warning_capitals",
        title="Warning heading in capitals",
        status=status,
        expected=HEADING,
        found=heading_text,
        note=note,
    )


def check_warning(label: LabelText) -> list[FieldResult]:
    """Check the warning's wording and heading capitalisation, and claim its text."""
    heading = label.find("GOVERNMENT WARNING", min_score=_HEADING_SCORE)
    if heading is None:
        return [
            FieldResult(
                key="warning_wording",
                title="Government warning wording",
                status=Status.NOT_FOUND,
                expected=STATEMENT,
                note="No government warning statement found on the label.",
            )
        ]
    wording, span = _check_wording(label, heading)
    label.claim(span)
    return [wording, _check_capitals(label.raw_span(heading.start, heading.end))]
