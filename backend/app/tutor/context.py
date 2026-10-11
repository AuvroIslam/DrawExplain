"""Lesson context: where a page sits in a longer document, what the earlier pages said, what was
already taught, and the student's focus question. Rendered into the lesson prompt so the tutor builds
on earlier pages instead of teaching every page as if it were the first."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

MAX_PREVIOUS_PAGES = 5
PREVIOUS_PAGE_CHARS = 700  # the page right before this one
OLDER_PAGE_CHARS = 250  # the pages before that
MAX_TAUGHT = 6
TAUGHT_TITLE_CHARS = 100
TAUGHT_SUMMARY_CHARS = 240
TITLE_CHARS = 120


def clip(text: str | None, limit: int) -> str:
    """Whitespace-normalised text, cut at a word boundary to at most `limit` characters ("..." when cut)."""
    t = " ".join((text or "").split())
    if len(t) <= limit:
        return t
    cut = t[: max(0, limit - 3)]
    space = cut.rfind(" ")
    if space > limit * 0.6:
        cut = cut[:space]
    return cut.rstrip(" ,;:.-") + "..."


@dataclass
class PageNote:
    page: int
    text: str  # the page's text layer, shortened


@dataclass
class TaughtNote:
    page: int
    title: str
    summary: str


@dataclass
class LessonContext:
    question: str | None = None  # the student's focus question (any image)
    title: str | None = None  # document title (else its file name)
    page: int | None = None  # this page, 1-based; None when the image is not a document page
    pages: int | None = None  # the document's page count
    previous: list[PageNote] = field(default_factory=list)  # earlier pages with text, in page order
    taught: list[TaughtNote] = field(default_factory=list)  # lessons already taught, most recent first

    @property
    def is_document(self) -> bool:
        return self.page is not None

    @property
    def context_pages(self) -> list[int]:
        """The other pages the prompt mentions (earlier pages' text, pages already taught)."""
        return sorted({n.page for n in self.previous} | {t.page for t in self.taught})

    def document_block(self) -> str:
        if self.page is None:
            return ""
        where = f"page {self.page} of {self.pages}" if self.pages else f"page {self.page}"
        name = f" {json.dumps(self.title, ensure_ascii=False)}" if self.title else ""
        lines = ["DOCUMENT CONTEXT", f"This image is {where} of the document{name}."]
        if self.previous:
            lines.append("Earlier pages (their PDF text layer, shortened; background only):")
            for n in self.previous:
                tag = " (the previous page)" if n.page == self.page - 1 else ""
                lines.append(f"- Page {n.page}{tag}: {n.text}")
        elif self.page == 1:
            lines.append("This is the first page.")
        if self.taught:
            lines.append("Already taught to this student in this session (most recent first):")
            for t in self.taught:
                lines.append(f"- Page {t.page}: {t.title}" + (f". {t.summary}" if t.summary else ""))
        return "\n".join(lines)

    def question_block(self) -> str:
        if not self.question:
            return ""
        return f"STUDENT QUESTION: {json.dumps(self.question, ensure_ascii=False)}"

    def prompt_text(self) -> str:
        """DOCUMENT CONTEXT and STUDENT QUESTION blocks (whichever apply)."""
        return "\n\n".join(b for b in (self.document_block(), self.question_block()) if b)


def build_context(meta: dict[str, Any] | None, page: int | None, question: str | None = None) -> LessonContext:
    """Context for teaching `page` of the document described by `meta` (documents.DocumentStore.snapshot):
    up to MAX_PREVIOUS_PAGES earlier pages' text (the previous page in more detail) and the latest lesson
    taught for each other page (most recent first). With no document, only the question is carried."""
    ctx = LessonContext(question=" ".join(question.split()) if question and question.strip() else None)
    if not meta or page is None:
        return ctx
    texts = meta.get("texts") or []
    ctx.title = clip(meta.get("title") or meta.get("filename") or "", TITLE_CHARS) or None
    ctx.page = page
    ctx.pages = int(meta.get("pages") or 0) or None
    for n in range(max(1, page - MAX_PREVIOUS_PAGES), page):
        raw = texts[n - 1] if n - 1 < len(texts) else ""
        text = clip(raw, PREVIOUS_PAGE_CHARS if n == page - 1 else OLDER_PAGE_CHARS)
        if text:
            ctx.previous.append(PageNote(page=n, text=text))
    seen = {page}
    for entry in reversed(meta.get("taught") or []):
        p = entry.get("page") if isinstance(entry, dict) else None
        if not isinstance(p, int) or p in seen:
            continue
        seen.add(p)
        ctx.taught.append(TaughtNote(page=p, title=clip(entry.get("title"), TAUGHT_TITLE_CHARS),
                                     summary=clip(entry.get("summary"), TAUGHT_SUMMARY_CHARS)))
        if len(ctx.taught) >= MAX_TAUGHT:
            break
    return ctx
