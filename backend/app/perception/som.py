"""Set-of-Mark image: every region outlined and tagged with its id, for the vision LLM to read."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from app.schemas import Region

KIND_COLORS = {
    "text": (25, 113, 194),
    "text_block": (12, 166, 120),
    "shape": (240, 140, 0),
    "figure": (194, 37, 146),
}
_FONT_CANDIDATES = ("C:/Windows/Fonts/arialbd.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf")


def _font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    for name in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _overlaps(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def render_marks(image: Image.Image, regions: list[Region]) -> Image.Image:
    base = image.convert("RGB")
    W, H = base.size
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    size = max(14, round(0.018 * max(H, 0.56 * W)))
    font = _font(size)
    line_w = max(2, round(min(W, H) / 400))
    # outlines first (containers under contents), tags after so they stay on top
    for r in sorted(regions, key=lambda r: -(r.box.w * r.box.h)):
        x0, y0, x1, y1 = r.box.x * W, r.box.y * H, (r.box.x + r.box.w) * W, (r.box.y + r.box.h) * H
        draw.rectangle((x0, y0, x1, y1), outline=KIND_COLORS[r.kind] + (230,), width=line_w)
    placed: list[tuple[float, float, float, float]] = []
    for r in regions:
        x0, y0, x1, y1 = r.box.x * W, r.box.y * H, (r.box.x + r.box.w) * W, (r.box.y + r.box.h) * H
        tw, th = draw.textbbox((0, 0), r.id, font=font)[2:]
        pw, ph = tw + 8, th + 6
        options = [(x0, y0 - ph), (x1 - pw, y0 - ph), (x0, y1), (x0, y0), (x1 - pw, y0), (x1 + 2, y0)]
        spot = None
        for ox, oy in options + [(x0 + k * (pw + 2), y0 - ph) for k in range(1, 6)]:
            ox, oy = min(max(ox, 0), W - pw), min(max(oy, 0), H - ph)
            rect = (ox, oy, ox + pw, oy + ph)
            if not any(_overlaps(rect, p) for p in placed):
                spot = rect
                break
        if spot is None:
            ox, oy = min(max(x0, 0), W - pw), min(max(y0 - ph, 0), H - ph)
            spot = (ox, oy, ox + pw, oy + ph)
        placed.append(spot)
        draw.rectangle(spot, fill=KIND_COLORS[r.kind] + (255,))
        draw.text((spot[0] + 4, spot[1] + 2), r.id, fill=(255, 255, 255, 255), font=font)
    return Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
