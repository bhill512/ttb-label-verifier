import threading

import numpy as np
from rapidocr_onnxruntime import RapidOCR

from .base import TextLine
from .layout import reading_order


class RapidOcrExtractor:
    """Local OCR (PP-OCR models on ONNX Runtime).

    The models ship inside the Python package and run on CPU, so reading a
    label makes no network calls.
    """

    def __init__(self) -> None:
        # The 180-degree classifier is off: it misjudges long lines of small
        # print (such as the government warning) and they are then dropped.
        self._engine = RapidOCR(use_cls=False)
        self._lock = threading.Lock()

    def extract(self, image: np.ndarray) -> list[TextLine]:
        with self._lock:
            result, _ = self._engine(image)
        lines = [
            TextLine(
                text=text.strip(),
                confidence=float(score),
                box=tuple((float(x), float(y)) for x, y in box),
            )
            for box, text, score in result or []
            if text.strip()
        ]
        return reading_order(lines)
