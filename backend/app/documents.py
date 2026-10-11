"""PDF reader mode: an uploaded PDF is kept whole, its pages are rendered lazily as plain images and
nothing is perceived until the student asks for one page to be explained.

DATA_DIR/docs/<doc_id>/source.pdf       the upload
                       meta.json        filename, title, page count, page sizes, each page's text layer,
                                        page -> image_id of the pages already perceived, lessons taught
                       pages/<n>.png    page n exactly as the reader shows it (a scan of it uses these pixels)
DATA_DIR/docs/_images/<image_id>.json   {doc_id, page}: the document page a perceived image belongs to
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any

from app import config
from app.perception import preprocess
from app.schemas import DocumentInfo, Lesson
from app.store import _write_bytes, valid_id
from app.tutor.context import clip

log = logging.getLogger(__name__)

TEXT_CHARS = 1500  # text layer kept per page
TITLE_CHARS = 120
FILENAME_CHARS = 200
MAX_TAUGHT = 50  # taught-lesson entries kept per document (the prompt shows only the latest few)

_DOC_ID_RE = re.compile(r"^[0-9a-f]{12}$")
_JUNK_TITLE_RE = re.compile(
    r"^(?:slide|page|folie|diapositiva)\s*\d*$|^untitled\b|^(?:microsoft\s+)?powerpoint(?:\s+presentation)?$"
    r"|^presentation\s*\d*$|^document\s*\d*$",
    re.I,
)
_TITLE_PREFIX_RE = re.compile(r"^microsoft\s+(?:powerpoint|word)\s*-\s*", re.I)
_TITLE_EXT_RE = re.compile(r"\.(?:pptx?|docx?|pdf|key|odp|odt|tex)$", re.I)


class DocumentError(ValueError):
    """The upload is not a usable PDF (the API answers 400 with this message)."""


def valid_doc_id(value: Any) -> bool:
    return isinstance(value, str) and _DOC_ID_RE.match(value) is not None


def page_url(doc_id: str) -> str:
    """Template of the page image URL: replace "{page}" with a 1-based page number."""
    return f"/api/documents/{doc_id}/pages/{{page}}.png"


def _clean_filename(name: str | None) -> str:
    base = re.split(r"[\\/]", name or "")[-1].strip()
    base = "".join(ch for ch in base if ch.isprintable())
    return base[:FILENAME_CHARS] or "document.pdf"


def _title(metadata: dict[str, Any], first_page: str) -> str | None:
    """PDF metadata title unless it is a placeholder ("Slide 1", "PowerPoint Presentation"), else the
    first real line of page 1."""
    t = " ".join(str(metadata.get("title") or "").split())
    t = _TITLE_EXT_RE.sub("", _TITLE_PREFIX_RE.sub("", t)).strip()
    if len(t) >= 3 and not _JUNK_TITLE_RE.match(t):
        return clip(t, TITLE_CHARS)
    for line in first_page.splitlines():
        line = " ".join(line.split())
        if len(line) >= 3 and any(ch.isalpha() for ch in line):
            return clip(line, TITLE_CHARS)
    return None


def _page_size(page: Any) -> tuple[int, int]:
    """Pixel size of the page image without rendering it: the pixmap bbox of the reader's DPI rule
    (MuPDF rounds the transformed page rect the same way), then prepare_image's size rule."""
    import pymupdf

    zoom = preprocess.pdf_page_dpi(page) / 72
    r = (page.rect * pymupdf.Matrix(zoom, zoom)).irect
    return preprocess.target_size(max(1, r.width), max(1, r.height))


def _read_pdf(data: bytes) -> dict[str, Any]:
    """Page count, title, page sizes and text layers of a PDF (no rendering)."""
    import pymupdf

    with preprocess.PDF_LOCK:
        try:
            doc = pymupdf.open(stream=data, filetype="pdf")
        except Exception as exc:
            raise DocumentError(f"Could not read the PDF ({type(exc).__name__})") from None
        with doc:
            if doc.needs_pass:
                raise DocumentError("The PDF is password-protected")
            if doc.page_count == 0:
                raise DocumentError("The PDF has no pages")
            sizes: list[list[int]] = []
            texts: list[str] = []
            first = ""
            for i, page in enumerate(doc):
                try:
                    sizes.append(list(_page_size(page)))
                except Exception as exc:
                    raise DocumentError(f"Could not read page {i + 1} of the PDF ({type(exc).__name__})") from None
                try:
                    raw = page.get_text("text", sort=True)
                except Exception:  # a broken text layer only costs the context
                    raw = ""
                if i == 0:
                    first = raw
                texts.append(clip(raw, TEXT_CHARS))
            metadata = dict(doc.metadata or {})
    return {"pages": len(sizes), "title": _title(metadata, first), "page_sizes": sizes, "texts": texts}


def _render_page(pdf: Path, page: int, size: tuple[int, int]) -> bytes:
    """PNG of a 1-based page: the reader's DPI rule, then resized to `size` if prepare_image would resize."""
    import pymupdf

    with preprocess.PDF_LOCK:
        with pymupdf.open(pdf) as doc:
            p = doc[page - 1]
            pix = p.get_pixmap(dpi=preprocess.pdf_page_dpi(p), alpha=False)
            png = pix.tobytes("png")
            got = (pix.width, pix.height)
    if got == size:
        return png
    from PIL import Image

    log.info("page %d renders at %dx%d; resizing to %dx%d", page, *got, *size)
    with Image.open(BytesIO(png)) as im:
        out = im.convert("RGB").resize(size, Image.LANCZOS)
    buf = BytesIO()
    out.save(buf, format="PNG", compress_level=3)
    return buf.getvalue()


class DocumentStore:
    """Uploaded PDFs by doc_id: meta in memory and in DATA_DIR/docs/<doc_id>/meta.json. Thread-safe."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root is not None else config.DATA_DIR / "docs"
        self._meta: dict[str, dict[str, Any]] = {}
        self._by_image: dict[str, tuple[str, int]] = {}
        self._lock = threading.RLock()
        self._keyed: dict[tuple[str, str, int], threading.Lock] = {}

    # ---------------------------------------------------------------- storage

    def folder(self, doc_id: str) -> Path:
        if not valid_doc_id(doc_id):
            raise KeyError(doc_id)
        return self.root / doc_id

    def _load(self, doc_id: str) -> dict[str, Any]:
        """The live meta dict (caller holds self._lock); KeyError if unknown."""
        meta = self._meta.get(doc_id)
        if meta is None:
            path = self.folder(doc_id) / "meta.json"
            try:
                meta = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                raise KeyError(doc_id) from None
            if not isinstance(meta, dict) or meta.get("doc_id") != doc_id:
                raise KeyError(doc_id)
            self._meta[doc_id] = meta
        return meta

    def _save(self, doc_id: str, meta: dict[str, Any]) -> None:
        _write_bytes(self.folder(doc_id) / "meta.json", json.dumps(meta, ensure_ascii=False).encode("utf-8"))
        self._meta[doc_id] = meta

    def _keyed_lock(self, kind: str, doc_id: str, page: int) -> threading.Lock:
        with self._lock:
            return self._keyed.setdefault((kind, doc_id, page), threading.Lock())

    # ---------------------------------------------------------------- documents

    def create(self, data: bytes, filename: str | None) -> DocumentInfo:
        """Store an uploaded PDF under a fresh doc_id. Raises DocumentError for unusable PDFs."""
        meta = _read_pdf(data)
        with self._lock:
            doc_id = uuid.uuid4().hex[:12]
            while (self.root / doc_id).exists():
                doc_id = uuid.uuid4().hex[:12]
            meta = {"doc_id": doc_id, "filename": _clean_filename(filename), **meta, "images": {}, "taught": [],
                    "created": round(time.time(), 3)}
            _write_bytes(self.folder(doc_id) / "source.pdf", data)
            self._save(doc_id, meta)
        return self._info(meta)

    def info(self, doc_id: str) -> DocumentInfo:
        with self._lock:
            return self._info(self._load(doc_id))

    @staticmethod
    def _info(meta: dict[str, Any]) -> DocumentInfo:
        return DocumentInfo(doc_id=meta["doc_id"], filename=meta["filename"], pages=meta["pages"],
                            title=meta.get("title"), page_sizes=meta["page_sizes"], page_url=page_url(meta["doc_id"]))

    def snapshot(self, doc_id: str) -> dict[str, Any]:
        """A copy of the document's meta that later updates do not change (for building a lesson context)."""
        with self._lock:
            meta = self._load(doc_id)
            return {**meta, "texts": list(meta.get("texts") or []), "images": dict(meta.get("images") or {}),
                    "taught": [dict(t) for t in meta.get("taught") or []]}

    def page_size(self, doc_id: str, page: int) -> tuple[int, int]:
        """(width, height) of a 1-based page image; KeyError for unknown documents or pages."""
        with self._lock:
            meta = self._load(doc_id)
            if not 1 <= page <= meta["pages"]:
                raise KeyError(page)
            w, h = meta["page_sizes"][page - 1]
            return int(w), int(h)

    def page_png(self, doc_id: str, page: int) -> Path:
        """Path of the rendered page image, rendering (and caching) it on first use."""
        size = self.page_size(doc_id, page)
        path = self.folder(doc_id) / "pages" / f"{page}.png"
        if path.is_file():
            return path
        with self._keyed_lock("render", doc_id, page):
            if not path.is_file():
                t0 = time.perf_counter()
                _write_bytes(path, _render_page(self.folder(doc_id) / "source.pdf", page, size))
                log.info("document %s page %d rendered in %.2fs", doc_id, page, time.perf_counter() - t0)
        return path

    def scan_lock(self, doc_id: str, page: int) -> threading.Lock:
        """Held while a page is perceived, so a double click scans it once."""
        return self._keyed_lock("scan", doc_id, page)

    # ---------------------------------------------------------------- perceived pages

    def image_for(self, doc_id: str, page: int) -> str | None:
        """image_id of the page's earlier scan, if any."""
        with self._lock:
            image_id = (self._load(doc_id).get("images") or {}).get(str(page))
        return image_id if valid_id(image_id) else None

    def set_image(self, doc_id: str, page: int, image_id: str, ocr_text: str | None = None) -> None:
        """Remember the page's scan (both ways); a page without a text layer keeps its OCR text instead."""
        if not valid_id(image_id):
            raise KeyError(image_id)
        with self._lock:
            meta = self._load(doc_id)
            meta.setdefault("images", {})[str(page)] = image_id
            texts = meta.get("texts") or []
            if ocr_text and page - 1 < len(texts) and not texts[page - 1]:
                texts[page - 1] = clip(ocr_text, TEXT_CHARS)
            self._save(doc_id, meta)
            self._by_image[image_id] = (doc_id, page)
            _write_bytes(self.root / "_images" / f"{image_id}.json",
                         json.dumps({"doc_id": doc_id, "page": page}).encode("utf-8"))

    def page_of_image(self, image_id: str) -> tuple[str, int] | None:
        """(doc_id, page) when the image is the scan of a document page (the latest such page), else None."""
        if not valid_id(image_id):
            return None
        with self._lock:
            hit = self._by_image.get(image_id)
        if hit is not None:
            return hit
        path = self.root / "_images" / f"{image_id}.json"
        if not path.is_file():
            return None
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
            doc_id, page = blob["doc_id"], int(blob["page"])
        except (OSError, ValueError, KeyError, TypeError):
            return None
        if not valid_doc_id(doc_id):
            return None
        with self._lock:
            self._by_image[image_id] = (doc_id, page)
        return doc_id, page

    # ---------------------------------------------------------------- lessons

    def add_taught(self, doc_id: str, page: int, lesson: Lesson) -> None:
        """Record a finished lesson for one of the document's pages (later lessons build on it)."""
        entry = {"page": page, "lesson_id": lesson.lesson_id, "title": clip(lesson.title, 160),
                 "summary": clip(lesson.summary, 600), "question": lesson.question, "at": round(time.time(), 3)}
        with self._lock:
            meta = self._load(doc_id)
            meta["taught"] = [*(meta.get("taught") or []), entry][-MAX_TAUGHT:]
            self._save(doc_id, meta)
