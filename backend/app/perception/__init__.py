"""Perception: find candidate regions with OCR + classical CV, before any LLM call.

    prepare_image(data: bytes) -> PIL.Image.Image   # EXIF-rotate, RGB on white, downscale
    perceive(image, image_id) -> PerceptionResult   # regions, Set-of-Mark image, ink mask
"""
from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING, Any, Callable

import cv2

from app.perception.types import FreeSpaceMap, PerceptionResult

if TYPE_CHECKING:
    from PIL import Image

__all__ = ["FreeSpaceMap", "PerceptionResult", "prepare_image", "perceive"]

log = logging.getLogger("app.perception")

# Sequential OpenCV: on page-sized images its internal thread pool saved < 0.1 s per page (OCR dominates),
# while requests already run in parallel threads. It also keeps the native pool (ConcRT on Windows) out of
# the request path, where a rare "Unknown C++ exception from OpenCV code" showed up under heavy load.
cv2.setNumThreads(1)

RETRY_PAUSE_S = 1.0


def prepare_image(data: bytes) -> "Image.Image":
    from app.perception.pipeline import prepare_image as _prepare

    return _prepare(data)


def perceive(image: "Image.Image", image_id: str, flatten: bool = True) -> PerceptionResult:
    from app.perception.pipeline import perceive as _perceive

    try:
        return _perceive(image, image_id, flatten=flatten)
    except cv2.error:
        # A native OpenCV failure on an image that perceives fine on its own (seen twice under heavy machine
        # load). Perception has no side effects, so retry once, on a fresh thread in case the failure left
        # per-thread native state behind.
        log.warning("perception of %s failed inside OpenCV; retrying once", image_id, exc_info=True)
        time.sleep(RETRY_PAUSE_S)
        return _on_fresh_thread(_perceive, image, image_id, flatten=flatten)


def _on_fresh_thread(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    box: dict[str, Any] = {}

    def run() -> None:
        try:
            box["result"] = fn(*args, **kwargs)
        except BaseException as exc:  # re-raised in the caller's thread
            box["error"] = exc

    t = threading.Thread(target=run, name="perceive-retry", daemon=True)
    t.start()
    t.join()
    if "error" in box:
        raise box["error"]
    return box["result"]
