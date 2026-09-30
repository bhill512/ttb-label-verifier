"""Estimate whether the "GOVERNMENT WARNING:" heading is printed in bold.

OCR returns characters, not font weight, so this measures it from the pixels:
the stroke thickness of the heading is compared with the body text that follows
it on the same line. It is a heuristic, so it can confirm bold but never fails
a label on its own; anything short of a clear result goes to the agent.
"""

import math
from collections.abc import Sequence

import cv2
import numpy as np

from ..ocr.base import TextLine
from ..schemas import FieldResult, Status
from .text import squash
from .warning import HEADING

# Heading strokes this much thicker than the body text count as bold.
BOLD_RATIO = 1.25

_CROP_HEIGHT = 96
_MIN_INK_PIXELS = 50


def _straighten(image: np.ndarray, line: TextLine) -> np.ndarray:
    """Cut a text line out of the image as an upright greyscale strip."""
    top_left, top_right, _, bottom_left = line.box
    width = math.dist(top_left, top_right)
    height = math.dist(top_left, bottom_left)
    out_width = max(1, round(width * _CROP_HEIGHT / max(height, 1)))
    target = np.float32([[0, 0], [out_width, 0], [out_width, _CROP_HEIGHT], [0, _CROP_HEIGHT]])
    transform = cv2.getPerspectiveTransform(np.float32(line.box), target)
    strip = cv2.warpPerspective(image, transform, (out_width, _CROP_HEIGHT), flags=cv2.INTER_CUBIC)
    return cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY)


def _stroke_width(ink: np.ndarray) -> float | None:
    """Typical stroke thickness: twice the distance from a stroke's centre to its edge."""
    if ink.sum() < _MIN_INK_PIXELS:
        return None
    distance = cv2.distanceTransform(ink.astype(np.uint8), cv2.DIST_L2, 5)
    centres = ink & (distance >= cv2.dilate(distance, np.ones((3, 3), np.uint8)))
    return 2 * float(np.median(distance[centres]))


def heading_stroke_ratio(image: np.ndarray, lines: Sequence[TextLine]) -> float | None:
    """Heading stroke thickness relative to the body text beside it, if measurable."""
    heading = squash(HEADING)[0]
    for line in lines:
        text, index = squash(line.text)
        at = text.find(heading)
        if at < 0:
            continue

        # Bold capitals are wider than the body text, so the heading takes up
        # more of the line than its share of characters. Sample well inside
        # each side of the estimated boundary.
        boundary = (index[at + len(heading) - 1] + 1) / len(line.text)
        strip = _straighten(image, line)
        _, binary = cv2.threshold(strip, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        ink = binary == 0 if (binary == 0).mean() < 0.5 else binary == 255

        width = strip.shape[1]
        heading_stroke = _stroke_width(ink[:, : int(width * boundary * 0.85)])
        body_stroke = _stroke_width(ink[:, int(width * min(1.0, boundary * 1.6)) :])
        if heading_stroke is None or body_stroke is None:
            return None
        return heading_stroke / body_stroke
    return None


def check_heading_bold(image: np.ndarray, lines: Sequence[TextLine]) -> FieldResult:
    ratio = heading_stroke_ratio(image, lines)
    if ratio is not None and ratio >= BOLD_RATIO:
        status, note = Status.MATCH, "Heading appears to be in bold."
    elif ratio is None:
        status, note = Status.REVIEW, "Could not tell whether the heading is bold. Please check by eye."
    else:
        status = Status.REVIEW
        note = "Heading does not look bolder than the text beside it. Please check by eye."
    return FieldResult(
        key="warning_bold",
        title="Warning heading in bold",
        status=status,
        expected="Bold",
        found=None if ratio is None else ("Looks bold" if ratio >= BOLD_RATIO else "Looks regular weight"),
        note=note,
    )
