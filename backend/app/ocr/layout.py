import math
from statistics import median

from .base import TextLine


def _height(line: TextLine) -> float:
    return math.dist(line.box[0], line.box[3])


def reading_order(lines: list[TextLine]) -> list[TextLine]:
    """Sort lines top-to-bottom, left-to-right, allowing for a tilted photo.

    Sorting on raw y-coordinates scrambles the order when the label is rotated,
    so positions are first rotated back by the median text angle.
    """
    if len(lines) < 2:
        return lines

    angle = median(
        math.atan2(line.box[1][1] - line.box[0][1], line.box[1][0] - line.box[0][0])
        for line in lines
    )
    cos, sin = math.cos(-angle), math.sin(-angle)

    def position(line: TextLine) -> tuple[float, float]:
        x = sum(p[0] for p in line.box) / 4
        y = sum(p[1] for p in line.box) / 4
        return (x * sin + y * cos, x * cos - y * sin)

    same_row = 0.6 * median(_height(line) for line in lines)
    placed = sorted(((position(line), line) for line in lines), key=lambda item: item[0][0])

    rows: list[list[tuple[tuple[float, float], TextLine]]] = [[placed[0]]]
    for item in placed[1:]:
        if item[0][0] - rows[-1][0][0][0] <= same_row:
            rows[-1].append(item)
        else:
            rows.append([item])
    return [line for row in rows for _, line in sorted(row, key=lambda item: item[0][1])]
