"""Shared composition for the design preview and final video frames."""
from __future__ import annotations

import io
import math
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

from .sources import RECITERS, UserError

FONT = Path(__file__).parent / "fonts" / "Amiri-Regular.ttf"
TEXT_ELEMENTS = {"arabic": "Arabic ayah", "translation": "Translation", "surah": "Surah name", "reference": "Ayah reference", "reciter": "Reciter name", "watermark": "Watermark"}


@dataclass(frozen=True)
class TextStyle:
    visible: bool = True
    x: float = 50
    y: float = 50
    width: float = 82
    size: int = 25


@dataclass(frozen=True)
class LogoStyle:
    visible: bool = False
    x: float = 97
    y: float = 3
    width: float = 12
    opacity: int = 100


@dataclass(frozen=True)
class VideoStyle:
    arabic: TextStyle = field(default_factory=lambda: TextStyle(y=45, size=55))
    translation: TextStyle = field(default_factory=lambda: TextStyle(y=59, size=29))
    surah: TextStyle = field(default_factory=lambda: TextStyle(y=8, width=90))
    reference: TextStyle = field(default_factory=lambda: TextStyle(y=13, size=21))
    reciter: TextStyle = field(default_factory=lambda: TextStyle(visible=False, y=85, size=21))
    watermark: TextStyle = field(default_factory=lambda: TextStyle(y=94))
    logo: LogoStyle = field(default_factory=LogoStyle)
    watermark_text: str = "Quran Reels Studio"
    dim: int = 33
    panels: bool = True

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or set(data) - set(cls.__dataclass_fields__):
            raise UserError("The layout contains unsupported settings.")
        try:
            settings = {}
            for name, value in data.items():
                settings[name] = TextStyle(**value) if name in TEXT_ELEMENTS else LogoStyle(**value) if name == "logo" else value
            style = cls(**settings)
            style.validate()
            return style
        except (TypeError, ValueError):
            raise UserError("The layout settings have an invalid value.") from None

    def validate(self):
        def number(value, minimum, maximum):
            return type(value) in (int, float) and math.isfinite(value) and minimum <= value <= maximum
        if type(self.panels) is not bool or not number(self.dim, 0, 85):
            raise UserError("Use background dimming from 0–85 percent and a true/false text-panel setting.")
        if not isinstance(self.watermark_text, str) or len(self.watermark_text) > 120:
            raise UserError("Use a watermark of no more than 120 characters.")
        for name in (*TEXT_ELEMENTS, "logo"):
            item = getattr(self, name)
            expected = LogoStyle if name == "logo" else TextStyle
            if not isinstance(item, expected) or type(item.visible) is not bool:
                raise UserError(f"Invalid settings for {name}.")
            if not all(number(v, 0, 100) for v in (item.x, item.y)) or not number(item.width, 3, 95):
                raise UserError("Element positions must be 0–100 percent and widths 3–95 percent.")
            if name == "logo":
                if not number(item.opacity, 0, 100):
                    raise UserError("Logo opacity must be 0–100 percent.")
            elif not number(item.size, 18, 120):
                raise UserError("Text sizes must be 18–120.")


def load_logo(data: bytes):
    if not data or len(data) > 10 * 1024 * 1024:
        raise UserError("Use a PNG, JPEG or WebP logo smaller than 10 MB.")
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format not in {"PNG", "JPEG", "WEBP"} or image.width * image.height > 16_000_000:
                raise UserError("Use a PNG, JPEG or WebP logo with no more than 16 million pixels.")
            return ImageOps.exif_transpose(image).convert("RGBA")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise UserError("The logo is not a supported image. Try a PNG, JPEG or WebP file.") from None


def wrap(text, font, width, direction):
    lines, line = [], ""
    for word in text.split():
        if font.getlength(word, direction=direction) > width:
            raise ValueError("word too wide")
        candidate = (line + " " + word).strip()
        if line and font.getlength(candidate, direction=direction) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def position(frame_size, element_size, x, y):
    """Percent of available travel: 0 is left/top, 100 is right/bottom."""
    return round((frame_size[0] - element_size[0]) * x / 100), round((frame_size[1] - element_size[1]) * y / 100)


def _text_block(text, settings, size, color, *, arabic=False, caption=False):
    width, height = size
    scale = min(width / 720, height / 1000)
    max_width = max(1, round(width * settings.width / 100) - 4)
    max_height = height * (.68 if caption else .18)
    direction = "rtl" if arabic or any(unicodedata.bidirectional(c) in {"R", "AL"} for c in text) else "ltr"
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    maximum = max(14, round(settings.size * scale))
    minimum = max(14, round(maximum * .6))
    for font_size in range(maximum, minimum - 1, -1):
        font = ImageFont.truetype(str(FONT), font_size, layout_engine=ImageFont.Layout.RAQM)
        try:
            lines = wrap(text, font, max_width, direction)
        except ValueError:
            continue
        boxes = [probe.textbbox((0, 0), line, font=font, direction=direction, stroke_width=1) for line in lines]
        gap = round(font_size * .44)
        total = sum(b[3] - b[1] for b in boxes) + gap * max(0, len(lines) - 1)
        if not boxes or total > max_height:
            continue
        block_width = max(b[2] - b[0] for b in boxes) + 4
        block = Image.new("RGBA", (block_width, total + 4))
        draw, top = ImageDraw.Draw(block), 2
        for line, box in zip(lines, boxes):
            draw.text(((block_width - (box[2] - box[0])) / 2 - box[0], top - box[1]), line, font=font, direction=direction, fill=color, stroke_width=1, stroke_fill=(0, 0, 0, 200))
            top += box[3] - box[1] + gap
        return block
    raise UserError("Text is too long for this layout. Increase its width, reduce its text size, use portrait format, or hide the translation. Text has not been truncated.")


def compose_overlay(passage, verse, size, style: VideoStyle | None = None, logo=None):
    style = style or VideoStyle()
    style.validate()
    width, height = size
    image = Image.new("RGBA", size, (0, 0, 0, round(255 * style.dim / 100)))
    boxes = {}
    reciter = next((name for name, edition in RECITERS.items() if edition == passage.reciter), passage.reciter)
    texts = {"arabic": verse.arabic, "translation": verse.translation, "surah": passage.name, "reference": verse.reference, "reciter": reciter, "watermark": style.watermark_text.strip()}
    for name, text in texts.items():
        element = getattr(style, name)
        if not element.visible or not text:
            continue
        try:
            block = _text_block(text, element, size, "#fff9e8" if name == "arabic" else "#e4cfa1" if name in {"surah", "reference"} else "#e3e7e5", arabic=name == "arabic", caption=name in {"arabic", "translation"})
        except UserError as error:
            raise UserError(f"{TEXT_ELEMENTS[name]} ({verse.reference}): {error}") from None
        x, y = position(size, block.size, element.x, element.y)
        if style.panels and name in {"arabic", "translation"}:
            padding = max(6, round(min(size) / 60))
            panel = Image.new("RGBA", size)
            ImageDraw.Draw(panel).rounded_rectangle((max(0, x - padding), max(0, y - padding), min(width, x + block.width + padding), min(height, y + block.height + padding)), radius=padding, fill=(5, 20, 19, 115))
            image.alpha_composite(panel)
        image.alpha_composite(block, (x, y))
        boxes[name] = (x, y, x + block.width, y + block.height)
    if style.logo.visible:
        if logo is None:
            raise UserError("Upload a logo or turn off Show logo.")
        scale = min(width * style.logo.width / 100 / logo.width, height * .35 / logo.height)
        resized = logo.resize((max(1, round(logo.width * scale)), max(1, round(logo.height * scale))), Image.Resampling.LANCZOS)
        if style.logo.opacity != 100:
            resized.putalpha(resized.getchannel("A").point(lambda a: round(a * style.logo.opacity / 100)))
        x, y = position(size, resized.size, style.logo.x, style.logo.y)
        image.alpha_composite(resized, (x, y))
        boxes["logo"] = (x, y, x + resized.width, y + resized.height)
    return image, boxes


def overlap_warnings(boxes):
    warnings = []
    for index, (name, a) in enumerate(boxes.items()):
        for other, b in list(boxes.items())[index + 1:]:
            if min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1]):
                warnings.append(f"{TEXT_ELEMENTS.get(name, 'Logo')} overlaps {TEXT_ELEMENTS.get(other, 'Logo')}.")
    return warnings


def preview_image(overlay):
    background = Image.new("RGB", overlay.size)
    draw = ImageDraw.Draw(background)
    for y in range(background.height):
        ratio = y / background.height
        draw.line((0, y, background.width, y), fill=(round(20 + 20 * ratio), round(65 - 25 * ratio), round(68 - 30 * ratio)))
    background.paste(overlay, mask=overlay.getchannel("A"))
    return background
