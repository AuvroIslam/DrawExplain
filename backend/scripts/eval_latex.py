"""Formula OCR on the GPU service: what the CPU OCR read vs the LaTeX the GPU returned, per formula line.

    python scripts/eval_latex.py [--out ../samples/eval/latex_ocr.md] image [image ...]

Needs GPU_URL / GPU_KEY (.env). Waits for the container, then perceives each image with the normal
pipeline and records every line sent to formula OCR: the OCR text, the LaTeX, and whether the pipeline
kept it (it drops LaTeX that adds nothing or disagrees with the OCR text).
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("GPU_WAIT_COLD", "1")  # set before app.config is imported
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image  # noqa: E402

from app.perception import gpu, perceive  # noqa: E402
from app.perception import pipeline  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+")
    ap.add_argument("--out", default=str(ROOT / "samples" / "eval" / "latex_ocr.md"))
    args = ap.parse_args()
    if not gpu.latex_enabled():
        sys.exit("formula OCR is off: set GPU_URL and GPU_KEY")
    t = time.perf_counter()
    print(f"GPU service ready: {gpu.wait_ready(240)} ({time.perf_counter() - t:.1f}s)", flush=True)

    jobs: list = []
    real_start = pipeline.start_formula_ocr

    def recording_start(*a, **kw):
        job = real_start(*a, **kw)
        if job is not None:
            jobs.append(job)
        return job

    pipeline.start_formula_ocr = recording_start
    rows, sent, kept, seconds = [], 0, 0, []
    for name in args.images:
        path = Path(name).resolve()
        jobs.clear()
        pr = perceive(Image.open(path).convert("RGB"), path.stem)
        latex_s = pr.perception.timings.get("latex")
        for job in jobs:
            seconds.append(job.seconds)
            for ocr, tex in zip(job.texts, job.result or [None] * len(job.texts)):
                ok = gpu.latex_text(ocr, tex) is not None
                sent += 1
                kept += ok
                rows.append((path.relative_to(ROOT).as_posix(), ocr, tex, ok))
        print(f"{path.name}: {sum(len(j.texts) for j in jobs)} formula line(s), latex stage {latex_s}s", flush=True)

    def cell(s: str | None) -> str:
        return "-" if not s else "`" + s.replace("|", r"\|").replace("`", "'") + "`"

    md = ["# Formula OCR (GPU service)", "",
          "Each line the CPU OCR read that looks like a formula is cropped and read again by the formula-OCR "
          "model on the GPU service; the LaTeX is kept (appended to the region text the tutor reads) only when "
          "it adds something and shares most letters and digits with the OCR text. Made by "
          "`backend/scripts/eval_latex.py`.", "",
          f"{sent} formula lines sent, {kept} LaTeX kept; GPU time per image {min(seconds, default=0):.1f}-"
          f"{max(seconds, default=0):.1f} s (in the background, while the CPU stages run).", "",
          "| image | CPU OCR text | LaTeX from the GPU | kept |", "|---|---|---|---|"]
    md += [f"| {img} | {cell(ocr)} | {cell(tex)} | {'yes' if ok else 'no'} |" for img, ocr, tex, ok in rows]
    Path(args.out).write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print(f"{sent} lines, {kept} kept -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
