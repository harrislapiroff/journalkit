"""Tests.  Run with ``.venv/bin/python tests/test_pagekit.py`` or pytest."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pagekit import spec  # noqa: E402
from pagekit.geometry import Rect  # noqa: E402
from pagekit.layout import layout_stack  # noqa: E402
from pagekit.modules import build  # noqa: E402
from pagekit.render import RenderContext, Renderer, resolve_placement  # noqa: E402
from pagekit.units import mm, snap  # noqa: E402


def close(a, b, tol=0.01):
    return abs(a - b) < tol


# --------------------------------------------------------------------------
def test_units():
    assert close(mm(5), 5.0)
    assert close(mm("5mm"), 5.0)
    assert close(mm("0.25pt"), 0.0882)
    assert close(mm("1in"), 25.4)
    assert close(mm("1cm"), 10.0)
    assert close(snap(3.1, 2.5), 2.5)
    assert close(snap(3.9, 2.5), 5.0)
    assert close(snap(3.9, 2.5, "floor"), 2.5)
    assert close(snap(2.6, 2.5, "ceil"), 5.0)


def test_geometry():
    r = Rect(10, 20, 30, 40)
    assert (r.right, r.bottom, r.cx, r.cy) == (40, 60, 25, 40)
    assert r.inset(5) == Rect(15, 25, 20, 30)
    assert r.inset(1, 2) == Rect(12, 21, 26, 38)
    assert r.contains_point(11, 21) and not r.contains_point(10, 20)


# --------------------------------------------------------------------------
def _context(**overrides):
    document = spec.load(ROOT / "templates" / "daily.yaml")
    renderer = Renderer(document)
    page, content = renderer.content_rect(document.pages[0])
    defaults = dict(
        theme=document.theme, icons=renderer.icons, grid=document.grid,
        default_gap=document.default_gap, dots=document.dots,
        page=page, content=content, side="right",
    )
    defaults.update(overrides)
    return RenderContext(**defaults)


def test_fill_absorbs_leftover_exactly():
    ctx = _context()
    children = [
        build({"type": "box", "height": 10}, ctx),
        build({"type": "box", "height": "fill"}, ctx),
        build({"type": "box", "height": 20}, ctx),
    ]
    area = Rect(0, 0, 75, 100)
    placements = layout_stack(children, area, 2.5, 2.5, ctx)
    assert close(placements[1].rect.h, 100 - 10 - 20 - 2 * 2.5)
    assert close(placements[-1].rect.bottom, area.bottom), "stack must end on the container edge"
    assert not ctx.warnings


def test_fill_shares_by_weight_and_stays_on_grid():
    ctx = _context()
    children = [
        build({"type": "box", "height": "fill"}, ctx),
        build({"type": "box", "height": "fill", "flex": 2}, ctx),
    ]
    placements = layout_stack(children, Rect(0, 0, 75, 100), 0, 2.5, ctx)
    assert close(placements[0].rect.h + placements[1].rect.h, 100)
    assert close(placements[0].rect.h % 2.5, 0)
    assert placements[1].rect.h > placements[0].rect.h


def test_off_grid_height_is_snapped_and_warned():
    ctx = _context()
    children = [build({"type": "box", "height": 11}, ctx)]
    placements = layout_stack(children, Rect(0, 0, 75, 100), 2.5, 2.5, ctx)
    assert close(placements[0].rect.h, 10.0)
    assert any("grid" in w for w in ctx.warnings)


def test_overflow_warns():
    ctx = _context()
    children = [build({"type": "box", "height": 200}, ctx)]
    layout_stack(children, Rect(0, 0, 75, 100), 2.5, 2.5, ctx)
    assert any("overflow" in w for w in ctx.warnings)


# --------------------------------------------------------------------------
def test_dots_are_page_anchored_and_strictly_inside():
    ctx = _context()
    top = list(ctx.dot_points(Rect(25, 142.5, 75, 20)))
    assert (30.0, 147.5) in [(round(x, 3), round(y, 3)) for x, y in top]
    # Nothing on the boundary: 25 and 100 are lattice columns, 142.5/162.5 rows.
    assert all(25 < x < 100 and 142.5 < y < 162.5 for x, y in top)

    # Two unrelated modules must sample the same lattice.
    other = list(ctx.dot_points(Rect(25, 25, 75, 22.5)))
    xs_a = {round(x, 3) for x, _ in top}
    xs_b = {round(x, 3) for x, _ in other}
    assert xs_a == xs_b
    assert all(close(y % 5, 2.5) for _, y in top + other)


def test_dot_spacing_override_per_module():
    ctx = _context()
    fine = list(ctx.dot_points(Rect(25, 25, 10, 10), spacing=2.5))
    coarse = list(ctx.dot_points(Rect(25, 25, 10, 10)))
    assert len(fine) > len(coarse)


# --------------------------------------------------------------------------
def test_margins_mirror():
    margins = spec.Margins.parse({"top": 2.5, "bottom": 7.5, "inner": 25, "outer": 5})
    assert margins.for_side("right") == (2.5, 5.0, 7.5, 25.0)
    assert margins.for_side("left") == (2.5, 25.0, 7.5, 5.0)


def test_explicit_left_right_disables_mirroring():
    margins = spec.Margins.parse({"left": 12, "right": 8})
    assert margins.for_side("right") == margins.for_side("left")


def test_decoration_anchor_mirrors():
    page = Rect(0, 0, 105, 170)
    recto = Rect(25, 2.5, 75, 160)
    verso = Rect(5, 2.5, 75, 160)
    at = {"x": {"from": "inner", "offset": 5}, "y": 0, "width": 0, "height": "full"}
    assert close(resolve_placement(at, page, recto, "right").x, 20.0)
    assert close(resolve_placement(at, page, verso, "left").x, 85.0)


# --------------------------------------------------------------------------
def _rects(svg: str):
    out = []
    for tag in re.findall(r"<rect [^>]*/>", svg):
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', tag))
        out.append(tuple(round(float(attrs[k]), 2) for k in ("x", "y", "width", "height")))
    return out


def test_daily_matches_the_original_artwork():
    """Key coordinates measured from the source Illustrator file."""
    document = spec.load(ROOT / "templates" / "daily.yaml")
    assert (document.width, document.height) == (105.0, 170.0)

    svg = Renderer(document).render_all()[0][1]
    rects = _rects(svg)
    for expected in [
        (25.0, 2.5, 75.0, 5.0),      # DATE | LOC.
        (25.0, 17.5, 75.0, 5.0),     # morning MOOD
        (25.0, 25.0, 75.0, 22.5),    # morning notes
        (32.5, 50.0, 67.5, 5.0),     # first checklist writing box
        (32.5, 80.0, 67.5, 5.0),     # fifth checklist writing box
        (25.0, 97.5, 75.0, 5.0),     # evening MOOD
        (25.0, 105.0, 75.0, 35.0),   # evening notes (height: fill)
        (25.0, 142.5, 75.0, 20.0),   # gratitude
    ]:
        assert expected in rects, "missing %r" % (expected,)

    assert '<line x1="20"' in svg.replace("20.0", "20"), "binding rule at x=20"
    assert "Montserrat" in svg


def test_back_page_is_mirrored():
    document = spec.load(ROOT / "templates" / "daily.yaml")
    svg = Renderer(document).render_all()[1][1]
    assert (5.0, 2.5, 75.0, 160.0) in _rects(svg)


def test_custom_module_registers():
    document = spec.load(ROOT / "templates" / "weekly.yaml")
    from pagekit.modules import REGISTRY

    assert "habit_grid" in REGISTRY
    pages = Renderer(document).render_all()
    assert len(pages) == 2
    assert "MOVE" in pages[0][1]


def test_repeat_expands_pages(tmp_path=None):
    import tempfile

    source = """
document: rep
page: {size: a6, margins: {all: 10}}
templates:
  plain: {content: [{type: box, height: fill}]}
pages:
  - {template: plain, repeat: 3}
"""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
        handle.write(source)
        path = handle.name
    document = spec.load(path)
    assert len(document.pages) == 3
    assert document.pages[0].name == "plain-01"


# --------------------------------------------------------------------------
if __name__ == "__main__":
    failures = 0
    for name, function in sorted(globals().items()):
        if not name.startswith("test_") or not callable(function):
            continue
        try:
            function()
            print("ok   %s" % name)
        except AssertionError as exc:
            failures += 1
            print("FAIL %s: %s" % (name, exc))
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print("ERR  %s: %s: %s" % (name, type(exc).__name__, exc))
    print("\n%s" % ("all tests passed" if not failures else "%d failure(s)" % failures))
    raise SystemExit(1 if failures else 0)
