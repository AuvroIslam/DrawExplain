"""Tutor: turns a PerceptionResult into a grounded, step-by-step whiteboard lesson.

    plan_lesson(pr, model=None, context=None) -> Lesson
    stream_lesson(pr, model=None, context=None) -> Iterator[event dict]
    answer_followup(pr, question, lesson=None, selection=None, model=None, context=None) -> FollowupResponse
    locate_targets(pr, queries, model=None) -> list[LocatedTarget]

context (optional, app.tutor.context.LessonContext): the document page context (title, page X of N,
earlier pages, lessons already taught) and/or the student's focus question.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    from app.perception.types import PerceptionResult
    from app.schemas import Box, FollowupResponse, Lesson, LocatedTarget
    from app.tutor.context import LessonContext

__all__ = ["plan_lesson", "stream_lesson", "answer_followup", "locate_targets"]


def plan_lesson(
    pr: "PerceptionResult", model: str | None = None, context: "LessonContext | None" = None
) -> "Lesson":
    from app.tutor.planner import plan_lesson as _plan

    return _plan(pr, model=model, context=context)


def stream_lesson(
    pr: "PerceptionResult", model: str | None = None, context: "LessonContext | None" = None
) -> "Iterator[dict[str, Any]]":
    """plan_lesson as events: meta, header, one step at a time, then the full lesson."""
    from app.tutor.planner import stream_lesson as _stream

    return _stream(pr, model=model, context=context)


def answer_followup(
    pr: "PerceptionResult",
    question: str,
    lesson: "Lesson | None" = None,
    selection: "Box | None" = None,
    model: str | None = None,
    context: "LessonContext | None" = None,
) -> "FollowupResponse":
    from app.tutor.planner import answer_followup as _answer

    return _answer(pr, question, lesson=lesson, selection=selection, model=model, context=context)


def locate_targets(pr: "PerceptionResult", queries: list[str], model: str | None = None) -> "list[LocatedTarget]":
    from app.tutor.planner import locate_targets as _locate

    return _locate(pr, queries, model=model)
