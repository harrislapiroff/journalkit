"""Containers: modules that lay other modules out."""

from __future__ import annotations

from ..layout import layout_row, layout_stack
from ..units import mm
from .base import Module, build, register


class Container(Module):
    axis = "stack"

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx)
        self.children = [build(child, ctx) for child in spec.get("content", spec.get("children", []))]
        gap = spec.get("gap_between", spec.get("spacing"))
        self.gap = ctx.default_gap if gap is None else mm(self.theme.resolve(gap))
        self.padding = mm(spec.get("padding", 0))

    def _inner(self, rect):
        return rect.inset(self.padding) if self.padding else rect

    def _place(self, rect):
        inner = self._inner(rect)
        if self.axis == "row":
            return layout_row(self.children, inner, self.gap, self.ctx.grid, self.ctx)
        return layout_stack(self.children, inner, self.gap, self.ctx.grid, self.ctx)

    def draw(self, canvas, rect):
        for placement in self._place(rect):
            placement.module.draw(canvas, placement.rect)


@register("stack")
class Stack(Container):
    """Stacks its children vertically.  ``content`` is an implicit stack."""

    axis = "stack"
    params = {
        "content": "list of child modules",
        "gap_between": "vertical gap between children (default: page defaults.gap)",
        "padding": "inset applied to the container before laying children out",
    }

    def natural_height(self, width):
        inner_width = width - 2 * self.padding
        total = 2 * self.padding
        for index, child in enumerate(self.children):
            height = child.requested_height(inner_width)
            if height == "fill":
                return None  # a filling child makes the stack itself elastic
            gap = child.spec.get("gap")
            total += height + (mm(gap) if gap is not None else (0.0 if index == 0 else self.gap))
        return total


@register("row")
class Row(Container):
    """Lays its children out side by side.

    Children size on ``width`` (mm or ``fill``); ``valign`` positions a child
    shorter than the row.
    """

    axis = "row"
    params = {
        "content": "list of child modules",
        "gap_between": "horizontal gap between children (default: page defaults.gap)",
        "padding": "inset applied to the container before laying children out",
        "height": "row height; children may be shorter and are aligned by 'valign'",
    }

    def natural_height(self, width):
        heights = []
        for child in self.children:
            height = child.requested_height(width)
            if height != "fill":
                heights.append(height)
        return max(heights) if heights else None
