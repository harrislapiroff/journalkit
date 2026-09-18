"""The built-in module library."""

from __future__ import annotations

from ..geometry import Rect
from ..units import mm
from .base import Module, register

_SIDES = ("top", "right", "bottom", "left")


def _border_sides(value) -> tuple:
    """``true`` / ``false`` / ``"top bottom"`` / ``["left"]`` -> side tuple."""
    if value is None or value is True or value == "all":
        return _SIDES
    if value is False or value == "none":
        return ()
    if isinstance(value, str):
        value = value.replace(",", " ").split()
    return tuple(s for s in value if s in _SIDES)


class _Framed(Module):
    """Shared behaviour: an optional frame, an optional label, optional dots."""

    def frame(self, canvas, rect):
        sides = _border_sides(self.spec.get("border", True))
        background = self.opt("background", "none")
        radius = self.length("radius", 0) or 0
        if background and background != "none":
            canvas.rect(rect.x, rect.y, rect.w, rect.h, fill=background,
                        rx=radius or None, ry=radius or None, stroke="none")
        if not sides:
            return
        if sides == _SIDES:
            canvas.rect(
                rect.x, rect.y, rect.w, rect.h,
                fill="none", stroke=self.stroke, stroke_width=self.stroke_width,
                rx=radius or None, ry=radius or None,
            )
            return
        edges = {
            "top": (rect.x, rect.y, rect.right, rect.y),
            "bottom": (rect.x, rect.bottom, rect.right, rect.bottom),
            "left": (rect.x, rect.y, rect.x, rect.bottom),
            "right": (rect.right, rect.y, rect.right, rect.bottom),
        }
        for side in sides:
            x1, y1, x2, y2 = edges[side]
            canvas.line(x1, y1, x2, y2, stroke=self.stroke, stroke_width=self.stroke_width)


@register("box")
class Box(_Framed):
    """A bordered writing area with an optional top-left label."""

    params = {
        "label": "small caps label drawn inside the top-left corner",
        "height": "mm, or 'fill' to absorb leftover space",
        "dots": "true, or a mapping to override radius/colour/inset",
        "border": "true | false | 'top bottom' | ['left','right']",
        "theme": "per-module overrides, e.g. {dots: {reserve_label: text}}",
        "background": "fill colour behind the box (default none)",
        "radius": "corner radius in mm",
        "stroke": "border colour (default theme.stroke)",
        "stroke_width": "border weight (default theme.stroke_width)",
    }

    def draw(self, canvas, rect):
        self.frame(canvas, rect)
        self.draw_dots(canvas, rect)
        self.draw_label(canvas, rect)


@register("dotfield")
class DotField(Box):
    """Bare dot grid, no border.  ``box`` with the frame turned off."""

    def draw(self, canvas, rect):
        self.spec.setdefault("border", False)
        self.spec.setdefault("dots", True)
        super().draw(canvas, rect)


@register("fields")
class Fields(_Framed):
    """A single framed row divided into labelled cells (DATE | LOC.)."""

    params = {
        "columns": "list of labels, or mappings {label, width, align}",
        "height": "row height in mm (default 5)",
        "dots": "dot grid inside the row",
    }

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx)
        self.columns = []
        for column in spec.get("columns", []):
            if isinstance(column, str):
                column = {"label": column}
            self.columns.append(column)

    def natural_height(self, width):
        return 5.0

    def _widths(self, total):
        fixed, flexible = {}, []
        for index, column in enumerate(self.columns):
            if column.get("width") not in (None, "fill"):
                fixed[index] = mm(column["width"])
            else:
                flexible.append(index)
        leftover = total - sum(fixed.values())
        share = leftover / len(flexible) if flexible else 0.0
        return [fixed.get(i, share) for i in range(len(self.columns))]

    def draw(self, canvas, rect):
        self.frame(canvas, rect)
        widths = self._widths(rect.w)
        reserve = []
        cursor = rect.x
        for column, width in zip(self.columns, widths):
            band = self.label_band(Rect(cursor, rect.y, width, rect.h), column.get("label"))
            if band:
                reserve.append(band)
            cursor += width
        self.draw_dots(canvas, rect, reserve=reserve, label=False)

        cursor = rect.x
        for index, (column, width) in enumerate(zip(self.columns, widths)):
            if index:
                canvas.line(cursor, rect.y, cursor, rect.bottom,
                            stroke=self.stroke, stroke_width=self.stroke_width)
            self.draw_label(canvas, Rect(cursor, rect.y, width, rect.h), column.get("label"))
            cursor += width


@register("heading")
class Heading(Module):
    """A section title, optionally preceded by an icon.

    The icon sits in a fixed-width box at the left edge so headings with and
    without icons keep the same text origin, and text is centred on the
    heading's cap height.
    """

    params = {
        "text": "the heading itself",
        "icon": "icon name from icons/ (e.g. sunrise)",
        "height": "slot height in mm (default 7.5)",
        "rule": "true to draw a hairline under the heading",
        "size": "font size override",
        "align": "left (default) | center | right",
    }

    def natural_height(self, width):
        return 7.5

    def draw(self, canvas, rect):
        icon_name = self.opt("icon")
        icon_box = self.theme.mm("heading.icon_box")
        icon_gap = self.theme.mm("heading.icon_gap")
        text_x = rect.x
        if icon_name:
            icon = self.ctx.icons.get(icon_name)
            icon.place(
                canvas,
                Rect(rect.x, rect.y, icon_box, rect.h),
                colour=self.opt("colour", self.theme.get("heading.colour")),
                height=self.length("icon_height") or self.theme.mm("heading.icon_height"),
                align="center",
                valign="middle",
            )
            text_x = rect.x + icon_box + icon_gap

        size = self.length("size") or self.theme.mm("heading.size")
        cap = size * self.cap_ratio("heading")
        baseline = rect.cy + cap / 2.0
        align = self.opt("align", "left")
        anchor = {"left": None, "center": "middle", "right": "end"}.get(align)
        if align == "center":
            text_x = rect.cx
        elif align == "right":
            text_x = rect.right

        self.text(canvas, text_x, baseline, self.opt("text", ""), style="heading",
                  size=size, text_anchor=anchor)

        if self.spec.get("rule"):
            canvas.line(rect.x, rect.bottom, rect.right, rect.bottom,
                        stroke=self.stroke, stroke_width=self.stroke_width)


@register("rating")
class Rating(_Framed):
    """A labelled row with a run of icons at the right edge (a mood scale)."""

    params = {
        "label": "left-hand label",
        "icons": "list of icon names, or use 'icon' + 'count'",
        "icon": "icon name prefix; combined with 'count' gives name-1..name-N",
        "count": "how many icons when using 'icon'",
        "icon_size": "icon height in mm (default theme.rating.icon_size)",
        "icon_gap": "gap between icons",
        "height": "row height (default 5)",
    }

    def natural_height(self, width):
        return 5.0

    def _icon_names(self):
        icons = self.opt("icons")
        if icons:
            return list(icons)
        prefix = self.opt("icon")
        if not prefix:
            return []
        return ["%s-%d" % (prefix, i + 1) for i in range(int(self.opt("count", 5)))]

    def draw(self, canvas, rect):
        self.frame(canvas, rect)
        self.draw_dots(canvas, rect)
        self.draw_label(canvas, rect)

        names = self._icon_names()
        if not names:
            return
        size = self.length("icon_size") or self.theme.mm("rating.icon_size")
        gap = self.length("icon_gap") or self.theme.mm("rating.icon_gap")
        pad = self.length("pad_right") or self.theme.mm("rating.pad_right")
        colour = self.opt("colour", self.theme.get("label.colour"))

        # Right-aligned run; each icon is centred in a size-wide cell so mixed
        # aspect ratios stay evenly spaced.
        run = len(names) * size + (len(names) - 1) * gap
        x = rect.right - pad - run
        for name in names:
            icon = self.ctx.icons.get(name)
            icon.place(canvas, Rect(x, rect.y, size, rect.h), colour=colour,
                       height=size, align="center", valign="middle")
            x += size + gap


@register("checklist")
class Checklist(_Framed):
    """Rows of marker + writing box."""

    params = {
        "rows": "number of rows (default 5)",
        "row_height": "height of each row (default 5)",
        "row_gap": "gap between rows (default 2.5)",
        "marker": "circle | circle-slash | square | none | icon:<name>",
        "marker_size": "marker box size in mm (default 5)",
        "marker_gap": "gap between marker and writing box",
        "labels": "optional list of labels, one per row",
        "border": "border of the writing boxes",
        "dots": "dot grid inside the writing boxes",
    }

    def _metrics(self):
        rows = int(self.opt("rows", 5))
        row_height = self.length("row_height") or 5.0
        row_gap = self.length("row_gap")
        if row_gap is None:
            row_gap = self.ctx.grid
        return rows, row_height, row_gap

    def natural_height(self, width):
        rows, row_height, row_gap = self._metrics()
        return rows * row_height + max(rows - 1, 0) * row_gap

    def draw(self, canvas, rect):
        rows, row_height, row_gap = self._metrics()
        marker = self.opt("marker", self.theme.get("marker.shape"))
        has_marker = bool(marker) and marker != "none"
        marker_size = self.length("marker_size") or self.theme.mm("marker.size")
        marker_gap = self.length("marker_gap") or self.theme.mm("checklist.marker_gap")
        if not has_marker:
            marker_size = marker_gap = 0.0
        labels = self.opt("labels") or []

        y = rect.y
        for index in range(rows):
            row = Rect(rect.x, y, rect.w, row_height)
            if has_marker:
                self.draw_marker(canvas, Rect(row.x, row.y, marker_size, row.h), marker)
            box = Rect(row.x + marker_size + marker_gap, row.y,
                       row.w - marker_size - marker_gap, row.h)
            self.frame(canvas, box)
            row_label = labels[index] if index < len(labels) else None
            self.draw_dots(canvas, box, label=row_label)
            if row_label:
                self.draw_label(canvas, box, row_label)
            y += row_height + row_gap


@register("lines")
class Lines(_Framed):
    """A writing area ruled with horizontal lines."""

    params = {
        "spacing": "line spacing in mm (default theme.lines.spacing)",
        "border": "frame around the area (default false)",
        "label": "top-left label",
        "inset": "horizontal inset of the rules from the module edges",
        "first": "offset of the first rule from the top (default = spacing)",
    }

    def __init__(self, spec, ctx):
        spec.setdefault("border", False)
        super().__init__(spec, ctx)

    def draw(self, canvas, rect):
        self.frame(canvas, rect)
        spacing = self.length("spacing") or self.theme.mm("lines.spacing")
        inset = self.length("inset") or 0.0
        first = self.length("first")
        colour = self.opt("colour", self.theme.get("lines.colour"))
        opacity = self.opt("opacity", self.theme.get("lines.opacity"))
        y = rect.y + (spacing if first is None else first)
        while y < rect.bottom - 1e-6:
            canvas.line(rect.x + inset, y, rect.right - inset, y,
                        stroke=colour, stroke_width=self.stroke_width, stroke_opacity=opacity)
            y += spacing
        self.draw_label(canvas, rect)


@register("rule")
class Rule(Module):
    """A single hairline across the module's rect."""

    params = {
        "orientation": "horizontal (default) | vertical",
        "position": "start | center (default) | end, within the rect",
        "inset": "shortens the line at both ends",
        "dash": "SVG dash pattern, e.g. '1 1'",
    }

    def natural_height(self, width):
        return self.ctx.grid

    def draw(self, canvas, rect):
        inset = self.length("inset") or 0.0
        position = self.opt("position", "center")
        dash = self.opt("dash")
        attrs = dict(stroke=self.stroke, stroke_width=self.stroke_width, stroke_dasharray=dash)
        if self.opt("orientation", "horizontal") == "vertical":
            x = {"start": rect.x, "end": rect.right}.get(position, rect.cx)
            canvas.line(x, rect.y + inset, x, rect.bottom - inset, **attrs)
        else:
            y = {"start": rect.y, "end": rect.bottom}.get(position, rect.cy)
            canvas.line(rect.x + inset, y, rect.right - inset, y, **attrs)


@register("text")
class Text(Module):
    """A line of free text."""

    params = {
        "text": "the string to draw",
        "style": "label (default) | heading — which theme block to use",
        "align": "left | center | right",
        "size": "font size override",
        "weight": "font weight override",
    }

    def natural_height(self, width):
        return self.ctx.grid

    def draw(self, canvas, rect):
        style = self.opt("style", "label")
        size = self.length("size") or self.theme.mm("%s.size" % style)
        cap = size * self.cap_ratio(style)
        align = self.opt("align", "left")
        x = {"center": rect.cx, "right": rect.right}.get(align, rect.x)
        anchor = {"center": "middle", "right": "end"}.get(align)
        self.text(canvas, x, rect.cy + cap / 2.0, self.opt("text", ""), style=style,
                  size=size, weight=self.opt("weight"), text_anchor=anchor)


@register("spacer")
class Spacer(Module):
    """Empty space.  ``height: fill`` pushes everything after it down."""

    params = {"height": "mm, or 'fill'"}

    def natural_height(self, width):
        return self.ctx.grid

    def draw(self, canvas, rect):
        if self.ctx.debug:
            canvas.rect(rect.x, rect.y, rect.w, rect.h, fill="none",
                        stroke="#d0d0ff", stroke_width=0.1, stroke_dasharray="0.5 0.5")
