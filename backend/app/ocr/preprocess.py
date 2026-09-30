import io

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

# Large phone photos are scaled down to this before OCR. It keeps small print
# legible while holding processing time well inside the 5 second target.
MAX_SIDE = 1600


class UnreadableImage(ValueError):
    """The upload is not an image we can open."""


def load_image(data: bytes) -> np.ndarray:
    """Decode an upload into an upright BGR array no larger than MAX_SIDE."""
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise UnreadableImage("This file could not be opened as an image.") from exc

    scale = MAX_SIDE / max(img.size)
    if scale < 1:
        img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
