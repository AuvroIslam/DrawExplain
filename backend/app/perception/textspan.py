"""Word geometry inside OCR text lines: tight line boxes, repair of dropped spaces, span boxes.

A line crop is deskewed (principal axis of its ink) and binarised against its own background;
the column profile of the main text band gives letter runs and, at wide gaps, ink words. A small
dynamic program aligns the OCR words with the ink words using Helvetica-like character widths.
That lets perception re-insert spaces RapidOCR dropped ("Arouterforwards" -> "A router forwards")
and lets the tutor underline one word inside a sentence.
"""
from __future__ import annotations

import difflib
import math
import re
import unicodedata
from dataclasses import dataclass
from typing import TYPE_CHECKING

import cv2
import numpy as np

from app.perception.gpu import strip_latex
from app.perception.preprocess import local_text_mask, remove_specks
from app.schemas import Box

if TYPE_CHECKING:
    from app.perception.types import PerceptionResult
    from app.schemas import Region

WORD_GAP = 0.2  # ink gap (x band height) that may separate two words
SPLIT_GAP = 0.3  # gap that is a word gap even without a clear jump in the line's gap sizes
MIN_SKEW, MAX_SKEW = 0.7, 12.0  # degrees
SPACE_EM, BEARING_EM = 0.278, 0.1
MAX_GROUP_CHARS = 32
BULLETS = "•●▪■◦·◆◇▶►○‣⁃*–—-"

# Helvetica / Arial advance widths in 1/1000 em (proportions are what matters).
_ADV = {
    " ": 278, "!": 278, '"': 355, "#": 556, "$": 556, "%": 889, "&": 667, "'": 191, "(": 333, ")": 333,
    "*": 389, "+": 584, ",": 278, "-": 333, ".": 278, "/": 278, ":": 278, ";": 278, "<": 584, "=": 584,
    ">": 584, "?": 556, "@": 1015, "[": 278, "\\": 278, "]": 278, "^": 469, "_": 556, "`": 333,
    "{": 334, "|": 260, "}": 334, "~": 584,
    "A": 667, "B": 667, "C": 722, "D": 722, "E": 667, "F": 611, "G": 778, "H": 722, "I": 278, "J": 500,
    "K": 667, "L": 556, "M": 833, "N": 722, "O": 778, "P": 667, "Q": 778, "R": 722, "S": 667, "T": 611,
    "U": 722, "V": 667, "W": 944, "X": 667, "Y": 667, "Z": 611,
    "a": 556, "b": 556, "c": 500, "d": 556, "e": 556, "f": 278, "g": 556, "h": 556, "i": 222, "j": 222,
    "k": 500, "l": 222, "m": 833, "n": 556, "o": 556, "p": 556, "q": 556, "r": 333, "s": 500, "t": 278,
    "u": 556, "v": 500, "w": 722, "x": 500, "y": 500, "z": 500,
}
_SPLITTABLE = re.compile(r"[0-9A-Za-z'’.,:;!?()%&/+=\-]+")


def char_em(c: str) -> float:
    """Approximate advance width of one character in em."""
    w = _ADV.get(c)
    if w is None:
        if c.isdigit():
            w = 556
        elif unicodedata.east_asian_width(c) in ("W", "F"):
            w = 1000
        else:
            w = 600
    return w / 1000.0


def _runs(on: np.ndarray) -> list[tuple[int, int]]:
    """[start, end) runs of True in a 1-D bool array."""
    if on.size == 0 or not on.any():
        return []
    d = np.diff(np.concatenate(([0], on.astype(np.int8), [0])))
    starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    return [(int(s), int(e)) for s, e in zip(starts, ends)]


# ---------------------------------------------------------------- line ink


@dataclass
class LineInk:
    """Binarised, deskewed crop of one text line."""

    mask: np.ndarray  # bool (h, w) in the deskewed crop frame
    band: tuple[int, int]  # rows [y0, y1) of the text band
    runs: list[tuple[int, int]]  # letter runs [x0, x1) inside the band
    to_image: np.ndarray  # 2x3 affine: crop frame -> image pixels
    angle: float  # skew the crop was corrected by (degrees)

    @property
    def h(self) -> int:
        return max(1, self.band[1] - self.band[0])

    @property
    def x_range(self) -> tuple[int, int]:
        return self.runs[0][0], self.runs[-1][1]

    def words(self, gap: float = WORD_GAP) -> list[tuple[int, int]]:
        """Letter runs merged across gaps narrower than `gap` x band height."""
        if not self.runs:
            return []
        limit = max(2.0, gap * self.h)
        out = [list(self.runs[0])]
        for s, e in self.runs[1:]:
            if s - out[-1][1] < limit:
                out[-1][1] = e
            else:
                out.append([s, e])
        return [(a, b) for a, b in out]

    def image_box(self, x0: float, x1: float) -> tuple[float, float, float, float]:
        """Axis-aligned image-pixel box of crop columns [x0, x1), tightened to their ink rows."""
        y0, y1 = self.band
        a, b = int(max(0, math.floor(x0))), int(min(self.mask.shape[1], math.ceil(x1)))
        if b > a:
            rows = np.flatnonzero(self.mask[y0:y1, a:b].any(axis=1))
            if rows.size:
                y0, y1 = y0 + int(rows[0]), y0 + int(rows[-1]) + 1
        pts = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], np.float64)
        img = pts @ self.to_image[:, :2].T + self.to_image[:, 2]
        return float(img[:, 0].min()), float(img[:, 1].min()), float(img[:, 0].max()), float(img[:, 1].max())


def _profile_sharpness(xc: np.ndarray, yc: np.ndarray, deg: float) -> float:
    t = math.radians(deg)
    yp = yc * math.cos(t) - xc * math.sin(t)
    hist = np.bincount(np.round(yp - yp.min()).astype(np.int64))
    return float(np.dot(hist, hist))


def _skew(mask: np.ndarray) -> float:
    """Text direction in degrees (rising lines are negative): the angle whose row projection of
    the line's ink is sharpest. 0 when the line is short or the gain over 0 degrees is marginal."""
    h, w = mask.shape
    if w < 3 * h or mask.sum() < 40:
        return 0.0
    k = max(3, int(round(0.6 * h)))
    blob = cv2.dilate(mask.astype(np.uint8), np.ones((1, k), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(blob, connectivity=8)
    if n <= 1:
        return 0.0
    best = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    if stats[best, cv2.CC_STAT_WIDTH] < 1.5 * stats[best, cv2.CC_STAT_HEIGHT]:
        return 0.0
    ys, xs = np.nonzero((labels == best) & mask)
    if xs.size < 40:
        return 0.0
    step = max(1, xs.size // 4000)
    xc = (xs[::step] - xs.mean()).astype(np.float64)
    yc = (ys[::step] - ys.mean()).astype(np.float64)
    s0 = _profile_sharpness(xc, yc, 0.0)
    coarse = np.arange(-MAX_SKEW, MAX_SKEW + 0.01, 0.5)
    vals = [_profile_sharpness(xc, yc, a) for a in coarse]
    a0 = float(coarse[int(np.argmax(vals))])
    fine = np.arange(a0 - 0.4, a0 + 0.41, 0.1)
    fvals = [_profile_sharpness(xc, yc, a) for a in fine]
    i = int(np.argmax(fvals))
    theta = float(fine[i])
    if abs(theta) < MIN_SKEW or fvals[i] < 1.08 * s0:
        return 0.0
    return round(theta, 2)


def _rotate(crop: np.ndarray, angle: float) -> tuple[np.ndarray, np.ndarray]:
    """Rotate a crop by `angle` degrees onto an enlarged canvas filled with its background colour."""
    h, w = crop.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2.0, h / 2.0), angle, 1.0)
    cos, sin = abs(m[0, 0]), abs(m[0, 1])
    nw, nh = int(math.ceil(w * cos + h * sin)), int(math.ceil(h * cos + w * sin))
    m[0, 2] += nw / 2.0 - w / 2.0
    m[1, 2] += nh / 2.0 - h / 2.0
    ring = np.concatenate([crop[0], crop[-1], crop[:, 0], crop[:, -1]], axis=0)
    bg = tuple(int(v) for v in np.median(ring, axis=0))
    out = cv2.warpAffine(crop, m, (nw, nh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=bg)
    return out, m


def _band(mask: np.ndarray) -> tuple[int, int] | None:
    """Rows of the main text band: the densest row run (x-height zone) grown through ascenders,
    dots and descenders, but not into fragments of neighbouring lines."""
    rows = mask.sum(axis=1).astype(np.float64)
    if rows.size == 0 or rows.max() <= 0:
        return None
    core = _runs(rows >= 0.15 * rows.max())
    c0, c1 = max(core, key=lambda r: rows[r[0]:r[1]].sum())
    ch = c1 - c0
    gap = max(2, int(round(0.2 * ch)))
    y0, y1 = c0, c1
    empty, y = 0, c0 - 1
    while y >= max(0, c0 - int(round(0.8 * ch))):
        if rows[y] > 0:
            y0, empty = y, 0
        else:
            empty += 1
            if empty > gap:
                break
        y -= 1
    empty, y = 0, c1
    while y < min(rows.size, c1 + int(round(0.7 * ch))):
        if rows[y] > 0:
            y1, empty = y + 1, 0
        else:
            empty += 1
            if empty > gap:
                break
        y += 1
    return y0, y1


def analyse_line(rgb: np.ndarray, box: tuple[float, float, float, float], angle: float | None = None,
                 pad: int = 3) -> LineInk | None:
    """Ink analysis of the text line inside pixel box (x0, y0, x1, y1); None if it holds no ink."""
    H, W = rgb.shape[:2]
    x0, y0 = max(0, int(math.floor(box[0])) - pad), max(0, int(math.floor(box[1])) - pad)
    x1, y1 = min(W, int(math.ceil(box[2])) + pad), min(H, int(math.ceil(box[3])) + pad)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return None
    crop = np.ascontiguousarray(rgb[y0:y1, x0:x1])
    mask = local_text_mask(crop)
    if angle is None:
        angle = _skew(mask)
    to_image = np.array([[1.0, 0.0, x0], [0.0, 1.0, y0]])
    if abs(angle) >= MIN_SKEW:
        crop, fwd = _rotate(crop, angle)
        mask = local_text_mask(crop)
        to_image = cv2.invertAffineTransform(fwd)
        to_image[:, 2] += (x0, y0)
    else:
        angle = 0.0
    mask = remove_specks(mask, max(2, int(round(3 * (mask.shape[0] / 30.0) ** 2))))
    band = _band(mask)
    if band is None:
        return None
    cols = mask[band[0]:band[1]]
    runs = _runs(cols.any(axis=0))
    full = mask.any(axis=1).sum()
    # drop edge runs that are lines crossing the whole crop (a shape outline next to the text)
    while runs:
        s, e = runs[0]
        if e - s <= 0.2 * (band[1] - band[0]) and mask[:, s:e].any(axis=1).sum() >= 0.95 * mask.shape[0] and len(runs) > 1:
            runs.pop(0)
            continue
        s, e = runs[-1]
        if e - s <= 0.2 * (band[1] - band[0]) and mask[:, s:e].any(axis=1).sum() >= 0.95 * mask.shape[0] and len(runs) > 1:
            runs.pop()
            continue
        break
    if not runs or full == 0:
        return None
    return LineInk(mask=mask, band=band, runs=runs, to_image=to_image, angle=float(angle))


# ---------------------------------------------------------------- word alignment


@dataclass
class WordMatch:
    c0: int  # char range [c0, c1) in the aligned text
    c1: int
    x0: int  # ink columns [x0, x1) in the line crop
    x1: int
    err: float  # relative width error of this group


def _split_ok(left: str, right: str) -> bool:
    return (left.isalnum() or left in ".,:;!?)%") and (right.isalnum() or right == "(") and not (
        left.isdigit() and right.isdigit())


def word_gap_px(li: LineInk, text: str) -> float:
    """Smallest ink gap that counts as a word gap in this line: the top cluster of gap sizes above
    the largest jump down to letter-gap sizes, bounded by fixed fractions of the band height."""
    h = li.h
    gaps = sorted((li.runs[i + 1][0] - li.runs[i][1] for i in range(len(li.runs) - 1)), reverse=True)
    n_chars = sum(1 for c in text if not c.isspace())
    blurred = n_chars >= 6 and len(li.runs) < 0.6 * n_chars
    lo, hi = (WORD_GAP if blurred else 0.25) * h, SPLIT_GAP * h
    thr, best = hi, 1.5
    for k in range(len(gaps) - 1):
        if gaps[k] < lo:
            break
        if gaps[k + 1] <= 0.25 * h and gaps[k] / max(gaps[k + 1], 1.0) >= best:
            thr, best = float(gaps[k]), gaps[k] / max(gaps[k + 1], 1.0)
    if len(text.split()) <= 1 and not blurred:
        return float(max(thr, hi))
    return float(min(max(thr, lo), hi))


def align(text: str, words: list[tuple[int, int]], h: float, word_px: float | None = None,
          split: bool = False, max_merge: int = 6) -> tuple[str, list[WordMatch], float] | None:
    """Align the text's words (in order) with ink words by a DP over char boundaries.

    Several tokens may share one ink word (narrow word gaps) and up to `max_merge` ink words may
    form one group (wide letter gaps; merging a word-sized gap >= `word_px` is expensive). With
    `split`, long Latin tokens may be cut at word-sized gaps, which re-inserts spaces OCR dropped.
    Returns (text with single spaces, matches, total cost) or None when no alignment exists.
    """
    toks = [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]
    q = len(words)
    if not toks or not q:
        return None
    if word_px is None:
        word_px = SPLIT_GAP * h
    chars: list[str] = []
    tok_start: set[int] = set()
    cand: set[int] = set()
    for a, b in toks:
        k0 = len(chars)
        if k0:
            tok_start.add(k0)
        tok = text[a:b]
        chars.extend(tok)
        if split and _SPLITTABLE.fullmatch(tok):
            for i in range(1, len(tok)):
                if _split_ok(tok[i - 1], tok[i]) and (len(tok) >= 7 or tok[i - 1] in ",;:"):
                    cand.add(k0 + i)
    m = len(chars)
    cum = np.concatenate(([0.0], np.cumsum([char_em(c) for c in chars])))
    starts_cum = np.zeros(m + 2, np.int32)
    for k in range(1, m + 1):
        starts_cum[k] = starts_cum[k - 1] + (1 if k in tok_start else 0)
    pos = sorted({0, m} | tok_start | cand)
    gaps = [words[j + 1][0] - words[j][1] for j in range(q - 1)]
    total_px = float(sum(b - a for a, b in words))
    denom = float(cum[m]) - BEARING_EM * q + SPACE_EM * max(0, len(toks) - q)
    if total_px <= 0 or denom <= 0:
        return None
    scale = total_px / denom
    norm_min = 0.6 * h
    inf = float("inf")
    n_pos = len(pos)
    dp = np.full((q + 1, n_pos), inf)
    back: dict[tuple[int, int], tuple[int, int, float]] = {}
    dp[0, 0] = 0.0
    merge_cost = [0.15 if g >= word_px else 0.01 + 0.5 * max(0.0, g / h - WORD_GAP) for g in gaps]
    for j in range(q):
        for pi in range(n_pos):
            base = dp[j, pi]
            if base == inf:
                continue
            p = pos[pi]
            for pj in range(pi + 1, n_pos):
                p2 = pos[pj]
                if p2 - p > MAX_GROUP_CHARS:
                    break
                is_split = p2 in cand
                inner = int(starts_cum[p2 - 1] - starts_cum[p])
                pred = scale * (float(cum[p2] - cum[p]) + SPACE_EM * inner - BEARING_EM)
                mc = 0.0
                for j2 in range(j + 1, min(q, j + max_merge) + 1):
                    if j2 > j + 1:
                        mc += merge_cost[j2 - 2]
                    if (j2 == q) != (p2 == m):
                        continue
                    if is_split and j2 < q and gaps[j2 - 1] < word_px:
                        continue
                    act = float(words[j2 - 1][1] - words[j][0])
                    e = (pred - act) / max(act, norm_min)
                    cost = base + 3.0 * e * e + mc + (0.02 if is_split else 0.0)
                    if cost < dp[j2, pj]:
                        dp[j2, pj] = cost
                        back[(j2, pj)] = (j, pi, e)
    if dp[q, n_pos - 1] == inf:
        return None
    groups: list[tuple[int, int, int, int, float]] = []
    j, pi = q, n_pos - 1
    while j > 0:
        pj, pjx, e = back[(j, pi)]
        groups.append((pos[pjx], pos[pi], pj, j, e))
        j, pi = pj, pjx
    groups.reverse()
    used = {g[1] for g in groups if g[1] in cand}
    out: list[str] = []
    new_index = [0] * (m + 1)
    for k, c in enumerate(chars):
        if k and (k in tok_start or k in used):
            out.append(" ")
        new_index[k] = len(out)
        out.append(c)
    new_index[m] = len(out)
    matches = [WordMatch(new_index[p0], new_index[p1 - 1] + 1, words[j0][0], words[j1 - 1][1], e)
               for p0, p1, j0, j1, e in groups]
    return "".join(out), matches, float(dp[q, n_pos - 1])


def restore_spaces(text: str, li: LineInk) -> str:
    """Re-insert spaces OCR dropped inside long tokens when the ink clearly shows word gaps."""
    toks = text.split()
    words = li.words(WORD_GAP)
    if len(words) <= len(toks) or not any(len(t) >= 7 for t in toks) or len(text) > 160:
        return text
    fixed = align(text, words, li.h, word_gap_px(li, text), split=True, max_merge=4)
    if fixed is None or fixed[0] == " ".join(toks):
        return text
    errs = [abs(mt.err) for mt in fixed[1]]
    if max(errs) > 0.45 or float(np.mean(np.square(errs))) > 0.04:
        return text
    return fixed[0]


def strip_bullet(text: str, li: LineInk) -> tuple[str, LineInk]:
    """Remove a leading bullet glyph from the text and its ink from the line (if present)."""
    t = text.lstrip()
    glyph = len(t) > 1 and t[0] in BULLETS and (t[1].isspace() or t[1].isalnum() or t[1] in "\"'(")
    if glyph:
        t = t[1:].lstrip()
    words = li.words(WORD_GAP)
    if len(words) < 2 or not t:
        return (t if glyph else text), li
    (s, e), nxt = words[0], words[1][0]
    h = li.h
    rows = np.flatnonzero(li.mask[li.band[0]:li.band[1], s:e].any(axis=1))
    bh = int(rows[-1] - rows[0] + 1) if rows.size else 0
    gap = nxt - e
    first = t.split()[0]
    if glyph:
        drop = e - s <= 1.0 * h and gap >= 0.25 * h
    else:
        drop = (e - s <= 0.6 * h and 0 < bh <= 0.7 * h and gap >= 0.4 * h and 0.3 <= (e - s) / max(bh, 1) <= 2.5
                and len(first) >= 3 and first[:3].isalpha())
    if not drop:
        return (t if glyph else text), li
    runs = [r for r in li.runs if r[0] >= nxt]
    return t, LineInk(mask=li.mask, band=li.band, runs=runs, to_image=li.to_image, angle=li.angle)


def refine_line(rgb: np.ndarray, box: tuple[float, float, float, float], text: str
                ) -> tuple[str, tuple[float, float, float, float]]:
    """OCR line -> (cleaned text, tight pixel box): bullet removed, dropped spaces restored."""
    li = analyse_line(rgb, box)
    if li is None:
        return text, box
    text, li = strip_bullet(text, li)
    if not li.runs:
        return text, box
    text = restore_spaces(text, li)
    tight = li.image_box(*li.x_range)
    bw, bh = box[2] - box[0], box[3] - box[1]
    tw, th = tight[2] - tight[0], tight[3] - tight[1]
    if tw < 0.35 * bw or th < 0.25 * bh:
        return text, box
    tight = (max(tight[0], box[0] - 2), max(tight[1], box[1] - 2), min(tight[2], box[2] + 2), min(tight[3], box[3] + 2))
    return text, tight


# ---------------------------------------------------------------- span lookup


def _fold(text: str) -> tuple[str, list[int]]:
    """Lower-cased text with whitespace runs collapsed, plus a map to original indices."""
    out: list[str] = []
    idx: list[int] = []
    prev_space = True
    for i, ch in enumerate(text):
        if ch.isspace():
            if not prev_space:
                out.append(" ")
                idx.append(i)
            prev_space = True
            continue
        prev_space = False
        for c in ch.lower():
            out.append(c)
            idx.append(i)
    while out and out[-1] == " ":
        out.pop()
        idx.pop()
    return "".join(out), idx


def _word_bounded(t: str, a: int, b: int) -> bool:
    return (a == 0 or not t[a - 1].isalnum()) and (b >= len(t) or not t[b].isalnum())


def find_span(text: str, span: str) -> tuple[int, int, float] | None:
    """Char range [i, j) of `span` in `text` (case/whitespace-insensitive, then space-insensitive,
    then fuzzy with difflib ratio >= 0.8) and a match score."""
    t, tmap = _fold(text)
    s = " ".join(span.lower().split()).strip(" .,;:!?\"'")
    if not t or not s:
        return None
    hits = [k.start() for k in re.finditer(re.escape(s), t)]
    if hits:
        k = next((h for h in hits if _word_bounded(t, h, h + len(s))), hits[0])
        return tmap[k], tmap[k + len(s) - 1] + 1, 1.0
    keep = [i for i, c in enumerate(t) if c != " "]
    t2, s2 = "".join(t[i] for i in keep), s.replace(" ", "")
    k = t2.find(s2) if s2 else -1
    if k >= 0:
        return tmap[keep[k]], tmap[keep[k + len(s2) - 1]] + 1, 0.95
    best = (0.0, 0, 0)
    n = len(s)
    if n > 120 or len(t) > 600:
        return None
    sm = difflib.SequenceMatcher(autojunk=False)
    sm.set_seq2(s)
    for length in range(max(1, n - 2), n + 3):
        for a in range(0, len(t) - length + 1):
            sm.set_seq1(t[a:a + length])
            if sm.real_quick_ratio() <= best[0] or sm.quick_ratio() <= best[0]:
                continue
            r = sm.ratio()
            if r > best[0]:
                best = (r, a, a + length)
    if best[0] < 0.8:
        return None
    a, b = best[1], best[2]
    while a < b and t[a] == " ":
        a += 1
    while b > a and t[b - 1] == " ":
        b -= 1
    if b <= a:
        return None
    return tmap[a], tmap[b - 1] + 1, best[0]


def _em(text: str, a: int, b: int) -> float:
    return sum(char_em(c) for c in text[a:b])


def _snap(runs: list[tuple[int, int]], x: float, lo: int, hi: int, start: bool) -> float:
    edges = [(r[0] if start else r[1]) for r in runs if r[1] > lo and r[0] < hi]
    if not edges:
        return x
    return float(min(edges, key=lambda v: abs(v - x)))


def span_x(li: LineInk, text: str, i: int, j: int) -> tuple[float, float]:
    """Crop-frame column range of characters [i, j) of the line text."""
    res = (align(text, li.words(WORD_GAP), li.h, word_gap_px(li, text)) if " ".join(text.split()) == text
           else None)
    if res is not None and res[0] == text and max(abs(mt.err) for mt in res[1]) <= 0.5:
        matches = res[1]
        x0 = x1 = None
        for mt in matches:
            if x0 is None and mt.c0 <= i < mt.c1:
                if i == mt.c0:
                    x0 = float(mt.x0)
                else:
                    est = mt.x0 + (mt.x1 - mt.x0) * _em(text, mt.c0, i) / max(_em(text, mt.c0, mt.c1), 1e-6)
                    x0 = _snap(li.runs, est, mt.x0, mt.x1, start=True)
            if mt.c0 < j <= mt.c1:
                if j == mt.c1:
                    x1 = float(mt.x1)
                else:
                    est = mt.x0 + (mt.x1 - mt.x0) * _em(text, mt.c0, j) / max(_em(text, mt.c0, mt.c1), 1e-6)
                    x1 = _snap(li.runs, est, mt.x0, mt.x1, start=False)
        if x0 is None:  # span starts on a space between groups
            x0 = float(next((mt.x0 for mt in matches if mt.c0 >= i), matches[-1].x0))
        if x1 is None:
            x1 = float(next((mt.x1 for mt in reversed(matches) if mt.c1 <= j), matches[0].x1))
        if x1 > x0:
            return x0, x1
    a, b = li.x_range
    total = max(_em(text, 0, len(text)), 1e-6)
    est0 = a + (b - a) * _em(text, 0, i) / total
    est1 = a + (b - a) * _em(text, 0, j) / total
    x0, x1 = _snap(li.runs, est0, a, b, True), _snap(li.runs, est1, a, b, False)
    return (x0, x1) if x1 > x0 else (est0, est1)


def _descendant_lines(pr: "PerceptionResult", region: "Region") -> list["Region"]:
    if region.kind == "text":
        return [region]
    parent = {r.id: r.parent_id for r in pr.perception.regions}
    out = []
    for r in pr.perception.regions:
        if r.kind != "text" or not r.text:
            continue
        p, hops = r.parent_id, 0
        while p is not None and hops < 8:
            if p == region.id:
                out.append(r)
                break
            p, hops = parent.get(p), hops + 1
    return out


def _line_span_px(rgb: np.ndarray, r: "Region", W: int, H: int, i: int, j: int
                  ) -> tuple[float, float, float, float]:
    b = r.box
    px = (b.x * W, b.y * H, (b.x + b.w) * W, (b.y + b.h) * H)
    text = strip_latex(r.text)  # spans index the OCR text, not an appended formula-OCR LaTeX
    li = analyse_line(rgb, px)
    if li is None or not li.runs:
        total = max(_em(text, 0, len(text)), 1e-6)
        x0 = px[0] + (px[2] - px[0]) * _em(text, 0, i) / total
        x1 = px[0] + (px[2] - px[0]) * _em(text, 0, j) / total
        return x0, px[1], x1, px[3]
    x0, x1 = span_x(li, text, i, j)
    return li.image_box(x0, x1)


def span_box(pr: "PerceptionResult", region_id: str, span: str) -> Box | None:
    """Tight normalized box of `span` inside a text region (or inside the text lines of a shape /
    text block), None when the region has no text or the span is not found."""
    region = pr.region(region_id)
    if region is None or not span or not span.strip():
        return None
    lines = _descendant_lines(pr, region)
    if not lines:
        return None
    rgb = np.asarray(pr.image.convert("RGB"))
    H, W = rgb.shape[:2]
    best: tuple["Region", tuple[int, int, float]] | None = None
    for r in lines:
        hit = find_span(strip_latex(r.text), span)
        if hit is not None and (best is None or hit[2] > best[1][2] + 1e-9):
            best = (r, hit)
    parts: list[tuple[float, float, float, float]] = []
    if best is not None:
        r, (i, j, _) = best
        parts.append(_line_span_px(rgb, r, W, H, i, j))
    elif len(lines) > 1:
        joined, offsets = "", []
        for r in lines:
            if joined:
                joined += " "
            offsets.append(len(joined))
            joined += strip_latex(r.text)
        hit = find_span(joined, span)
        if hit is None:
            return None
        i, j, _ = hit
        for r, off in zip(lines, offsets):
            n = len(strip_latex(r.text))
            a, b = max(i, off), min(j, off + n)
            if b > a:
                parts.append(_line_span_px(rgb, r, W, H, a - off, b - off))
    if not parts:
        return None
    x0 = max(0.0, min(p[0] for p in parts))
    y0 = max(0.0, min(p[1] for p in parts))
    x1 = min(float(W), max(p[2] for p in parts))
    y1 = min(float(H), max(p[3] for p in parts))
    if x1 <= x0 or y1 <= y0:
        return None
    return Box(x=x0 / W, y=y0 / H, w=(x1 - x0) / W, h=(y1 - y0) / H)
