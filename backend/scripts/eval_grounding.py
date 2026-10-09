"""Grounding evaluation: how precisely do the tutor's drawings land?

For every ground-truth element (samples/**/*.json) we ask each model to locate it and score four
ways of turning the answer into a drawing box, all from the same images and calls:
  raw         the model alone on the plain image ("just ask GPT for coordinates")
  som_approx  the model's own box estimate when it also sees the Set-of-Mark image
  ids_only    the CV region(s) the model picked, without the cross-check
  fused       the pipeline: ids x estimate x OCR text x ink, fused (app.tutor.grounding.fuse)

    python scripts/eval_grounding.py [--models gpt-5.4-mini,gpt-4.1-mini] [--sets clean,photo,...]
                                     [--limit N] [--workers 4]
Writes samples/eval/results.json and results.md. LLM responses are cached on disk, so re-runs are free.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.perception import perceive, prepare_image  # noqa: E402
from app.perception.rectify import transform_box  # noqa: E402
from app.schemas import Box  # noqa: E402
from app.tutor import prompts  # noqa: E402
from app.tutor.geometry import box_iou, union_box  # noqa: E402
from app.tutor.grounding import RELIABLE_AGREEMENT, approx_agreement, fuse, normalize_ids, parse_approx  # noqa: E402
from app.tutor.llm import chat_json  # noqa: E402

SETS = {
    "clean": config.ROOT_DIR / "samples" / "synthetic" / "clean",
    "photo": config.ROOT_DIR / "samples" / "synthetic" / "photo",
    "dark": config.ROOT_DIR / "samples" / "synthetic" / "dark",
    "small": config.ROOT_DIR / "samples" / "synthetic" / "small",
    "fixtures": config.BACKEND_DIR / "tests" / "fixtures",
    "quick": config.ROOT_DIR / "samples" / "quick",
}
METHODS = ("raw", "som_approx", "ids_only", "fused")
OUT_DIR = config.ROOT_DIR / "samples" / "eval"

RAW_SYSTEM = "You locate things on a study image so a tutor can draw on them precisely."
RAW_SCHEMA: dict = {
    "type": "object",
    "properties": {"targets": {"type": "array", "items": {
        "type": "object",
        "properties": {"query": {"type": "string"},
                       "approx": {"type": "array", "items": {"type": "number"},
                                  "description": "[x, y, w, h] as fractions of the image size"}},
        "required": ["query", "approx"], "additionalProperties": False}}},
    "required": ["targets"],
    "additionalProperties": False,
}


def raw_parts(img: Any, queries: list[str]) -> list:
    qs = "\n".join(f"- {json.dumps(q, ensure_ascii=False)}" for q in queries)
    return [f"IMAGE ({img.width}x{img.height} px):", img,
            "For each query return query (copied exactly) and approx = the tight bounding box of that thing as "
            "[x, y, w, h] = left, top, width, height in fractions (0..1) of the image width and height. "
            f"Return one entry per query, in order.\nQueries:\n{qs}"]


def _entries(data: dict, queries: list[str]) -> list[dict | None]:
    entries = [e for e in (data.get("targets") or []) if isinstance(e, dict)]
    by_q = {str(e.get("query", "")).strip().lower(): e for e in entries}
    return [by_q.get(q.strip().lower()) or (entries[i] if i < len(entries) else None) for i, q in enumerate(queries)]


def load_items(sets: list[str], limit: int | None) -> list[dict]:
    items = []
    for s in sets:
        for gt_path in sorted(SETS[s].glob("*.json")):
            gt = json.loads(gt_path.read_text(encoding="utf-8"))
            if "elements" not in gt:
                continue
            img = gt_path.parent / gt.get("image", "")
            if not img.is_file():
                img = next((p for p in (gt_path.with_suffix(".png"), gt_path.with_suffix(".jpg")) if p.is_file()), None)
            if img is None:
                continue
            items.append({"set": s, "path": img, "gt": gt})
    return items[:limit] if limit else items


def evaluate(item: dict, models: list[str], flatten: bool = True) -> list[dict]:
    gt = item["gt"]
    img = prepare_image(item["path"].read_bytes())
    t0 = time.perf_counter()
    pr = perceive(img, item["path"].stem, flatten=flatten)
    perceive_s = time.perf_counter() - t0
    sx, sy = img.width / gt["width"], img.height / gt["height"]
    els = gt["elements"]
    queries = [el.get("query") or el["name"] for el in els]

    def to_board(b: list[float]) -> Box:  # ground-truth pixels -> normalized box on the board image
        px = (b[0] * sx, b[1] * sy, b[2] * sx, b[3] * sy)
        if pr.transform is not None:
            px = transform_box(pr.transform, px)
        return Box(x=px[0] / pr.width, y=px[1] / pr.height, w=(px[2] - px[0]) / pr.width, h=(px[3] - px[1]) / pr.height)

    truth = [to_board(e["box"]) for e in els]
    recs: list[dict] = []
    for model in models:
        raw, raw_meta = chat_json(model, RAW_SYSTEM, raw_parts(pr.image, queries), RAW_SCHEMA, "raw_locate", cache=True)
        som, som_meta = chat_json(model, prompts.LOCATE_SYSTEM, prompts.locate_parts(pr, queries),
                                  prompts.LOCATE_SCHEMA, "locate", cache=True)
        som_entries = _entries(som, queries)
        agreement = approx_agreement(pr, [(e.get("ids"), e.get("approx")) for e in som_entries if e])
        trust = agreement is None or agreement >= RELIABLE_AGREEMENT
        raw_s = raw_meta.get("original_seconds") or raw_meta.get("seconds", 0.0)
        som_s = som_meta.get("original_seconds") or som_meta.get("seconds", 0.0)
        for el, q, g, r, s in zip(els, queries, truth, _entries(raw, queries), som_entries):
            ids = normalize_ids(s.get("ids")) if s else []
            valid = [pr.region(i) for i in ids if pr.region(i) is not None]
            fused = fuse(pr, ids, s.get("approx") if s else None, q, trust_approx=trust)
            boxes = {
                "raw": parse_approx(r.get("approx"), pr.width, pr.height) if r else None,
                "som_approx": parse_approx(s.get("approx"), pr.width, pr.height) if s else None,
                "ids_only": union_box(v.box for v in valid) if valid else None,
                "fused": fused.box if fused else None,
            }
            for method, b in boxes.items():
                iou = box_iou(b, g) if b is not None else 0.0
                cx, cy = (b.x + b.w / 2, b.y + b.h / 2) if b is not None else (-1.0, -1.0)
                recs.append({
                    "set": item["set"], "image": item["path"].name, "element": el["name"], "kind": el.get("kind", "?"),
                    "model": model, "method": method, "iou": round(iou, 4),
                    "center_in": g.x <= cx <= g.x + g.w and g.y <= cy <= g.y + g.h,
                    "grounding": fused.grounding if (method == "fused" and fused) else None,
                    "agreement": agreement,
                    "rectified": pr.transform is not None,
                    "llm_seconds": round(raw_s if method == "raw" else som_s, 3),
                    "perceive_seconds": round(perceive_s, 3),
                })
    print(f"  {item['set']:8s} {item['path'].name:28s} {len(els):3d} elements, perception {perceive_s:.1f}s", flush=True)
    return recs


def summarize(recs: list[dict], keys: tuple[str, ...]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in recs:
        groups[tuple(r[k] for k in keys)].append(r)
    rows = []
    for key, rs in sorted(groups.items()):
        n = len(rs)
        rows.append({**dict(zip(keys, key)), "n": n,
                     "mean_iou": sum(r["iou"] for r in rs) / n,
                     "hit50": sum(r["iou"] >= 0.5 for r in rs) / n,
                     "hit75": sum(r["iou"] >= 0.75 for r in rs) / n,
                     "hit90": sum(r["iou"] >= 0.9 for r in rs) / n,
                     "center": sum(r["center_in"] for r in rs) / n})
    return rows


def to_markdown(recs: list[dict], models: list[str]) -> str:
    out = ["# Grounding evaluation", "",
           "IoU between each drawing box and the ground-truth box; hit@t = share of elements with IoU >= t.", "",
           "## Overall", "", "| model | method | n | mean IoU | hit@0.5 | hit@0.75 | hit@0.9 | centre in box |",
           "|---|---|---|---|---|---|---|---|"]
    for r in summarize(recs, ("model", "method")):
        out.append(f"| {r['model']} | {r['method']} | {r['n']} | {r['mean_iou']:.3f} | {r['hit50']:.0%} | "
                   f"{r['hit75']:.0%} | {r['hit90']:.0%} | {r['center']:.0%} |")
    out += ["", "## hit@0.75 by image set", "", "| model | method | " + " | ".join(SETS) + " |",
            "|---|---|" + "---|" * len(SETS)]
    by_set = {(r["model"], r["method"], r["set"]): r for r in summarize(recs, ("model", "method", "set"))}
    for m in models:
        for meth in METHODS:
            cells = [f"{by_set[(m, meth, s)]['hit75']:.0%}" if (m, meth, s) in by_set else "-" for s in SETS]
            out.append(f"| {m} | {meth} | " + " | ".join(cells) + " |")
    out += ["", "## How the fused pipeline grounded each target", "", "| model | grounding | count |", "|---|---|---|"]
    counts: dict[tuple, int] = defaultdict(int)
    for r in recs:
        if r["method"] == "fused":
            counts[(r["model"], r["grounding"] or "none")] += 1
    for (m, g), c in sorted(counts.items()):
        out.append(f"| {m} | {g} | {c} |")
    return "\n".join(out) + "\n"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="gpt-5.4-mini,gpt-4.1-mini")
    ap.add_argument("--sets", default=",".join(SETS))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=str(OUT_DIR))
    ap.add_argument("--no-flatten", action="store_true", help="ablation: skip photo rectification")
    args = ap.parse_args()
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    items = load_items([s.strip() for s in args.sets.split(",") if s.strip()], args.limit)
    print(f"{len(items)} images x {len(models)} models")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        recs = [r for rs in pool.map(lambda it: evaluate(it, models, not args.no_flatten), items) for r in rs]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(recs, indent=1), encoding="utf-8")
    md = to_markdown(recs, models)
    (out / "results.md").write_text(md, encoding="utf-8")
    print("\n" + md)


if __name__ == "__main__":
    main()
