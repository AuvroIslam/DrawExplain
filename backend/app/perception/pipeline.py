"""Perception pipeline: ink analysis -> OCR -> line refinement -> regions -> free space -> Set-of-Mark."""
from __future__ import annotations

import logging
import time

import numpy as np
from PIL import Image

from app.perception.freespace import FreeSpace
from app.perception.ocr import run_ocr
from app.perception.preprocess import analyse_ink, prepare_image
from app.perception.rectify import rectify
from app.perception.regions import TextLine, build_regions
from app.perception.som import render_marks
from app.perception.textspan import refine_line
from app.perception.types import PerceptionResult
from app.schemas import Perception

log = logging.getLogger("app.perception")

__all__ = ["prepare_image", "perceive"]


def perceive(image: Image.Image, image_id: str, flatten: bool = True) -> PerceptionResult:
    """flatten: perspective-rectify phone photos of a page first (the result's `image` is the flat page)."""
    image = image.convert("RGB")
    timings: dict[str, float] = {}
    t0 = t = time.perf_counter()

    def lap(name: str) -> None:
        nonlocal t
        now = time.perf_counter()
        timings[name] = round(now - t, 3)
        t = now

    transform = None
    if flatten:
        image, transform = rectify(image)
        lap("rectify")
        if transform is not None:
            timings["rectified"] = 1.0
    rgb = np.asarray(image)
    H, W = rgb.shape[:2]
    ink = analyse_ink(rgb)
    lap("ink")
    raw_lines = run_ocr(rgb, invert=ink.dark)
    lap("ocr")
    lines: list[TextLine] = []
    for ln in raw_lines:
        cx, cy = int((ln.x0 + ln.x1) / 2), int((ln.y0 + ln.y1) / 2)
        if ink.page is not None and not ink.page[min(cy, H - 1), min(cx, W - 1)]:
            continue  # text on the desk around a photographed page
        try:
            text, box = refine_line(rgb, ln.box, ln.text)
        except Exception:  # refinement is best effort; keep the raw OCR line
            text, box = ln.text, ln.box
        lines.append(TextLine(box=box, text=text, score=ln.score))
    lap("text")
    regions = build_regions(ink, lines, W, H)
    lap("regions")
    freespace = FreeSpace(ink.ink)
    lap("freespace")
    marked = render_marks(image, regions)
    lap("som")
    timings["total"] = round(time.perf_counter() - t0, 3)
    perception = Perception(image_id=image_id, width=W, height=H, regions=regions, timings=timings)
    log.info("perceived %s: %dx%d, %d regions in %.2fs", image_id, W, H, len(regions), timings["total"])
    return PerceptionResult(perception=perception, image=image, marked=marked, ink=ink.ink, freespace=freespace,
                            transform=transform)
