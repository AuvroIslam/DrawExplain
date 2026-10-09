"""Generate the perception test fixtures (images + pixel ground truth JSON).

Run from backend/:  .venv/Scripts/python tests/fixtures/make_fixtures.py
Ground truth format matches samples/: {"elements": [{"name", "kind", "box": [x0, y0, x1, y1]}]}.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FONT_DIR = Path("C:/Windows/Fonts")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "arialbd.ttf" if bold else "arial.ttf"
    path = FONT_DIR / name
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


def text_el(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str, fnt, fill, name: str | None = None,
            anchor: str = "la") -> dict:
    draw.text(xy, text, font=fnt, fill=fill, anchor=anchor)
    box = draw.textbbox(xy, text, font=fnt, anchor=anchor)
    return {"name": name or text, "kind": "text", "box": [int(v) for v in box]}


def save(name: str, img: Image.Image, elements: list[dict], note: str, fmt: str = "png") -> None:
    path = HERE / f"{name}.{fmt}"
    if fmt == "jpg":
        img.save(path, quality=62)
    else:
        img.save(path, optimize=True)
    meta = {"image": path.name, "width": img.width, "height": img.height, "note": note, "elements": elements}
    (HERE / f"{name}.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print("wrote", path.name, img.size, len(elements), "elements")


def arrow(draw: ImageDraw.ImageDraw, p0, p1, fill, width: int = 3, head: int = 12) -> None:
    draw.line([p0, p1], fill=fill, width=width)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    left = (p1[0] - head * math.cos(ang - 0.45), p1[1] - head * math.sin(ang - 0.45))
    right = (p1[0] - head * math.cos(ang + 0.45), p1[1] - head * math.sin(ang + 0.45))
    draw.polygon([p1, left, right], fill=fill)


def dense_diagram() -> None:
    """A dense labelled block diagram: 16 small shapes of 4 kinds, connectors, arrows."""
    w, h = 1280, 720
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    els = [text_el(d, (40, 22), "Inside a Computer: Data Paths", font(32, True), (20, 20, 20))]
    labels = [
        ["CPU", "ALU", "Registers", "L1 Cache", "L2 Cache"],
        ["Control Unit", "RAM", "GPU", "VRAM", "SSD"],
        ["Bus", "I/O Hub", "NIC", "USB", "BIOS"],
        ["DMA", "Clock", "Fan", "PSU", "Display"],
    ]
    kinds = [
        ["round", "round", "rect", "round", "round"],
        ["rect", "round", "round", "rect", "round"],
        ["ellipse", "round", "diamond", "round", "rect"],
        ["diamond", "ellipse", None, "round", "rect"],
    ]
    fills = [(255, 236, 204), (219, 234, 254), (220, 252, 231), (243, 232, 255), (254, 226, 226)]
    xs = [128 + 256 * i for i in range(5)]
    ys = [150, 290, 430, 580]
    fnt = font(19)
    centers = {}
    for r, row in enumerate(labels):
        for c, label in enumerate(row):
            kind = kinds[r][c]
            if kind is None:
                continue
            cx, cy = xs[c], ys[r]
            bw, bh = (150, 58) if kind in ("round", "rect") else (150, 80) if kind == "diamond" else (130, 70)
            box = [cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2]
            fill = fills[(r + c) % len(fills)]
            outline = (40, 60, 90)
            if kind == "round":
                d.rounded_rectangle(box, radius=12, fill=fill, outline=outline, width=3)
            elif kind == "rect":
                d.rectangle(box, fill=fill, outline=outline, width=3)
            elif kind == "ellipse":
                d.ellipse(box, fill=fill, outline=outline, width=3)
            else:
                pts = [(cx, box[1]), (box[2], cy), (cx, box[3]), (box[0], cy)]
                d.polygon(pts, fill=fill, outline=outline, width=3)
            centers[label] = (cx, cy, bw, bh)
            els.append({"name": label, "kind": "shape", "shape": kind, "box": box})
            els.append(text_el(d, (cx, cy), label, fnt, (15, 15, 15), name=f"label: {label}", anchor="mm"))
    links = [("CPU", "ALU"), ("ALU", "Registers"), ("Registers", "L1 Cache"), ("L1 Cache", "L2 Cache"),
             ("Control Unit", "RAM"), ("RAM", "GPU"), ("GPU", "VRAM"), ("VRAM", "SSD"),
             ("Bus", "I/O Hub"), ("I/O Hub", "NIC"), ("NIC", "USB"), ("USB", "BIOS"),
             ("DMA", "Clock"), ("PSU", "Display")]
    for a, b in links:
        ax, ay, aw, _ = centers[a]
        bx, by, bw2, _ = centers[b]
        arrow(d, (ax + aw // 2 + 4, ay), (bx - bw2 // 2 - 6, by), (60, 60, 60), width=2, head=10)
    for a, b in [("CPU", "Control Unit"), ("RAM", "I/O Hub"), ("Bus", "DMA"), ("SSD", "BIOS"), ("BIOS", "Display")]:
        ax, ay, _, ah = centers[a]
        bx, by, _, bh2 = centers[b]
        arrow(d, (ax, ay + ah // 2 + 4), (bx, by - bh2 // 2 - 6), (60, 60, 60), width=2, head=10)
    els.append(text_el(d, (40, 676), "Arrows show the direction data moves between components", font(20), (70, 70, 70),
                       name="caption"))
    save("dense_diagram", img, els, "16 shapes (round/rect/ellipse/diamond) with labels, 3px outlines.")


def dark_slide() -> None:
    """Dark background, light text, filled boxes without outlines, a sun circle, yellow arrows."""
    w, h = 1280, 720
    img = Image.new("RGB", (w, h), (17, 24, 39))
    d = ImageDraw.Draw(img)
    els = [text_el(d, (60, 40), "Photosynthesis in Three Steps", font(42, True), (255, 255, 255), name="title")]
    sun = [1080, 30, 1190, 140]
    d.ellipse(sun, fill=(255, 209, 102))
    els.append({"name": "sun", "kind": "shape", "shape": "ellipse", "box": sun})
    boxes = [
        ([60, 250, 380, 450], "Light absorbed", ["Chlorophyll captures", "energy from sunlight"]),
        ([480, 250, 800, 450], "Water split", ["H2O releases oxygen", "and electrons"]),
        ([900, 250, 1220, 450], "Sugar made", ["CO2 is fixed into", "glucose molecules"]),
    ]
    for box, title, lines in boxes:
        d.rounded_rectangle(box, radius=18, fill=(42, 157, 143))
        els.append({"name": title, "kind": "shape", "shape": "round", "box": box})
        els.append(text_el(d, (box[0] + 24, box[1] + 24), title, font(30, True), (255, 255, 255)))
        for i, line in enumerate(lines):
            els.append(text_el(d, (box[0] + 24, box[1] + 90 + i * 34), line, font(24), (225, 245, 240)))
    arrow(d, (390, 350), (468, 350), (255, 209, 102), width=6, head=18)
    arrow(d, (810, 350), (888, 350), (255, 209, 102), width=6, head=18)
    els.append(text_el(d, (60, 560), "Inputs: carbon dioxide, water and light", font(28), (203, 213, 225)))
    els.append(text_el(d, (60, 606), "Outputs: glucose and oxygen", font(28), (203, 213, 225)))
    save("dark_slide", img, els, "Dark slide: filled boxes (no outline), light text, yellow sun + arrows.")


def bullets_formula() -> None:
    """Bullet list with separate bullet glyphs, a large formula and a small bar chart figure."""
    w, h = 1280, 720
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    els = [text_el(d, (60, 40), "Newton's Second Law", font(44, True), (25, 25, 112), name="title")]
    bullets = [
        "Force causes acceleration",
        "Heavier objects need more force",
        "Acceleration points along the net force",
        "Units: newtons (N) = kg m/s2",
    ]
    fnt = font(26)
    y = 150
    for b in bullets:
        d.ellipse([70, y + 11, 80, y + 21], fill=(40, 40, 40))
        els.append(text_el(d, (96, y), b, fnt, (30, 30, 30)))
        y += 44
    els.append({"name": "bullet list", "kind": "text_block", "box": [96, 150, 600, y - 10]})
    els.append(text_el(d, (760, 170), "F = m \u00d7 a", font(64), (190, 30, 45), name="formula"))
    els.append(text_el(d, (790, 270), "a = F / m", font(40), (60, 60, 60), name="formula 2"))
    # bar chart figure
    ox, oy = 760, 640
    d.line([(ox, 380), (ox, oy)], fill=(30, 30, 30), width=3)
    d.line([(ox, oy), (1200, oy)], fill=(30, 30, 30), width=3)
    for i, hv in enumerate([210, 150, 105, 70]):
        x0 = ox + 30 + i * 100
        d.rectangle([x0, oy - hv, x0 + 60, oy - 2], fill=(25, 113, 194))
    els.append({"name": "bar chart", "kind": "figure", "box": [ox - 2, 380, 1200, oy + 2]})
    els.append(text_el(d, (60, 400), "Same force, bigger mass:", font(26, True), (30, 30, 30)))
    els.append(text_el(d, (60, 444), "smaller acceleration", font(26), (30, 30, 30)))
    els.append(text_el(d, (60, 640), "Chart: acceleration for 1, 2, 3 and 4 kg", font(20), (90, 90, 90), name="caption"))
    save("bullets_formula", img, els, "Bullets with drawn bullet dots, formula text, bar chart figure.")


def _smooth_noise(w: int, h: int, rng: np.random.Generator) -> np.ndarray:
    small = rng.random((h // 24 + 2, w // 24 + 2, 3)).astype(np.float32)
    img = Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    arr = np.asarray(img).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    arr[..., 1] += 40 * np.sin(xx / 23.0) * np.cos(yy / 17.0)
    return np.clip(arr, 0, 255).astype(np.uint8)


def textbook_page() -> None:
    """Paragraph text, a photo-like figure with a caption and a line-drawing figure."""
    w, h = 1200, 1500
    rng = np.random.default_rng(7)
    img = Image.new("RGB", (w, h), (252, 251, 247))
    d = ImageDraw.Draw(img)
    els = [text_el(d, (80, 70), "2.3 The Mitochondrion", font(46, True), (20, 20, 20), name="heading")]
    para = [
        "Mitochondria are the power plants of the cell. They turn the",
        "chemical energy stored in food into ATP, a molecule the cell can",
        "spend on work such as moving, building proteins and dividing.",
        "Each mitochondrion has two membranes: a smooth outer membrane",
        "and a folded inner membrane whose folds are called cristae.",
    ]
    fnt = font(28)
    for i, line in enumerate(para):
        els.append(text_el(d, (80, 170 + i * 44), line, fnt, (30, 30, 30)))
    els.append({"name": "paragraph", "kind": "text_block", "box": [80, 170, 1100, 170 + 5 * 44]})
    photo = Image.fromarray(_smooth_noise(520, 360, rng))
    img.paste(photo, (80, 470))
    els.append({"name": "photo", "kind": "figure", "box": [80, 470, 600, 830]})
    els.append(text_el(d, (80, 850), "Figure 1: A cell under the microscope", font(24), (80, 80, 80), name="caption 1"))
    # line drawing of a mitochondrion: outer ellipse + wavy inner membrane
    cx, cy = 900, 650
    d.ellipse([700, 520, 1100, 780], outline=(120, 60, 20), width=5)
    pts = []
    for i in range(0, 361, 4):
        t = math.radians(i)
        rr = 1.0 + 0.12 * math.sin(7 * t)
        pts.append((cx + 165 * rr * math.cos(t), cy + 95 * rr * math.sin(t)))
    d.line(pts, fill=(200, 90, 40), width=4, joint="curve")
    els.append({"name": "mitochondrion drawing", "kind": "shape", "box": [700, 520, 1100, 780]})
    els.append(text_el(d, (700, 850), "Figure 2: Inner and outer membranes", font(24), (80, 80, 80), name="caption 2"))
    more = [
        "The inner membrane holds the enzymes of the electron transport",
        "chain. Because its folds make the surface much larger, a cell",
        "with many cristae can produce ATP faster.",
    ]
    for i, line in enumerate(more):
        els.append(text_el(d, (80, 960 + i * 44), line, fnt, (30, 30, 30)))
    save("textbook_page", img, els, "Paragraphs, photo-like figure, line drawing (ellipse) with captions.")


def network_photo() -> None:
    """samples/quick/network_basic.png as a phone photo: perspective, blur, uneven light, JPEG, desk."""
    import cv2

    src_path = ROOT / "samples" / "quick" / "network_basic.png"
    src = np.asarray(Image.open(src_path).convert("RGB")).astype(np.float32)
    gt = json.loads((ROOT / "samples" / "quick" / "network_basic.json").read_text(encoding="utf-8"))
    rng = np.random.default_rng(3)
    W, H = 1400, 1000
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    desk = np.zeros((H, W, 3), np.float32)
    grain = 18 * np.sin(yy / 9.0 + 3 * np.sin(xx / 140.0)) + rng.normal(0, 6, (H, W))
    desk[..., 0] = 128 + grain
    desk[..., 1] = 92 + grain * 0.8
    desk[..., 2] = 58 + grain * 0.5
    h0, w0 = src.shape[:2]
    quad_src = np.float32([[0, 0], [w0, 0], [w0, h0], [0, h0]])
    quad_dst = np.float32([[110, 170], [1300, 95], [1335, 880], [80, 905]])
    m = cv2.getPerspectiveTransform(quad_src, quad_dst)
    warped = cv2.warpPerspective(src, m, (W, H), flags=cv2.INTER_LINEAR)
    mask = cv2.warpPerspective(np.ones((h0, w0), np.float32), m, (W, H), flags=cv2.INTER_LINEAR)[..., None]
    paper = warped * np.array([0.97, 0.95, 0.9], np.float32)
    img = paper * mask + desk * (1 - mask)
    light = 0.72 + 0.38 * (xx / W) * 0.6 + 0.4 * (1 - ((xx - 950) ** 2 + (yy - 250) ** 2) / (1400.0 ** 2))
    img = img * np.clip(light, 0.55, 1.08)[..., None]
    img = cv2.GaussianBlur(img, (0, 0), 1.1)
    img = img + rng.normal(0, 3.5, img.shape)
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    els = []
    for el in gt["elements"]:
        x0, y0, x1, y1 = el["box"]
        pts = np.float32([[[x0, y0], [x1, y0], [x1, y1], [x0, y1]]])
        wp = cv2.perspectiveTransform(pts, m)[0]
        box = [int(wp[:, 0].min()), int(wp[:, 1].min()), int(math.ceil(wp[:, 0].max())), int(math.ceil(wp[:, 1].max()))]
        els.append({"name": el["name"], "kind": el["kind"], "box": box})
    save("network_photo", out, els, "network_basic warped into a phone photo; GT = bbox of warped GT corners.", fmt="jpg")


if __name__ == "__main__":
    which = set(sys.argv[1:])
    for fn in (dense_diagram, dark_slide, bullets_formula, textbook_page, network_photo):
        if not which or fn.__name__ in which:
            fn()
