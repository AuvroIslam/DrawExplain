"""OCR rescue: isolated short labels the text detector misses (graph weights, node letters, axis ticks).

The detector proposes text *lines*; a lone "1" beside an edge or a "C" inside a node circle often gets
no box. Here character-sized ink blobs that no OCR line covers are grouped into short words and read
by the recognizer alone (batched), keeping confident alphanumeric reads only.
"""
from __future__ import annotations

import re

import cv2
import numpy as np

from app.perception.ocr import recognize
from app.perception.preprocess import InkInfo
from app.perception.regions import TextLine

LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+\-=/%]{0,4}$")
MIN_SCORE = 0.75


def rescue_labels(rgb: np.ndarray, ink: InkInfo, lines: list[TextLine]) -> list[TextLine]:
    H, W = rgb.shape[:2]
    heights = sorted(ln.box[3] - ln.box[1] for ln in lines)
    th = heights[len(heights) // 2] if heights else 0.03 * H  # typical text height
    th = float(np.clip(th, 0.012 * H, 0.06 * H))
    m = ink.stroke.astype(np.uint8)
    for ln in lines:
        x0, y0, x1, y1 = (int(round(v)) for v in ln.box)
        m[max(0, y0 - 2):min(H, y1 + 3), max(0, x0 - 2):min(W, x1 + 3)] = 0
    n, _, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    glyphs = []
    for j in range(1, n):
        x, y, w, h, area = (int(v) for v in stats[j])
        if not (0.35 * th <= h <= 1.6 * th) or w > 1.4 * th or area < 12:
            continue
        glyphs.append([x, y, x + w, y + h])
    glyphs.sort(key=lambda g: g[0])
    groups: list[list[int]] = []  # neighbouring glyphs on one baseline form a word ("11", "18")
    for g in glyphs:
        for grp in groups:
            gh = grp[3] - grp[1]
            v_overlap = min(grp[3], g[3]) - max(grp[1], g[1])
            if 0 <= g[0] - grp[2] <= 0.6 * gh and v_overlap >= 0.5 * min(gh, g[3] - g[1]):
                grp[:] = [min(grp[0], g[0]), min(grp[1], g[1]), max(grp[2], g[2]), max(grp[3], g[3])]
                break
        else:
            groups.append(list(g))
    groups = [g for g in groups if (g[2] - g[0]) <= 5 * (g[3] - g[1])]
    if not groups:
        return []
    crops, boxes = [], []
    for x0, y0, x1, y1 in groups:
        pad = int(round(0.35 * (y1 - y0))) + 2
        crop = rgb[max(0, y0 - pad):min(H, y1 + pad), max(0, x0 - pad):min(W, x1 + pad)]
        if crop.shape[0] < 32:  # the recognizer reads 48 px tall strips; tiny crops lose detail
            s = 32.0 / crop.shape[0]
            crop = cv2.resize(crop, (max(1, int(crop.shape[1] * s)), 32), interpolation=cv2.INTER_CUBIC)
        crops.append(np.ascontiguousarray(crop[..., ::-1]))
        boxes.append((float(x0), float(y0), float(x1), float(y1)))
    out = []
    for box, (text, score) in zip(boxes, recognize(crops)):
        text = (text or "").strip()
        if score >= MIN_SCORE and LABEL.match(text):
            out.append(TextLine(box=box, text=text, score=float(score)))
    return out
