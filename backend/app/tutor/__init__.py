"""Tutor: turns a PerceptionResult into a grounded, step-by-step whiteboard lesson.

    plan_lesson(pr, model=None) -> Lesson
    answer_followup(pr, question, lesson=None, selection=None, model=None) -> FollowupResponse
    locate_targets(pr, queries, model=None) -> list[LocatedTarget]
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.perception.types import PerceptionResult
    from app.schemas import Box, FollowupResponse, Lesson, LocatedTarget

__all__ = ["plan_lesson", "answer_followup", "locate_targets"]


def plan_lesson(pr: "PerceptionResult", model: str | None = None) -> "Lesson":
    from app.tutor.planner import plan_lesson as _plan

    return _plan(pr, model=model)


def answer_followup(
    pr: "PerceptionResult",
    question: str,
    lesson: "Lesson | None" = None,
    selection: "Box | None" = None,
    model: str | None = None,
) -> "FollowupResponse":
    from app.tutor.planner import answer_followup as _answer

    return _answer(pr, question, lesson=lesson, selection=selection, model=model)


def locate_targets(pr: "PerceptionResult", queries: list[str], model: str | None = None) -> "list[LocatedTarget]":
    from app.tutor.planner import locate_targets as _locate

    return _locate(pr, queries, model=model)
