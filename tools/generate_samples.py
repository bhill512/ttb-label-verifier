"""Generate the synthetic test labels in samples/ and their application manifest.

Each sample pairs a label image with the application data an agent would be
checking it against, plus the verdict the verifier is expected to reach. The
manifest (samples/applications.csv) doubles as the golden set for the tests,
the "try a sample" list in the UI, and an example batch upload file.

Run from the repo root:  uv run --project backend python tools/generate_samples.py
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).resolve().parents[1] / "samples"

WIDTH, HEIGHT, MARGIN = 1000, 1300, 80

WARNING_HEADER = "GOVERNMENT WARNING:"
WARNING_BODY = (
    "(1) According to the Surgeon General, women should not drink alcoholic "
    "beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car "
    "or operate machinery, and may cause health problems."
)

FONT_DIRS = [
    Path("C:/Windows/Fonts"),
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/System/Library/Fonts/Supplemental"),
]
FONT_FILES = {
    "serif_bold": ["georgiab.ttf", "DejaVuSerif-Bold.ttf", "Georgia Bold.ttf"],
    "serif_italic": ["georgiai.ttf", "DejaVuSerif-Italic.ttf", "Georgia Italic.ttf"],
    "sans": ["arial.ttf", "DejaVuSans.ttf", "Arial.ttf"],
    "sans_bold": ["arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"],
}


def font(style: str, size: int) -> ImageFont.FreeTypeFont:
    for directory in FONT_DIRS:
        for name in FONT_FILES[style]:
            path = directory / name
            if path.exists():
                return ImageFont.truetype(str(path), size)
    raise FileNotFoundError(f"No font found for style '{style}'")


@dataclass
class Label:
    brand: str
    class_type: str
    alcohol: str
    net_contents: str
    bottler: str
    origin: str = ""
    warning_header: str = WARNING_HEADER
    warning_body: str = WARNING_BODY
    header_bold: bool = True
    paper: tuple[int, int, int] = (244, 236, 216)
    ink: tuple[int, int, int] = (40, 28, 20)


@dataclass
class Sample:
    filename: str
    label: Label
    application: dict[str, str]
    expected_verdict: str
    description: str
    photographed: bool = False


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, max_width: int) -> list[str]:
    lines, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and draw.textlength(candidate, font=fnt) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    return lines + [current] if current else lines


def draw_centered(draw, text: str, fnt, y: int, ink, line_gap: int = 12) -> int:
    """Draw wrapped, centered text starting at y and return the y below it."""
    for line in wrap(draw, text, fnt, WIDTH - 2 * MARGIN - 40):
        width = draw.textlength(line, font=fnt)
        draw.text(((WIDTH - width) / 2, y), line, font=fnt, fill=ink)
        y += fnt.size + line_gap
    return y


def draw_warning(draw, label: Label, y: int) -> None:
    """Flow the warning as one paragraph with the header in its own weight."""
    body_font = font("sans", 24)
    header_font = font("sans_bold", 24) if label.header_bold else body_font
    words = [(w, header_font) for w in label.warning_header.split()]
    words += [(w, body_font) for w in label.warning_body.split()]

    space = draw.textlength(" ", font=body_font)
    x = MARGIN
    for word, fnt in words:
        width = draw.textlength(word, font=fnt)
        if x + width > WIDTH - MARGIN:
            x, y = MARGIN, y + 34
        draw.text((x, y), word, font=fnt, fill=label.ink)
        x += width + space


def render(label: Label) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), label.paper)
    draw = ImageDraw.Draw(img)
    draw.rectangle([30, 30, WIDTH - 30, HEIGHT - 30], outline=label.ink, width=6)
    draw.rectangle([46, 46, WIDTH - 46, HEIGHT - 46], outline=label.ink, width=2)

    brand_size = 110
    while brand_size > 60 and draw.textlength(
        max(label.brand.split(), key=len), font=font("serif_bold", brand_size)
    ) > WIDTH - 2 * MARGIN - 40:
        brand_size -= 6
    y = draw_centered(draw, label.brand, font("serif_bold", brand_size), 120, label.ink, 16)

    y += 20
    draw.line([(WIDTH / 2 - 180, y), (WIDTH / 2 + 180, y)], fill=label.ink, width=3)
    y += 40
    y = draw_centered(draw, label.class_type, font("serif_italic", 50), y, label.ink)
    if label.origin:
        y = draw_centered(draw, label.origin, font("sans", 30), y + 20, label.ink)

    y = draw_centered(draw, label.alcohol, font("sans_bold", 44), y + 60, label.ink)
    y = draw_centered(draw, label.net_contents, font("sans_bold", 44), y + 10, label.ink)
    draw_centered(draw, label.bottler, font("sans", 28), y + 50, label.ink)

    if label.warning_header or label.warning_body:
        draw_warning(draw, label, HEIGHT - 300)
    return img


def photograph(img: Image.Image) -> Image.Image:
    """Make a clean render look like a handheld photo: tilt, uneven light, glare, blur."""
    label = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    h, w = label.shape[:2]
    pad = 110
    backdrop = (52, 46, 40)
    scene = np.full((h + 2 * pad, w + 2 * pad, 3), backdrop, np.uint8)
    scene[pad : pad + h, pad : pad + w] = label
    sh, sw = scene.shape[:2]

    corners = np.float32([[pad, pad], [pad + w, pad], [pad + w, pad + h], [pad, pad + h]])
    skewed = corners + np.float32([[35, 5], [-10, 40], [-40, -10], [10, -35]])
    scene = cv2.warpPerspective(
        scene, cv2.getPerspectiveTransform(corners, skewed), (sw, sh), borderValue=backdrop
    )
    rotation = cv2.getRotationMatrix2D((sw / 2, sh / 2), 5, 1.0)
    scene = cv2.warpAffine(scene, rotation, (sw, sh), borderValue=backdrop)

    lit = scene.astype(np.float32) * np.linspace(0.68, 1.05, sw, dtype=np.float32)[None, :, None]
    yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
    glare = np.exp(-(((xx - sw * 0.62) / 190) ** 2 + ((yy - sh * 0.42) / 120) ** 2))
    lit += (255 - lit) * (0.5 * glare)[:, :, None]

    blurred = cv2.GaussianBlur(np.clip(lit, 0, 255).astype(np.uint8), (0, 0), 1.0)
    return Image.fromarray(cv2.cvtColor(blurred, cv2.COLOR_BGR2RGB))


OLD_TOM = dict(
    brand="OLD TOM DISTILLERY",
    class_type="Kentucky Straight Bourbon Whiskey",
    alcohol="45% Alc./Vol. (90 Proof)",
    net_contents="750 mL",
    bottler="Distilled and Bottled by Old Tom Distillery, Bardstown, Kentucky",
)
OLD_TOM_APPLICATION = dict(
    brand_name="Old Tom Distillery",
    class_type="Kentucky Straight Bourbon Whiskey",
    alcohol_content="45% Alc./Vol. (90 Proof)",
    net_contents="750 mL",
    bottler="Old Tom Distillery, Bardstown, Kentucky",
    country_of_origin="",
)

SAMPLES = [
    Sample(
        "old_tom_bourbon.png",
        Label(**OLD_TOM),
        OLD_TOM_APPLICATION,
        "pass",
        "Clean label, everything matches",
    ),
    Sample(
        "stones_throw_gin.png",
        Label(
            brand="STONE'S THROW",
            class_type="London Dry Gin",
            alcohol="47% Alc./Vol. (94 Proof)",
            net_contents="750 mL",
            bottler="Bottled by Stone's Throw Spirits, Portland, Oregon",
            paper=(226, 236, 232),
            ink=(18, 52, 58),
        ),
        dict(
            brand_name="Stone's Throw",
            class_type="London Dry Gin",
            alcohol_content="47%",
            net_contents="75 cL",
            bottler="Stone's Throw Spirits, Portland, Oregon",
            country_of_origin="",
        ),
        "pass",
        "Brand differs only in capitalization; net contents in different units",
    ),
    Sample(
        "old_tom_wrong_abv.png",
        Label(**{**OLD_TOM, "alcohol": "40% Alc./Vol. (80 Proof)"}),
        OLD_TOM_APPLICATION,
        "fail",
        "Label shows 40% but the application says 45%",
    ),
    Sample(
        "silver_creek_titlecase_warning.png",
        Label(
            brand="SILVER CREEK",
            class_type="Vodka",
            alcohol="40% Alc./Vol. (80 Proof)",
            net_contents="1 L",
            bottler="Bottled by Silver Creek Spirits, Boise, Idaho",
            warning_header="Government Warning:",
            paper=(238, 240, 244),
            ink=(24, 32, 64),
        ),
        dict(
            brand_name="Silver Creek",
            class_type="Vodka",
            alcohol_content="40% Alc./Vol. (80 Proof)",
            net_contents="1 L",
            bottler="Silver Creek Spirits, Boise, Idaho",
            country_of_origin="",
        ),
        "fail",
        "Warning heading is in title case instead of capitals",
    ),
    Sample(
        "harbor_light_missing_warning.png",
        Label(
            brand="HARBOR LIGHT",
            class_type="India Pale Ale",
            alcohol="6.8% Alc./Vol.",
            net_contents="12 FL OZ",
            bottler="Brewed and Bottled by Harbor Light Brewing Co., Portland, Maine",
            warning_header="",
            warning_body="",
            paper=(250, 228, 170),
            ink=(60, 30, 10),
        ),
        dict(
            brand_name="Harbor Light",
            class_type="India Pale Ale",
            alcohol_content="6.8%",
            net_contents="12 fl oz",
            bottler="Harbor Light Brewing Co., Portland, Maine",
            country_of_origin="",
        ),
        "fail",
        "No government warning on the label",
    ),
    Sample(
        "red_mesa_altered_warning.png",
        Label(
            brand="RED MESA",
            class_type="Tequila Reposado",
            alcohol="40% Alc./Vol. (80 Proof)",
            net_contents="750 mL",
            bottler="Imported by Red Mesa Imports, San Antonio, Texas",
            origin="PRODUCT OF MEXICO",
            warning_body=(
                "(1) According to the Surgeon General, women should limit alcoholic "
                "beverages during pregnancy. (2) Consumption of alcoholic beverages "
                "may impair your ability to drive a car."
            ),
            paper=(240, 222, 200),
            ink=(90, 24, 16),
        ),
        dict(
            brand_name="Red Mesa",
            class_type="Tequila Reposado",
            alcohol_content="40% Alc./Vol. (80 Proof)",
            net_contents="750 mL",
            bottler="Red Mesa Imports, San Antonio, Texas",
            country_of_origin="Mexico",
        ),
        "fail",
        "Warning wording has been changed and shortened",
    ),
    Sample(
        "chateau_lumiere_wine.png",
        Label(
            brand="CHATEAU LUMIERE",
            class_type="Red Bordeaux Wine",
            alcohol="13.5% Alc./Vol.",
            net_contents="750 mL",
            bottler="Imported by Lumiere Wine Imports, New York, New York",
            origin="PRODUCT OF FRANCE",
            paper=(248, 244, 236),
            ink=(70, 16, 30),
        ),
        dict(
            brand_name="Chateau Lumiere",
            class_type="Red Bordeaux Wine",
            alcohol_content="13.5%",
            net_contents="750 mL",
            bottler="Lumiere Wine Imports, New York, New York",
            country_of_origin="France",
        ),
        "pass",
        "Imported wine with country of origin",
    ),
    Sample(
        "old_tom_photo.jpg",
        Label(**OLD_TOM),
        OLD_TOM_APPLICATION,
        "pass",
        "Same label photographed at an angle with glare and uneven light",
        photographed=True,
    ),
    Sample(
        "north_fork_plain_warning.png",
        Label(
            brand="NORTH FORK",
            class_type="Straight Rye Whiskey",
            alcohol="50% Alc./Vol. (100 Proof)",
            net_contents="750 mL",
            bottler="Distilled and Bottled by North Fork Distilling, Bozeman, Montana",
            header_bold=False,
            paper=(232, 226, 210),
            ink=(30, 40, 30),
        ),
        dict(
            brand_name="North Fork",
            class_type="Straight Rye Whiskey",
            alcohol_content="50% Alc./Vol. (100 Proof)",
            net_contents="750 mL",
            bottler="North Fork Distilling, Bozeman, Montana",
            country_of_origin="",
        ),
        "review",
        "Warning heading is in capitals but not bold",
    ),
    Sample(
        "blue_herron_brand_typo.png",
        Label(
            brand="BLUE HERRON",
            class_type="Small Batch Rum",
            alcohol="42% Alc./Vol. (84 Proof)",
            net_contents="750 mL",
            bottler="Bottled by Blue Heron Rum Company, Charleston, South Carolina",
            paper=(222, 232, 244),
            ink=(16, 40, 84),
        ),
        dict(
            brand_name="Blue Heron",
            class_type="Small Batch Rum",
            alcohol_content="42% Alc./Vol. (84 Proof)",
            net_contents="750 mL",
            bottler="Blue Heron Rum Company, Charleston, South Carolina",
            country_of_origin="",
        ),
        "review",
        "Brand on the label is spelled slightly differently from the application",
    ),
    Sample(
        "glen_cairn_british_spelling.png",
        Label(
            brand="GLEN CAIRN",
            class_type="Honey Flavoured Whisky Liqueur",
            alcohol="35% Alc./Vol. (70 Proof)",
            net_contents="700 mL",
            bottler="Imported by Glen Cairn Imports, Boston, Massachusetts",
            origin="PRODUCT OF SCOTLAND",
            paper=(236, 232, 214),
            ink=(28, 52, 40),
        ),
        dict(
            brand_name="Glen Cairn",
            class_type="Honey Flavored Whiskey Liqueur",
            alcohol_content="35% Alc./Vol. (70 Proof)",
            net_contents="700 mL",
            bottler="Glen Cairn Imports, Boston, Massachusetts",
            country_of_origin="Scotland",
        ),
        "pass",
        "Label uses British spelling; the application uses American",
    ),
]


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    for sample in SAMPLES:
        img = render(sample.label)
        if sample.photographed:
            photograph(img).save(OUT_DIR / sample.filename, quality=80)
        else:
            img.save(OUT_DIR / sample.filename)

    columns = ["filename", *OLD_TOM_APPLICATION, "expected_verdict", "description"]
    with open(OUT_DIR / "applications.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for s in SAMPLES:
            writer.writerow(
                {
                    "filename": s.filename,
                    **s.application,
                    "expected_verdict": s.expected_verdict,
                    "description": s.description,
                }
            )
    print(f"Wrote {len(SAMPLES)} labels and applications.csv to {OUT_DIR}")


if __name__ == "__main__":
    main()
