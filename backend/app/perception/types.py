"""Internal (server-side) perception types. The API-facing part is schemas.Perception."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
from PIL import Image

from app.schemas import Box, Perception, Region


class FreeSpaceMap(Protocol):
    """Where the page is empty, so labels and arrows avoid covering content."""

    def ink_fraction(self, box: Box) -> float:
        """Fraction (0..1) of content ("ink") pixels inside a normalized box."""
        ...

    def place_near(self, target: Box, w: float, h: float, avoid: list[Box] | None = None) -> Box:
        """Best normalized box of size (w, h) close to `target`, inside the image,
        over empty space, not overlapping `target` or any `avoid` box when possible."""
        ...


@dataclass
class PerceptionResult:
    perception: Perception  # API-facing; regions carry ids
    image: Image.Image  # processed RGB image every coordinate refers to
    marked: Image.Image  # Set-of-Mark overlay: region outlines + id tags
    ink: np.ndarray  # bool mask (H, W): True where the page has content
    freespace: FreeSpaceMap

    @property
    def width(self) -> int:
        return self.perception.width

    @property
    def height(self) -> int:
        return self.perception.height

    def region(self, region_id: str) -> Region | None:
        for r in self.perception.regions:
            if r.id == region_id:
                return r
        return None

    def span_box(self, region_id: str, span: str) -> Box | None:
        """Tight normalized box of the substring `span` inside a text region,
        or None when the region has no text or the span is not found."""
        from app.perception.textspan import span_box

        return span_box(self, region_id, span)
