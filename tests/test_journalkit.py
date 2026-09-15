"""Tests.  Run with ``.venv/bin/python tests/test_journalkit.py`` or pytest.

The example journal in ``examples/journal`` doubles as the fixture project.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "examples" / "journal"
sys.path.insert(0, str(ROOT))

from journalkit import spec  # noqa: E402
from journalkit.geometry import Rect  # noqa: E402
from journalkit.layout import layout_stack  # noqa: E402
from journalkit.modules import build  # noqa: E402
from journalkit.render import RenderContext, Renderer, resolve_placement  # noqa: E402
from journalkit.project import Project  # noqa: E402
from journalkit.units import mm, snap  # noqa: E402


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
    """A context for testing the *engine*, on a lattice of its own.

    The theme and icon set come from daily.yaml because it is a convenient
    source of both, but the grid and dot lattice are pinned here rather than
    inherited. The tests below assert specific lattice coordinates (27.5,
    32.5, …) to check the dot machinery; if they rode on the template, every
    redesign of the notebook would break tests that have nothing to do with
    the notebook.
    """
    document = spec.load(EXAMPLE / "templates" / "daily.yaml")
    renderer = Renderer(document)
    page, content = renderer.content_rect(document.pages[0])
    defaults = dict(
        theme=document.theme, icons=renderer.icons, grid=2.5,
        default_gap=2.5, dots=spec.DotGrid(spacing=5.0, origin=(0.0, 2.5)),
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


def test_intrinsic_height_is_snapped_without_warning():
    """Only a size the author wrote is worth complaining about.

    A heading's intrinsic 7.5mm cannot sit on a 2mm grid, and no template can
    fix that — warning about it would put an unactionable line under every
    heading on a 2mm page.
    """
    ctx = _context(grid=2.0)
    children = [build({"type": "heading", "text": "MORNING"}, ctx)]
    placements = layout_stack(children, Rect(0, 0, 84, 100), 2.0, 2.0, ctx)
    assert close(placements[0].rect.h, 8.0), "still snapped to the grid"
    assert not ctx.warnings, "but silently: the template did not choose 7.5"

    # An explicit height on the same grid still warns.
    ctx = _context(grid=2.0)
    layout_stack([build({"type": "heading", "text": "M", "height": 7}, ctx)],
                 Rect(0, 0, 84, 100), 2.0, 2.0, ctx)
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


def test_dots_keep_clear_of_a_label():
    """A dot must never land in the ink of the label above it."""
    ctx = _context()
    # A box whose first lattice row (y=27.5) falls inside the label's cap band.
    # State the mode explicitly: the document's own theme may choose either.
    module = build({"type": "box", "label": "NOTES/REFLECTION", "dots": True,
                    "theme": {"dots": {"reserve_label": "band"}}}, ctx)
    rect = Rect(25, 25, 75, 22.5)

    band = module.label_band(rect)
    assert band is not None
    baseline = rect.y + ctx.theme.mm("label.dy")
    assert band.y < baseline - module.cap_height("label") + 1e-9, "band must cover the cap"
    assert band.bottom > baseline, "band must cover the baseline"

    rows = {round(y, 2) for _, y in ctx.dot_points(rect)}
    kept = {round(y, 2) for _, y in ctx.dot_points(rect, exclude=[band])}
    assert 27.5 in rows and 27.5 not in kept, "the colliding row should be dropped"
    assert kept == {32.5, 37.5, 42.5}, "every other row must survive untouched"


def test_label_clearance_does_not_over_reach():
    """A label that already clears the first dot row must cost no dots."""
    ctx = _context()
    module = build({"type": "box", "label": "GRATITUDE", "dots": True,
                    "theme": {"dots": {"reserve_label": "band"}}}, ctx)
    rect = Rect(25, 142.5, 75, 20)
    band = module.label_band(rect)
    rows = {round(y, 2) for _, y in ctx.dot_points(rect)}
    kept = {round(y, 2) for _, y in ctx.dot_points(rect, exclude=[band])}
    assert rows == kept == {147.5, 152.5, 157.5}


def test_unlabelled_module_reserves_nothing():
    ctx = _context()
    module = build({"type": "box", "dots": True,
                    "theme": {"dots": {"reserve_label": "band"}}}, ctx)
    assert module.label_band(Rect(25, 25, 75, 22.5)) is None


def test_label_clearance_modes():
    ctx = _context()
    rect = Rect(25, 25, 75, 22.5)

    wide = build({"type": "box", "label": "MOOD", "dots": True,
                  "theme": {"dots": {"reserve_label": "band"}}}, ctx)
    narrow = build({"type": "box", "label": "MOOD", "dots": True,
                    "theme": {"dots": {"reserve_label": "text"}}}, ctx)
    off = build({"type": "box", "label": "MOOD", "dots": True,
                 "theme": {"dots": {"reserve_label": "none"}}}, ctx)

    assert close(wide.label_band(rect).w, rect.w), "band spans the module"
    assert narrow.label_band(rect).w < rect.w, "text mode is narrower"
    assert off.label_band(rect) is None

    # Only the horizontal extent differs; both clear the same line.
    assert close(wide.label_band(rect).y, narrow.label_band(rect).y)
    # Text mode must still be wide enough to cover the drawn glyphs.  MOOD is
    # the case a character-count estimate gets wrong: measured ink is 9.34mm
    # but 4 chars x 0.75em is only 8.47mm, so an estimate would under-reserve.
    assert narrow.label_band(rect).w > 9.34


def test_bundled_font_is_found_first():
    """The default family resolves to the copy inside the package, wherever
    the build runs and whatever else is installed."""
    from journalkit import fontmetrics

    for weight in (400, 500, 700):
        metrics = fontmetrics.load("Montserrat", weight)
        assert metrics is not None
        assert fontmetrics.BUNDLED_FONTS in metrics.path.parents, metrics.path
        assert metrics.has_outlines


def test_text_is_drawn_as_outlines():
    """No <text> in the output: the page depends on no installed font."""
    document = spec.load(EXAMPLE / "templates" / "daily.yaml")
    pages = Renderer(document).render_all()
    for _, svg in pages:
        assert "<text" not in svg
        assert "<path" in svg

    from journalkit import fontmetrics
    metrics = fontmetrics.load("Montserrat", 500)
    size = mm("8pt")
    d = metrics.outline("MOOD", size)
    assert d.startswith("M") and "Q" in d and d.count("Z") >= 4, "four closed glyph contours at least"
    # Anchors shift the whole run: an end-anchored path ends at the origin.
    xs = [float(v) for v in re.findall(r"[ML](-?[\d.]+) ", metrics.outline("MOOD", size, anchor="end"))]
    assert max(xs) <= 0.05 and min(xs) < -8
    # Advance width is unchanged by outlining.
    assert close(metrics.text_width("MOOD", size), 9.5, 0.3)


def test_outline_can_be_switched_off():
    ctx = _context()
    module = build({"type": "text", "text": "HELLO", "theme": {"font": {"outline": False}}}, ctx)
    from journalkit.svg import Canvas
    canvas = Canvas(100, 100)
    module.draw(canvas, Rect(0, 0, 50, 5))
    svg = canvas.to_svg()
    assert "<text" in svg and "Montserrat" in svg


def test_font_metrics_are_read_from_the_font():
    from journalkit import fontmetrics

    metrics = fontmetrics.load("Montserrat", 500)
    assert metrics is not None, "bundled, so always present"
    assert metrics.units_per_em == 1000
    # Montserrat's published cap height, from the OS/2 table.
    assert close(metrics.cap_ratio, 0.7, 0.001)

    size = mm("8pt")
    # Measured from Inkscape's rendered ink, which excludes side bearings, so
    # the advance width must be a little wider than each of these.
    for text, ink in [("DATE", 7.36), ("MOOD", 9.34),
                      ("NOTES/REFLECTION", 28.85), ("GRATITUDE", 16.51)]:
        width = metrics.text_width(text, size)
        assert width > ink, "%s: advance %.2f must cover ink %.2f" % (text, width, ink)
        assert width < ink + 1.5, "%s: advance %.2f is far too generous" % (text, width)


def test_unknown_font_falls_back_without_raising():
    from journalkit import fontmetrics

    assert fontmetrics.load("NoSuchFamilyXYZ", 400) is None

    ctx = _context()
    module = build({"type": "box", "label": "MOOD", "dots": True,
                    "theme": {"font": {"family": "NoSuchFamilyXYZ"},
                              "dots": {"reserve_label": "text"}}}, ctx)
    band = module.label_band(Rect(25, 25, 75, 22.5))
    assert band is not None and band.w > 0, "must still reserve something"
    assert close(module.cap_ratio("label"), 0.7), "falls back to the default ratio"


def test_dot_spacing_override_per_module():
    ctx = _context()
    fine = list(ctx.dot_points(Rect(25, 25, 10, 10), spacing=2.5))
    coarse = list(ctx.dot_points(Rect(25, 25, 10, 10)))
    assert len(fine) > len(coarse)


# --------------------------------------------------------------------------
def test_ink_recolours_every_role():
    """One `ink` value stands behind stroke, text, dots and rules."""
    from journalkit.theme import Theme

    roles = ["stroke", "label.colour", "heading.colour", "dots.colour", "lines.colour"]

    default = Theme()
    assert all(default.get(r) == "#231F20" for r in roles), "defaults unchanged"

    black = Theme({"ink": "#000"})
    assert all(black.get(r) == "#000" for r in roles)

    # An individual role can still be pinned without disturbing the others.
    mixed = Theme({"ink": "#000", "dots": {"colour": "#999"}})
    assert mixed.get("dots.colour") == "#999"
    assert mixed.get("stroke") == "#000"
    assert mixed.get("label.colour") == "#000"


def test_theme_indirection_is_general_and_guards_cycles():
    from journalkit.theme import Theme

    theme = Theme({"accent": "#c00", "heading": {"colour": "$theme.accent"}})
    assert theme.get("heading.colour") == "#c00"

    # A chain resolves all the way down.
    chained = Theme({"a": "#123", "b": "$theme.a", "stroke": "$theme.b"})
    assert chained.get("stroke") == "#123"

    looped = Theme({"stroke": "$theme.ink", "ink": "$theme.stroke"})
    try:
        looped.get("stroke")
    except ValueError as exc:
        assert "circular" in str(exc)
    else:
        raise AssertionError("a circular reference must raise, not hang")


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


def test_back_page_is_mirrored():
    """The verso must be the recto's mirror image, whatever it contains.

    Every figure is derived from the document, so redesigning the notebook —
    its margins, its grid, its page size — cannot break this test. Only the
    mirroring actually failing can.
    """
    document = spec.load(EXAMPLE / "templates" / "daily.yaml")
    renderer = Renderer(document)
    _, front_content = renderer.content_rect(document.pages[0])
    _, back_content = renderer.content_rect(document.pages[1])
    pages = renderer.render_all()
    front, back = pages[0][1], pages[1][1]

    # Same text block, reflected: the recto's left margin is the verso's right.
    assert close(front_content.w, back_content.w)
    assert close(front_content.x, document.width - back_content.right)
    assert close(back_content.x, document.width - front_content.right)

    # Content block: gutter on the left of a recto, on the right of a verso.
    width = front_content.w
    front_rects = [r for r in _rects(front) if close(r[2], width)]
    back_rects = [r for r in _rects(back) if close(r[2], width)]
    assert front_rects and back_rects
    assert all(close(r[0], front_content.x) for r in front_rects), "recto starts at the gutter"
    assert all(close(r[0], back_content.x) for r in back_rects), "verso starts at the outer edge"

    # The binding rule mirrors with it, at equal distances from opposite edges.
    rule = re.compile(r'<line x1="([\d.]+)"')
    front_rule = float(rule.search(front).group(1))
    back_rule = float(rule.search(back).group(1))
    assert close(front_rule, document.width - back_rule)
    assert front_rule < front_content.x, "the rule sits in the binding margin"


def test_habit_grid_is_built_in():
    """The tracker needs no `modules:` key — it ships with journalkit."""
    from journalkit.modules import REGISTRY

    assert "habit_grid" in REGISTRY
    document = spec.load(EXAMPLE / "templates" / "weekly.yaml")
    # Render with <text> rather than outlines so the labels can be read back.
    document.theme = document.theme.derive({"font": {"outline": False}})
    pages = Renderer(document).render_all()
    assert len(pages) == 2

    # Whatever the template calls its habits, the grid draws the named ones.
    # Derived from the document, so renaming a habit is not a test failure.
    grids = [m for page in document.pages for m in page.content
             if isinstance(m, dict) and m.get("type") == "habit_grid"]
    assert grids, "weekly.yaml has no habit grid to check"
    named = [h for h in grids[0].get("habits", []) if h]
    assert named, "the habit grid has no named rows to check"
    for habit in named:
        assert habit in pages[0][1]


# --------------------------------------------------------------------------
def test_project_locate():
    daily = EXAMPLE / "templates" / "daily.yaml"
    assert Project.locate(EXAMPLE).root == EXAMPLE, "a directory is itself"
    assert Project.locate(daily).root == EXAMPLE, "a file in templates/ climbs out of it"
    assert Project.locate(ROOT / "pyproject.toml").root == ROOT, "a bare file: its directory"
    assert Project.locate(EXAMPLE).templates() == sorted((EXAMPLE / "templates").glob("*.yaml"))


def _scaffold(tmp: Path) -> Path:
    from journalkit import cli

    target = tmp.resolve() / "journal"
    assert cli.cmd_init(argparse.Namespace(directory=str(target)), log=lambda _: None) == 0
    return target


def test_init_scaffolds_and_never_overwrites():
    import tempfile
    from journalkit import cli

    with tempfile.TemporaryDirectory() as tmp:
        target = _scaffold(Path(tmp))
        assert (target / "templates" / "daily.yaml").is_file()
        assert (target / "modules" / "stamp.py").is_file()
        (target / "templates" / "daily.yaml").write_text("document: mine\n")
        assert cli.cmd_init(argparse.Namespace(directory=str(target)), log=lambda _: None) == 0
        assert (target / "templates" / "daily.yaml").read_text() == "document: mine\n"


def test_project_modules_autoload():
    """modules/*.py register their types with no `modules:` key in the YAML."""
    import tempfile
    from journalkit.modules import REGISTRY

    with tempfile.TemporaryDirectory() as tmp:
        target = _scaffold(Path(tmp))
        loaded = Project(target).load_modules()
        assert [p.name for p in loaded] == ["stamp.py"]
        assert "stamp" in REGISTRY
        # Loading again — a second document in the same process — must not
        # trip the registry's duplicate check.
        Project(target).load_modules()

        document = spec.load(target / "templates" / "daily.yaml")
        assert document.project.root == target
        pages = Renderer(document).render_all()
        assert any('stroke-dasharray' in svg for _, svg in pages), "the stamp drew its dashes"


def test_packaged_icons_resolve_without_project_icons_dir():
    """The example has no icons/; `icon: sunrise` must come from the package."""
    assert not (EXAMPLE / "icons").exists()
    document = spec.load(EXAMPLE / "templates" / "daily.yaml")
    assert document.icon_dirs[-1] == spec.BUILTIN_ICONS
    renderer = Renderer(document)
    assert "sunrise" in renderer.icons.names()
    icon = renderer.icons.get("sunrise")
    assert icon.vw > 0 and icon.vh > 0


def test_build_writes_into_project_out():
    import tempfile
    from journalkit import cli

    with tempfile.TemporaryDirectory() as tmp:
        target = _scaffold(Path(tmp))
        assert cli.main(["build", str(target)]) == 0
        written = sorted(p.name for p in (target / "out").glob("*.svg"))
        assert written == ["daily-01-front.svg", "daily-02-back.svg"]
        # -o redirects, and a single file works as a source too.
        elsewhere = Path(tmp) / "elsewhere"
        assert cli.main(["build", str(target / "templates" / "daily.yaml"), "-o", str(elsewhere)]) == 0
        assert sorted(p.name for p in elsewhere.glob("*.svg")) == written


def test_grid_check_passes_on_the_example():
    from journalkit.checks import check_grid

    lines = []
    violations = check_grid(Project(EXAMPLE).templates(), out=lines.append)
    assert violations == 0, "\n".join(lines)
    assert any("placements checked" in line for line in lines)


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
