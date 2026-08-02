"""Turning a :class:`~pagekit.spec.Document` into SVG pages."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .geometry import Rect
from .icons import IconSet
from .layout import layout_stack
from .modules import build
from .svg import Canvas
from .units import mm, snap


@dataclass
class RenderContext:
    """Everything a module can see beyond its own spec."""

    theme: object
    icons: IconSet
    grid: float
    default_gap: float
    dots: object
    page: Rect
    content: Rect
    side: str
    debug: bool = False
    warnings: list = field(default_factory=list)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    # -- the page-wide dot lattice ----------------------------------------
    def dot_points(self, rect: Rect, spacing=None, origin=None, inset=0.0):
        """Lattice points strictly inside ``rect``.

        The lattice is anchored to the *page*, not to the module, which is what
        keeps dots lined up across every module on the page.
        """
        spacing = spacing or self.dots.spacing
        ox, oy = origin or self.dots.origin
        area = rect.inset(inset) if inset else rect
        first_i = math.ceil((area.x - ox) / spacing - 1e-9)
        last_i = math.floor((area.right - ox) / spacing + 1e-9)
        first_j = math.ceil((area.y - oy) / spacing - 1e-9)
        last_j = math.floor((area.bottom - oy) / spacing + 1e-9)
        for j in range(first_j, last_j + 1):
            y = oy + j * spacing
            if not (area.y < y < area.bottom):
                continue
            for i in range(first_i, last_i + 1):
                x = ox + i * spacing
                if area.x < x < area.right:
                    yield x, y

    def draw_dots(self, canvas: Canvas, rect: Rect, options=None) -> None:
        config = options if isinstance(options, dict) else {}
        spacing = mm(config["spacing"]) if "spacing" in config else None
        radius = mm(config.get("radius", self.dots.radius))
        colour = config.get("colour", config.get("color", self.dots.colour))
        opacity = float(config.get("opacity", self.dots.opacity))
        inset = mm(config.get("inset", self.dots.inset))
        origin = config.get("origin")
        if origin is not None:
            origin = (mm(origin[0]), mm(origin[1]))

        points = list(self.dot_points(rect, spacing, origin, inset))
        if not points:
            return
        canvas.open_group(fill=colour, fill_opacity=None if opacity >= 1 else opacity)
        for x, y in points:
            canvas.circle(x, y, radius)
        canvas.close_group()


def _anchor_x(name, offset, page: Rect, content: Rect, side: str) -> float:
    """Resolve a horizontal anchor.

    For ``inner``/``outer`` a positive offset moves *away from the text block
    towards the nearer page edge*, so a decoration mirrors correctly between a
    recto and a verso without changing its spec.
    """
    binding_left = side != "left"
    table = {
        "left": page.x + offset,
        "right": page.right - offset,
        "center": page.cx + offset,
        "content_left": content.x + offset,
        "content_right": content.right - offset,
        "content_center": content.cx + offset,
        "inner": (content.x - offset) if binding_left else (content.right + offset),
        "outer": (content.right + offset) if binding_left else (content.x - offset),
    }
    if name not in table:
        raise ValueError("unknown x anchor %r (known: %s)" % (name, ", ".join(sorted(table))))
    return table[name]


def _anchor_y(name, offset, page: Rect, content: Rect) -> float:
    table = {
        "top": page.y + offset,
        "bottom": page.bottom - offset,
        "middle": page.cy + offset,
        "content_top": content.y + offset,
        "content_bottom": content.bottom - offset,
        "content_middle": content.cy + offset,
    }
    if name not in table:
        raise ValueError("unknown y anchor %r (known: %s)" % (name, ", ".join(sorted(table))))
    return table[name]


def _coord(value, axis, page, content, side, default):
    if value is None:
        return default
    if isinstance(value, dict):
        anchor = value.get("from", "left" if axis == "x" else "top")
        offset = mm(value.get("offset", 0))
        if axis == "x":
            return _anchor_x(anchor, offset, page, content, side)
        return _anchor_y(anchor, offset, page, content)
    if isinstance(value, str):
        if axis == "x":
            return _anchor_x(value, 0.0, page, content, side)
        return _anchor_y(value, 0.0, page, content)
    return mm(value)


def _extent(value, page_extent, content_extent, default):
    if value is None:
        return default
    if value == "full":
        return page_extent
    if value == "content":
        return content_extent
    return mm(value)


def resolve_placement(at: dict | None, page: Rect, content: Rect, side: str) -> Rect:
    """Turn a decoration's ``at:`` mapping into a page-space rect."""
    at = at or {}
    x = _coord(at.get("x"), "x", page, content, side, content.x)
    y = _coord(at.get("y"), "y", page, content, side, content.y)
    w = _extent(at.get("width"), page.w, content.w, content.right - x)
    h = _extent(at.get("height"), page.h, content.h, content.bottom - y)
    return Rect(x, y, w, h)


class Renderer:
    def __init__(self, document, debug: bool = False, background: str | None = "#ffffff"):
        self.doc = document
        self.debug = debug
        self.background = background
        self.icons = IconSet(document.icon_dirs)
        self.warnings: list[str] = []

    def content_rect(self, page_spec) -> tuple[Rect, Rect]:
        page = Rect(0.0, 0.0, self.doc.width, self.doc.height)
        margins = page_spec.margins or self.doc.margins
        top, right, bottom, left = margins.for_side(page_spec.side)
        content = Rect(left, top, self.doc.width - left - right, self.doc.height - top - bottom)
        return page, content

    def render_page(self, page_spec) -> tuple[Canvas, RenderContext]:
        page, content = self.content_rect(page_spec)
        theme = self.doc.theme.derive(page_spec.theme)
        ctx = RenderContext(
            theme=theme,
            icons=self.icons,
            grid=self.doc.grid,
            default_gap=page_spec.gap if page_spec.gap is not None else self.doc.default_gap,
            dots=self.doc.dots,
            page=page,
            content=content,
            side=page_spec.side,
            debug=self.debug,
        )

        canvas = Canvas(self.doc.width, self.doc.height, self.background)
        if self.debug:
            self._draw_debug(canvas, ctx, page, content)

        decorations = list(self.doc.decorations) + list(page_spec.decorations)
        self._draw_decorations(canvas, ctx, decorations, page, content, above=False)

        if page_spec.content:
            canvas.comment("content")
            children = [build(spec, ctx) for spec in page_spec.content]
            for placement in layout_stack(children, content, ctx.default_gap, ctx.grid, ctx):
                placement.module.draw(canvas, placement.rect)

        self._draw_decorations(canvas, ctx, decorations, page, content, above=True)

        for message in ctx.warnings:
            self.warnings.append("%s: %s" % (page_spec.name, message))
        return canvas, ctx

    def _draw_decorations(self, canvas, ctx, decorations, page, content, above) -> None:
        selected = [d for d in decorations if bool(d.get("above", False)) == above]
        if not selected:
            return
        canvas.comment("decorations (%s content)" % ("above" if above else "below"))
        for spec in selected:
            spec = dict(spec)
            at = spec.pop("at", None)
            if "edge" in spec:  # shorthand: a full-length rule beside an edge
                edge = spec.pop("edge")
                offset = spec.pop("offset", 0)
                if edge in ("inner", "outer", "left", "right", "center"):
                    at = {"x": {"from": edge, "offset": offset}, "y": 0, "width": 0, "height": "full"}
                    spec.setdefault("orientation", "vertical")
                else:
                    at = {"y": {"from": edge, "offset": offset}, "x": 0, "height": 0, "width": "full"}
            spec.pop("above", None)
            rect = resolve_placement(at, page, content, ctx.side)
            build(spec, ctx).draw(canvas, rect)

    def _draw_debug(self, canvas, ctx, page, content) -> None:
        canvas.comment("debug overlay")
        canvas.open_group(stroke="#7fb2ff", stroke_width=0.05, fill="none")
        step = self.doc.grid
        x = snap(page.x, step, "ceil")
        while x <= page.right + 1e-9:
            canvas.line(x, 0, x, page.h)
            x += step
        y = snap(page.y, step, "ceil")
        while y <= page.bottom + 1e-9:
            canvas.line(0, y, page.w, y)
            y += step
        canvas.close_group()
        canvas.rect(content.x, content.y, content.w, content.h,
                    fill="none", stroke="#ff5f9e", stroke_width=0.15, stroke_dasharray="1 1")

    def render_all(self) -> list[tuple[str, str]]:
        """Render every page; returns ``[(page_name, svg_text), ...]``."""
        out = []
        for index, page_spec in enumerate(self.doc.pages, start=1):
            canvas, _ = self.render_page(page_spec)
            title = "%s / %s" % (self.doc.name, page_spec.name)
            out.append(("%02d-%s" % (index, page_spec.name), canvas.to_svg(title)))
        return out
