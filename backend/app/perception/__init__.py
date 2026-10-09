"""Perception: find candidate regions with OCR + classical CV, before any LLM call.

    prepare_image(data: bytes) -> PIL.Image.Image   # EXIF-rotate, RGB on white, downscale
    perceive(image, image_id) -> PerceptionResult   # regions, Set-of-Mark image, ink mask
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.perception.types import FreeSpaceMap, PerceptionResult

if TYPE_CHECKING:
    from PIL import Image

__all__ = ["FreeSpaceMap", "PerceptionResult", "prepare_image", "perceive"]


def prepare_image(data: bytes) -> "Image.Image":
    from app.perception.pipeline import prepare_image as _prepare

    return _prepare(data)


def perceive(image: "Image.Image", image_id: str) -> PerceptionResult:
    from app.perception.pipeline import perceive as _perceive

    return _perceive(image, image_id)
