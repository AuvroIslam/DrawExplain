"""Run perception on images: marked PNG + regions JSON per image, and box recall vs ground truth.

    python scripts/perceive_debug.py <image> [<image> ...] [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.perception import perceive, prepare_image  # noqa: E402


def _iou(a: list[float], b: list[float]) -> float:
    iw = min(a[2], b[2]) - max(a[0], b[0])
    ih = min(a[3], b[3]) - max(a[1], b[1])
    inter = iw * ih if iw > 0 and ih > 0 else 0.0
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--out", default=str(config.DATA_DIR / "debug"))
    args = ap.parse_args()
    for path in map(Path, args.images):
        img = prepare_image(path.read_bytes())
        pr = perceive(img, path.stem)
        out = Path(args.out) / path.stem
        out.mkdir(parents=True, exist_ok=True)
        pr.marked.save(out / "marked.png")
        (out / "regions.json").write_text(pr.perception.model_dump_json(indent=1), encoding="utf-8")
        regs = pr.perception.regions
        kinds = {k: sum(r.kind == k for r in regs) for k in ("text", "shape", "text_block", "figure")}
        print(f"\n== {path.name}: {pr.width}x{pr.height}, {len(regs)} regions {kinds}, timings {pr.perception.timings}")
        gt_path = path.with_suffix(".json")
        if not gt_path.is_file():
            continue
        gt = json.loads(gt_path.read_text(encoding="utf-8"))
        sx, sy = pr.width / gt["width"], pr.height / gt["height"]
        hits, ious = 0, []
        for el in gt["elements"]:
            g = [el["box"][0] * sx, el["box"][1] * sy, el["box"][2] * sx, el["box"][3] * sy]
            best, best_r = 0.0, None
            for r in regs:
                b = [r.box.x * pr.width, r.box.y * pr.height, (r.box.x + r.box.w) * pr.width, (r.box.y + r.box.h) * pr.height]
                v = _iou(g, b)
                if v > best:
                    best, best_r = v, r
            hits += best >= 0.5
            ious.append(best)
            tag = f"{best_r.id} {best_r.kind} {best_r.text!r:.40}" if best_r else "-"
            print(f"  {best:4.2f}  {el['name'][:38]:38s} -> {tag}")
        print(f"  recall@0.5: {hits}/{len(gt['elements'])}  mean IoU {sum(ious) / len(ious):.3f}  -> {out / 'marked.png'}")


if __name__ == "__main__":
    main()
