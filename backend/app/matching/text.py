"""Searching OCR output for an expected piece of text.

OCR routinely drops spaces ("OLDTOM"), swaps punctuation and cannot be relied
on for curly versus straight apostrophes. Comparisons are therefore made on a
"squashed" form of the text: lowercase letters and digits only. That is also
what makes "STONE'S THROW" and "Stone's Throw" the same brand.
"""

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from rapidfuzz import fuzz

# Below an exact match, text this similar is shown to the agent to decide on.
REVIEW_SCORE = 80.0

_CLAIMED = "\x00"


def squash(text: str) -> tuple[str, list[int]]:
    """Return the letters and digits of `text`, lowercased and without accents,
    along with the position each kept character came from."""
    chars, index = [], []
    for i, ch in enumerate(text):
        base = unicodedata.normalize("NFKD", ch)[0].lower()
        if len(base) == 1 and base.isalnum():
            chars.append(base)
            index.append(i)
    return "".join(chars), index


@dataclass(frozen=True)
class Hit:
    score: float
    start: int  # positions in the squashed label text
    end: int
    text: str  # what the label actually says there

    @property
    def exact(self) -> bool:
        return self.score >= 100


class LabelText:
    """The text read from a label, searchable without regard to case or spacing."""

    def __init__(self, lines: Sequence[str]) -> None:
        self.raw = "\n".join(lines)
        self.squashed, self._index = squash(self.raw)
        self._unclaimed = self.squashed

    def find(self, expected: str, min_score: float = REVIEW_SCORE) -> Hit | None:
        """Best match for `expected` among text not yet claimed by another field."""
        needle, _ = squash(expected)
        if not needle:
            return None

        start = self._unclaimed.find(needle)
        if start >= 0:
            end = start + len(needle)
            return Hit(100.0, start, end, self.raw_span(start, end))

        close = fuzz.partial_ratio_alignment(needle, self._unclaimed, score_cutoff=min_score)
        if close is None or close.dest_end <= close.dest_start:
            return None
        text = self.raw_span(close.dest_start, close.dest_end, whole_words=True)
        return Hit(min(close.score, 99.9), close.dest_start, close.dest_end, text)

    def claim(self, hit: Hit) -> None:
        """Reserve a span so it cannot also satisfy another field.

        Without this a brand name that is wrong on the front of the label would
        still "match" because the same name appears in the bottler's address.
        """
        width = hit.end - hit.start
        self._unclaimed = self._unclaimed[: hit.start] + _CLAIMED * width + self._unclaimed[hit.end :]

    def raw_span(self, start: int, end: int, whole_words: bool = False) -> str:
        first, last = self._index[start], self._index[end - 1] + 1
        if whole_words:
            while first > 0 and not self.raw[first - 1].isspace():
                first -= 1
            while last < len(self.raw) and not self.raw[last].isspace():
                last += 1
        return " ".join(self.raw[first:last].split())
