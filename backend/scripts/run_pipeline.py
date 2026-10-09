"""Run the whole backend pipeline on one image and write inspectable artifacts.

    python scripts/run_pipeline.py <image> [--model M] [--out DIR] [--no-llm] [--followup QUESTION]

Writes perception.json, marked.png, lesson.json, preview_step<N>.png (cumulative) and
preview_all.png (+ followup.json / preview_followup.png) into the out dir
(default backend/data/runs/<stem>/), and prints a readable summary.
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import argparse  # noqa: E402
import re  # noqa: E402
import time  # noqa: E402

from app import config  # noqa: E402
from app.perception import perceive, prepare_image  # noqa: E402
from app.perception.types import PerceptionResult  # noqa: E402
from app.render.preview import render_lesson  # noqa: E402
from app.schemas import Annotation, Box, Region, Step  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _parse(argv)
    src = Path(args.image)
    if not src.is_file():
        print(f"error: no such image: {src}", file=sys.stderr)
        return 1
    out = Path(args.out) if args.out else config.DATA_DIR / "runs" / src.stem
    out.mkdir(parents=True, exist_ok=True)
    timings: dict[str, float] = {}

    t0 = time.perf_counter()
    image = prepare_image(src.read_bytes())
    timings["prepare"] = time.perf_counter() - t0
    t0 = time.perf_counter()
    pr = perceive(image, re.sub(r"[^A-Za-z0-9_-]", "_", src.stem)[:48] or "image")
    timings["perceive"] = time.perf_counter() - t0
    (out / "perception.json").write_text(pr.perception.model_dump_json(indent=2), encoding="utf-8")
    pr.marked.convert("RGB").save(out / "marked.png")
    _print_perception(src, pr)
    regions = pr.perception.regions if args.show_regions else None
    written = ["perception.json", "marked.png"]

    if not args.no_llm:
        from app.tutor import answer_followup, plan_lesson

        t0 = time.perf_counter()
        try:
            lesson = plan_lesson(pr, model=args.model)
        except Exception as exc:
            print(f"\nerror: plan_lesson failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
        timings["plan_lesson"] = time.perf_counter() - t0
        (out / "lesson.json").write_text(lesson.model_dump_json(indent=2), encoding="utf-8")
        written.append("lesson.json")
        for old in out.glob("preview_step*.png"):
            old.unlink()
        for n in range(1, len(lesson.steps) + 1):
            render_lesson(pr.image, lesson.steps, upto=n, regions=regions).save(out / f"preview_step{n}.png")
            written.append(f"preview_step{n}.png")
        render_lesson(pr.image, lesson.steps, regions=regions).save(out / "preview_all.png")
        written.append("preview_all.png")
        _print_lesson(lesson.title, lesson.summary, lesson.model, lesson.steps, pr, lesson.warnings, lesson.timings)
        _print_quiz(lesson.quiz, pr)

        if args.followup:
            t0 = time.perf_counter()
            try:
                fu = answer_followup(pr, args.followup, lesson=lesson, model=args.model)
            except Exception as exc:
                print(f"\nerror: answer_followup failed: {type(exc).__name__}: {exc}", file=sys.stderr)
                return 2
            timings["answer_followup"] = time.perf_counter() - t0
            (out / "followup.json").write_text(fu.model_dump_json(indent=2), encoding="utf-8")
            render_lesson(pr.image, fu.steps, regions=regions).save(out / "preview_followup.png")
            written += ["followup.json", "preview_followup.png"]
            print(f"\n== follow-up: {args.followup!r}")
            _print_lesson(fu.title, None, fu.model, fu.steps, pr, fu.warnings, fu.timings)

    print("\n== timings (s): " + ", ".join(f"{k} {v:.2f}" for k, v in timings.items()))
    print(f"== wrote {len(written)} files to {out}")
    for name in written:
        print(f"   {name}")
    return 0


def _parse(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="image -> perception + lesson + preview PNGs")
    p.add_argument("image", help="path to a study image (png/jpg/webp)")
    p.add_argument("--model", default=None, help=f"OpenAI model (default {config.OPENAI_MODEL})")
    p.add_argument("--out", default=None, help="output folder (default backend/data/runs/<stem>/)")
    p.add_argument("--no-llm", action="store_true", help="perception only, no paid calls")
    p.add_argument("--followup", default=None, metavar="QUESTION", help="also ask one follow-up question")
    p.add_argument("--show-regions", action="store_true", help="draw faint region outlines in the previews")
    return p.parse_args(argv)


def _print_perception(src: Path, pr: PerceptionResult) -> None:
    p = pr.perception
    stage = ", ".join(f"{k} {v:.2f}" for k, v in p.timings.items())
    print(f"== perception: {src.name}  {p.width}x{p.height}  {len(p.regions)} regions" + (f"  ({stage})" if stage else ""))
    kinds: dict[str, int] = {}
    for r in p.regions:
        kinds[r.kind] = kinds.get(r.kind, 0) + 1
    print("   kinds: " + ", ".join(f"{k} {n}" for k, n in sorted(kinds.items())))
    for r in p.regions:
        text = f' "{_clip(r.text, 48)}"' if r.text else ""
        parent = f" in {r.parent_id}" if r.parent_id else ""
        print(f"   {r.id:>4} {r.kind:<10} {_fmt_box(r.box)} {r.source:<6} {r.score:.2f}{parent}{text}")


def _print_lesson(
    title: str,
    summary: str | None,
    model: str,
    steps: list[Step],
    pr: PerceptionResult,
    warnings: list[str],
    timings: dict[str, float],
) -> None:
    n_ann = sum(len(s.annotations) for s in steps)
    print(f'\n== lesson: "{title}"  [{model}]  {len(steps)} steps, {n_ann} annotations')
    if summary:
        print(f"   {summary}")
    for step in steps:
        print(f"\n   Step {step.index}: {step.title}")
        print(f"     narration: {step.narration}")
        for a in step.annotations:
            print(f"     - {_fmt_annotation(a, pr)}")
    if warnings:
        print(f"\n   warnings ({len(warnings)}):")
        for w in warnings:
            print(f"     ! {w}")
    if timings:
        print("   tutor timings (s): " + ", ".join(f"{k} {v:.2f}" for k, v in timings.items()))


def _print_quiz(quiz: list, pr: PerceptionResult) -> None:
    if not quiz:
        return
    print(f"\n== quiz ({len(quiz)} items)")
    for i, q in enumerate(quiz, 1):
        print(f"   Q{i}: {q.question}  -> {_fmt_ids(q.answer_ids, pr)}  {_fmt_box(q.answer_box)}")
        print(f"       {q.explanation}")


def _fmt_annotation(a: Annotation, pr: PerceptionResult) -> str:
    if a.kind == "arrow":
        targets = f"{_fmt_ids(a.from_ids, pr)} -> {_fmt_ids(a.to_ids, pr)}"
    else:
        targets = _fmt_ids(a.target_ids, pr)
    parts = [f"{a.kind:<9}", f"{a.color:<6}", targets, f"{a.grounding} {a.confidence:.2f}"]
    if a.span:
        parts.append(f'span="{a.span}"')
    if a.text:
        parts.append(f'text="{a.text}"')
    if a.cue:
        parts.append(f'cue="{a.cue}"')
    return "  ".join(parts)


def _fmt_ids(ids: list[str], pr: PerceptionResult) -> str:
    if not ids:
        return "(no ids)"
    out = []
    for rid in ids:
        region: Region | None = pr.region(rid)
        label = f'"{_clip(region.text, 20)}"' if region and region.text else (region.kind if region else "?")
        out.append(f"{rid}({label})")
    return "+".join(out)


def _fmt_box(box: Box) -> str:
    return f"[{box.x:.3f},{box.y:.3f} {box.w:.3f}x{box.h:.3f}]"


def _clip(text: str | None, n: int) -> str:
    text = (text or "").replace("\n", " ")
    return text if len(text) <= n else text[: n - 1] + "~"


if __name__ == "__main__":
    raise SystemExit(main())
