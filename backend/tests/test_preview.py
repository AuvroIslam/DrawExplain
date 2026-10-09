"""Preview renderer: synthetic steps -> pixels change exactly where the geometry says."""
from __future__ import annotations

from PIL import Image

from app.render.preview import PALETTE, render_lesson
from app.schemas import Annotation, Box, Geometry, Point, Region, Step

W, H = 400, 300


def _rgb(name: str) -> tuple[int, int, int]:
    v = PALETTE[name].lstrip("#")
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def _near(px: tuple[int, ...], color: tuple[int, int, int], tol: int = 12) -> bool:
    return all(abs(int(a) - b) <= tol for a, b in zip(px[:3], color))


WHITE = (255, 255, 255)


def _steps() -> list[Step]:
    s1 = Step(index=1, title="Shapes", narration="Look here.", annotations=[
        Annotation(id="s1a1", kind="circle", color="red", geometry=Geometry(box=Box(x=0.1, y=0.1, w=0.3, h=0.3))),
        Annotation(id="s1a2", kind="box", color="blue", geometry=Geometry(box=Box(x=0.55, y=0.1, w=0.3, h=0.2))),
    ])
    s2 = Step(index=2, title="Marks", narration="And here.", annotations=[
        Annotation(id="s2a1", kind="highlight", color="orange", geometry=Geometry(box=Box(x=0.1, y=0.6, w=0.3, h=0.1))),
        Annotation(id="s2a2", kind="underline", color="green", geometry=Geometry(points=[Point(x=0.55, y=0.5), Point(x=0.9, y=0.5)])),
        Annotation(id="s2a3", kind="arrow", color="purple", geometry=Geometry(points=[
            Point(x=0.2, y=0.9), Point(x=0.5, y=0.75), Point(x=0.8, y=0.9)])),
        Annotation(id="s2a4", kind="label", color="blue", text="Router", geometry=Geometry(
            box=Box(x=0.55, y=0.1, w=0.3, h=0.2),
            label_box=Box(x=0.6, y=0.62, w=0.3, h=0.1),
            leader=[Point(x=0.75, y=0.62), Point(x=0.7, y=0.3)])),
    ])
    return [s1, s2]


def _blank() -> Image.Image:
    return Image.new("RGB", (W, H), "white")


def test_all_kinds_are_drawn_where_the_geometry_says() -> None:
    out = render_lesson(_blank(), _steps())
    assert out.size == (W, H) and out.mode == "RGB"
    px = out.load()
    stroke = max(3, round(0.004 * max(W, H)))
    # circle: on the ellipse outline (left/right middle), not in its centre
    assert _near(px[0.1 * W + stroke // 2, 0.25 * H], _rgb("red"))
    assert _near(px[0.4 * W - 1 - stroke // 2, 0.25 * H], _rgb("red"))
    assert px[0.25 * W, 0.25 * H] == WHITE
    # box: on the left edge, centre empty
    assert _near(px[0.55 * W + 1, 0.2 * H], _rgb("blue"))
    assert px[0.7 * W, 0.2 * H] == WHITE
    # highlight: translucent orange fill (tinted, not opaque)
    hl = px[0.25 * W, 0.65 * H]
    assert hl != WHITE and not _near(hl, _rgb("orange"), tol=4)
    assert hl[0] > hl[2] + 40  # orange tint: much more red than blue
    # underline: green along y = 0.5
    assert _near(px[0.7 * W, 0.5 * H], _rgb("green"))
    # arrow: quadratic Bezier midpoint 0.25*P0 + 0.5*P1 + 0.25*P2
    mid = (0.25 * 0.2 + 0.5 * 0.5 + 0.25 * 0.8) * W, (0.25 * 0.9 + 0.5 * 0.75 + 0.25 * 0.9) * H
    assert _near(px[mid[0], mid[1]], _rgb("purple"))
    # arrowhead: purple pixels just behind the end point, off the curve
    end = (0.8 * W, 0.9 * H)
    assert any(_near(px[end[0] - dx, end[1] - dy], _rgb("purple")) for dx in range(4, 14) for dy in range(4, 14))
    # label text inside its label_box, leader line between its points
    label = [px[x, y] for x in range(int(0.6 * W), int(0.9 * W)) for y in range(int(0.62 * H), int(0.72 * H))]
    assert sum(_near(p, _rgb("blue"), tol=30) for p in label) > 40
    assert _near(px[0.725 * W, 0.46 * H], _rgb("blue"), tol=30)
    # untouched corner
    assert px[W - 3, H // 2] == WHITE


def test_upto_limits_steps_and_badges_are_drawn() -> None:
    only_first = render_lesson(_blank(), _steps(), upto=1).load()
    assert _near(only_first[0.1 * W + 2, 0.25 * H], _rgb("red"))
    assert only_first[0.7 * W, 0.5 * H] == WHITE  # step 2 underline absent
    assert only_first[0.25 * W, 0.65 * H] == WHITE  # step 2 highlight absent
    # step badge (filled red disc) just outside the circle's top-left corner
    badge = [only_first[x, y] for x in range(10, 44) for y in range(4, 34)]
    assert sum(_near(p, _rgb("red"), tol=20) for p in badge) > 80
    assert render_lesson(_blank(), _steps(), upto=0).tobytes() == _blank().tobytes()


def test_regions_are_outlined_faintly() -> None:
    regions = [Region(id="R1", kind="shape", box=Box(x=0.05, y=0.8, w=0.2, h=0.15))]
    px = render_lesson(_blank(), [], regions=regions).load()
    edge = px[0.15 * W, 0.8 * H]
    assert edge != WHITE and min(edge) > 100  # grey, faint
    assert px[0.15 * W, 0.87 * H] == WHITE


def test_original_image_is_untouched_and_dict_steps_work() -> None:
    base = _blank()
    before = base.tobytes()
    out = render_lesson(base, [s.model_dump() for s in _steps()])
    assert base.tobytes() == before
    assert out.tobytes() != before


def test_incomplete_geometry_does_not_crash() -> None:
    steps = [Step(index=1, title="t", narration="n", annotations=[
        Annotation(id="a", kind="circle", geometry=Geometry()),
        Annotation(id="b", kind="arrow", geometry=Geometry(points=[Point(x=0.1, y=0.1)])),
        Annotation(id="c", kind="arrow", geometry=Geometry(points=[Point(x=0.1, y=0.5), Point(x=0.9, y=0.5)])),
        Annotation(id="d", kind="underline", geometry=Geometry(box=Box(x=0.1, y=0.2, w=0.5, h=0.1))),
        Annotation(id="e", kind="label", text="Note", geometry=Geometry(box=Box(x=0.3, y=0.7, w=0.2, h=0.1))),
    ])]
    px = render_lesson(_blank(), steps).load()
    assert _near(px[0.5 * W, 0.5 * H], _rgb("red"))  # 2-point arrow drawn straight
    assert _near(px[0.35 * W, 0.3 * H], _rgb("red"))  # underline along the box bottom
