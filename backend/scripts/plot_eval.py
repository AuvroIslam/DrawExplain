"""Chart of the grounding evaluation: raw model coordinates vs the fused pipeline, per image set.

    python scripts/plot_eval.py [--metric hit75|hit50|hit90|mean_iou] [--methods raw,fused]
Reads samples/eval/results.json, writes samples/eval/chart_<metric>.png.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from app import config  # noqa: E402

SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e7e5df"
STYLE = {  # categorical slots 1-2 of the validated reference palette (all checks pass, light mode)
    "raw": ("#eb6834", "Raw GPT coordinates"),
    "som_approx": ("#eb6834", "GPT estimate with region marks"),
    "ids_only": ("#eb6834", "Region ids only"),
    "fused": ("#2a78d6", "StudyLens grounding (ours)"),
}
METRICS = {
    "hit75": ("Drawings that land tightly on their target", "IoU ≥ 0.75 with the ground-truth box"),
    "hit50": ("Drawings that land on their target", "IoU ≥ 0.5 with the ground-truth box"),
    "hit90": ("Pixel-tight drawings", "IoU ≥ 0.9 with the ground-truth box"),
    "mean_iou": ("How well drawing boxes match the target", "mean IoU with the ground-truth box"),
}
SET_ORDER = ["clean", "photo", "dark", "small", "fixtures"]  # "quick" is one slide: too small to plot
SET_LABELS = {"clean": "clean slides", "photo": "phone photos", "dark": "dark slides", "small": "small text",
              "fixtures": "hard cases", "all": "all images"}


def _value(rs: list[dict], metric: str) -> float:
    if not rs:
        return float("nan")
    if metric == "mean_iou":
        return sum(r["iou"] for r in rs) / len(rs)
    t = {"hit50": 0.5, "hit75": 0.75, "hit90": 0.9}[metric]
    return sum(r["iou"] >= t for r in rs) / len(rs)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--metric", default="hit75", choices=list(METRICS))
    ap.add_argument("--methods", default="raw,fused")
    ap.add_argument("--results", default=str(config.ROOT_DIR / "samples" / "eval" / "results.json"))
    args = ap.parse_args()
    recs = json.loads(Path(args.results).read_text(encoding="utf-8"))
    methods = args.methods.split(",")
    models = list(dict.fromkeys(r["model"] for r in recs))
    sets = [s for s in SET_ORDER if any(r["set"] == s for r in recs)] + ["all"]
    title, subtitle = METRICS[args.metric]

    plt.rcParams.update({"font.family": "Segoe UI", "font.size": 11, "axes.edgecolor": GRID})
    fig, axes = plt.subplots(1, len(models), figsize=(6.2 * len(models), 4.6), sharey=True, facecolor=SURFACE)
    axes = [axes] if len(models) == 1 else list(axes)
    width = 0.8 / len(methods)
    for ax, model in zip(axes, models):
        ax.set_facecolor(SURFACE)
        for mi, method in enumerate(methods):
            color, _ = STYLE[method]
            for si, s in enumerate(sets):
                rs = [r for r in recs if r["model"] == model and r["method"] == method
                      and (r["set"] == s if s != "all" else r["set"] in SET_ORDER)]
                v = _value(rs, args.metric)
                x = si + (mi - (len(methods) - 1) / 2) * width
                ax.bar(x, v, width=width, color=color, edgecolor=SURFACE, linewidth=2, zorder=3)
                ax.text(x, v + 0.015, f"{v:.0%}" if args.metric != "mean_iou" else f"{v:.2f}", ha="center",
                        va="bottom", fontsize=9, color=INK_2, zorder=4)
        ax.set_xticks(range(len(sets)), [SET_LABELS[s] for s in sets], color=INK_2)
        ax.axvline(len(sets) - 1.5, color=GRID, linewidth=1, zorder=1)
        ax.set_ylim(0, 1.1)
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0], ["0%", "25%", "50%", "75%", "100%"] if args.metric != "mean_iou"
                      else ["0", "0.25", "0.5", "0.75", "1"], color=INK_2)
        ax.grid(axis="y", color=GRID, linewidth=1, zorder=0)
        ax.tick_params(length=0)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.set_title(model, loc="left", fontsize=12, color=INK, fontweight="semibold", pad=10)
    handles = [plt.Rectangle((0, 0), 1, 1, color=STYLE[m][0]) for m in methods]
    fig.legend(handles, [STYLE[m][1] for m in methods], loc="upper right", ncol=len(methods), frameon=False,
               fontsize=10, labelcolor=INK_2, bbox_to_anchor=(0.99, 0.985))
    fig.text(0.012, 0.965, title, fontsize=15, fontweight="semibold", color=INK, va="top")
    fig.text(0.012, 0.905, f"{subtitle} · synthetic slides and photos with known answers · same model and image per pair",
             fontsize=10, color=INK_2, va="top")
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    out = Path(args.results).with_name(f"chart_{args.metric}.png")
    fig.savefig(out, dpi=200, facecolor=SURFACE)
    print(out)


if __name__ == "__main__":
    main()
