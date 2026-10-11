"""Incremental parsing of the streamed lesson JSON: hand over each step the moment its object closes.

Structured outputs emit keys in schema order (title, summary, steps, quiz), so the header is complete
before the first step starts and every step can be grounded and drawn while later ones are still
being written.
"""
from __future__ import annotations

import json
import re
from typing import Any

_STEPS = re.compile(r'"steps"\s*:\s*\[')


class StepStream:
    """Feed text deltas; get back newly completed step dicts from the top-level "steps" array."""

    def __init__(self) -> None:
        self.text = ""
        self.pos = 0
        self.array_at: int | None = None  # index of the steps array's "["
        self.depth = 0  # nesting depth inside the array (0 = between items)
        self.in_str = False
        self.esc = False
        self.obj_start: int | None = None
        self.closed = False

    def feed(self, chunk: str) -> list[dict[str, Any]]:
        self.text += chunk
        if self.array_at is None:
            m = _STEPS.search(self.text)
            if m is None:
                return []
            self.array_at = m.end() - 1
            self.pos = m.end()
        out: list[dict[str, Any]] = []
        t, i = self.text, self.pos
        while i < len(t) and not self.closed:
            ch = t[i]
            if self.in_str:
                if self.esc:
                    self.esc = False
                elif ch == "\\":
                    self.esc = True
                elif ch == '"':
                    self.in_str = False
            elif ch == '"':
                self.in_str = True
            elif ch in "{[":
                if self.depth == 0 and ch == "{":
                    self.obj_start = i
                self.depth += 1
            elif ch in "}]":
                if self.depth == 0:
                    self.closed = ch == "]"  # end of the steps array
                else:
                    self.depth -= 1
                    if self.depth == 0 and ch == "}" and self.obj_start is not None:
                        try:
                            step = json.loads(t[self.obj_start:i + 1])
                        except ValueError:
                            step = None
                        if isinstance(step, dict):
                            out.append(step)
                        self.obj_start = None
            i += 1
        self.pos = i
        return out

    def header(self) -> dict[str, Any] | None:
        """{title, summary, ...} parsed from the text before the steps array, once it has started."""
        if self.array_at is None:
            return None
        try:
            head = json.loads(self.text[:self.array_at] + "[]}")
        except ValueError:
            return None
        return head if isinstance(head, dict) else None

    def result(self) -> dict[str, Any]:
        data = json.loads(self.text)
        if not isinstance(data, dict):
            raise ValueError("lesson JSON is not an object")
        return data
