from dataclasses import dataclass
from typing import Protocol

import numpy as np

Point = tuple[float, float]


@dataclass(frozen=True)
class TextLine:
    text: str
    confidence: float
    box: tuple[Point, Point, Point, Point]  # corners, clockwise from top-left


class TextExtractor(Protocol):
    """Reads the text off a label image.

    The verifier only depends on this interface, so the bundled local OCR model
    can be swapped for another engine (for example a vision model hosted inside
    the agency's own network) without touching the matching rules.
    """

    def extract(self, image: np.ndarray) -> list[TextLine]:
        """Return the text lines found in a BGR image, in reading order."""
        ...
