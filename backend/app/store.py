"""Storage for perceived images and lessons: in memory first, persisted under DATA_DIR.

DATA_DIR/images/<image_id>/original.png   processed image (every coordinate refers to it)
                           marked.png     Set-of-Mark debug image
                           perception.json
DATA_DIR/lessons/<lesson_id>.json
"""
from __future__ import annotations

import logging
import os
import re
import threading
import uuid
from collections import OrderedDict
from pathlib import Path

from PIL import Image

from app import config, perception
from app.perception.types import PerceptionResult
from app.schemas import Lesson

log = logging.getLogger(__name__)

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def valid_id(value: str | None) -> bool:
    """True when `value` is safe to use as a file or folder name."""
    return bool(value) and _ID_RE.match(value) is not None


def image_url(image_id: str) -> str:
    return f"/api/images/{image_id}/original.png"


def marked_url(image_id: str) -> str:
    return f"/api/images/{image_id}/marked.png"


def _write_bytes(path: Path, data: bytes) -> None:
    """Write via a temp file + rename so readers never see a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex[:6]}.tmp")
    tmp.write_bytes(data)
    try:
        os.replace(tmp, path)
    except PermissionError:  # Windows: target briefly open by a reader
        tmp.unlink(missing_ok=True)
        path.write_bytes(data)


def _png_bytes(image: Image.Image) -> bytes:
    from io import BytesIO

    buf = BytesIO()
    image.save(buf, format="PNG", compress_level=3)
    return buf.getvalue()


class ImageStore:
    """PerceptionResults by image id. Memory is an LRU; anything evicted (or lost in a
    restart) is re-perceived from original.png on disk the next time it is asked for."""

    def __init__(self, root: Path | None = None, max_in_memory: int = 32) -> None:
        self.root = Path(root) if root is not None else config.DATA_DIR / "images"
        self.max_in_memory = max_in_memory
        self._items: OrderedDict[str, PerceptionResult] = OrderedDict()
        self._digests: dict[str, str] = {}
        self._loading: dict[str, threading.Lock] = {}
        self._lock = threading.Lock()

    def folder(self, image_id: str) -> Path:
        if not valid_id(image_id):
            raise KeyError(image_id)
        return self.root / image_id

    def file(self, image_id: str, name: str) -> Path:
        """Path of one stored file ("original.png", "marked.png", "perception.json")."""
        if name not in ("original.png", "marked.png", "perception.json"):
            raise KeyError(name)
        return self.folder(image_id) / name

    def exists(self, image_id: str) -> bool:
        with self._lock:
            if image_id in self._items:
                return True
        return valid_id(image_id) and (self.root / image_id / "original.png").is_file()

    def find_digest(self, digest: str) -> PerceptionResult | None:
        """Image already ingested from identical upload bytes (same process), if any."""
        with self._lock:
            image_id = self._digests.get(digest)
        if image_id is None:
            return None
        try:
            return self.get(image_id)
        except KeyError:
            return None

    def create(
        self,
        image: Image.Image,
        digest: str | None = None,
        timings: dict[str, float] | None = None,
    ) -> PerceptionResult:
        """Perceive a prepared image under a fresh id and persist it."""
        image_id = new_id()
        pr = perception.perceive(image, image_id)
        if timings:
            for key, value in timings.items():
                pr.perception.timings.setdefault(key, value)
        self.put(pr, digest=digest)
        return pr

    def put(self, pr: PerceptionResult, digest: str | None = None, save_original: bool = True) -> None:
        image_id = pr.perception.image_id
        folder = self.folder(image_id)
        pr.perception.image_url = image_url(image_id)
        pr.perception.marked_url = marked_url(image_id)
        folder.mkdir(parents=True, exist_ok=True)
        if save_original or not (folder / "original.png").is_file():
            _write_bytes(folder / "original.png", _png_bytes(pr.image.convert("RGB")))
        _write_bytes(folder / "marked.png", _png_bytes(pr.marked.convert("RGB")))
        _write_bytes(folder / "perception.json", pr.perception.model_dump_json(indent=2).encode("utf-8"))
        with self._lock:
            self._remember(image_id, pr)
            if digest:
                self._digests[digest] = image_id

    def get(self, image_id: str) -> PerceptionResult:
        """From memory, else re-perceived from DATA_DIR (server restart); KeyError if unknown."""
        with self._lock:
            pr = self._items.get(image_id)
            if pr is not None:
                self._items.move_to_end(image_id)
                return pr
            original = self.folder(image_id) / "original.png"
            if not original.is_file():
                raise KeyError(image_id)
            loading = self._loading.setdefault(image_id, threading.Lock())
        with loading:
            with self._lock:
                pr = self._items.get(image_id)
            if pr is not None:
                return pr
            log.info("re-perceiving %s from disk", image_id)
            with Image.open(original) as im:
                image = im.convert("RGB")
            pr = perception.perceive(image, image_id)
            self.put(pr, save_original=False)
        with self._lock:
            self._loading.pop(image_id, None)
        return pr

    def _remember(self, image_id: str, pr: PerceptionResult) -> None:
        self._items[image_id] = pr
        self._items.move_to_end(image_id)
        while len(self._items) > self.max_in_memory:
            self._items.popitem(last=False)


class LessonStore:
    """Lessons by lesson id, in memory and as DATA_DIR/lessons/<lesson_id>.json."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root is not None else config.DATA_DIR / "lessons"
        self._items: dict[str, Lesson] = {}
        self._lock = threading.Lock()

    def path(self, lesson_id: str) -> Path:
        if not valid_id(lesson_id):
            raise KeyError(lesson_id)
        return self.root / f"{lesson_id}.json"

    def put(self, lesson: Lesson) -> Lesson:
        """Store a lesson (assigning a fresh id when it has no usable one)."""
        if not valid_id(lesson.lesson_id):
            lesson.lesson_id = new_id()
        _write_bytes(self.path(lesson.lesson_id), lesson.model_dump_json(indent=2).encode("utf-8"))
        with self._lock:
            self._items[lesson.lesson_id] = lesson
        return lesson

    def get(self, lesson_id: str) -> Lesson:
        with self._lock:
            lesson = self._items.get(lesson_id)
        if lesson is not None:
            return lesson
        path = self.path(lesson_id)
        if not path.is_file():
            raise KeyError(lesson_id)
        lesson = Lesson.model_validate_json(path.read_text(encoding="utf-8"))
        with self._lock:
            self._items[lesson_id] = lesson
        return lesson
