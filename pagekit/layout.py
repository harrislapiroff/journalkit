"""Stack and row layout on the module grid.

Two rules keep a page tidy:

* every module rect is snapped to the module grid (2.5 mm by default), so
  modules always line up with each other and with the dot lattice;
* exactly the leftover space is handed to children whose size is ``fill``,
  divided by weight and rounded *down* to the grid, with the remainder going
  to the last filling child so the stack still ends on a grid line.
"""

from __future__ import annotations

from dataclasses import dataclass

from .geometry import Rect
from .units import mm, snap


@dataclass
class Placement:
    module: object
    rect: Rect


def _gap_before(child, index: int, default: float, theme) -> float:
    explicit = child.spec.get("gap")
    if explicit is not None:
        return mm(theme.resolve(explicit))
    return 0.0 if index == 0 else default


def _distribute(sizes, weights, leftover, grid):
    """Split ``leftover`` between the ``fill`` entries of ``sizes``."""
    fill_indices = [i for i, s in enumerate(sizes) if s == "fill"]
    if not fill_indices:
        return sizes, leftover
    if leftover < 0:
        leftover = 0.0
    total_weight = sum(weights[i] for i in fill_indices) or 1.0
    out = list(sizes)
    used = 0.0
    for i in fill_indices[:-1]:
        share = snap(leftover * weights[i] / total_weight, grid, "floor")
        out[i] = max(share, 0.0)
        used += out[i]
    last = fill_indices[-1]
    out[last] = max(leftover - used, 0.0)
    return out, 0.0


def _resolve(children, extent, gap_default, grid, axis, cross, ctx):
    """Shared 1-D solver.  ``axis`` is 'h' for a stack, 'w' for a row."""
    theme = ctx.theme
    gaps = [_gap_before(c, i, gap_default, theme) for i, c in enumerate(children)]
    if axis == "h":
        requested = [c.requested_height(cross) for c in children]
    else:
        requested = [c.requested_width(cross) for c in children]

    fixed = [0.0 if r == "fill" else snap(r, grid) for r in requested]
    for child, want, got in zip(children, requested, fixed):
        if want != "fill" and abs(want - got) > 1e-6:
            ctx.warn(
                "%s: %s %.3fmm is off the %.3fmm grid, snapped to %.3fmm"
                % (child.name, "height" if axis == "h" else "width", want, grid, got)
            )

    leftover = extent - sum(fixed) - sum(gaps)
    sizes = [r if r == "fill" else f for r, f in zip(requested, fixed)]
    weights = [c.fill_weight() for c in children]
    sizes, _ = _distribute(sizes, weights, leftover, grid)

    total = sum(sizes) + sum(gaps)
    if total - extent > 1e-6:
        ctx.warn(
            "content overflows its container by %.2fmm (%s available, %s needed)"
            % (total - extent, round(extent, 2), round(total, 2))
        )
    return sizes, gaps


def layout_stack(children, rect: Rect, gap_default: float, grid: float, ctx) -> list[Placement]:
    sizes, gaps = _resolve(children, rect.h, gap_default, grid, "h", rect.w, ctx)
    out, cursor = [], rect.y
    for child, size, gap in zip(children, sizes, gaps):
        cursor += gap
        out.append(Placement(child, Rect(rect.x, cursor, rect.w, size)))
        cursor += size
    return out


def layout_row(children, rect: Rect, gap_default: float, grid: float, ctx) -> list[Placement]:
    sizes, gaps = _resolve(children, rect.w, gap_default, grid, "w", rect.h, ctx)
    out, cursor = [], rect.x
    for child, size, gap in zip(children, sizes, gaps):
        cursor += gap
        height = child.requested_height(size)
        if height == "fill" or height > rect.h:
            height = rect.h
        else:
            height = snap(height, grid)
        align = child.spec.get("valign", "top")
        if align in ("middle", "center"):
            y = rect.y + (rect.h - height) / 2.0
        elif align == "bottom":
            y = rect.bottom - height
        else:
            y = rect.y
        out.append(Placement(child, Rect(cursor, y, size, height)))
        cursor += size
    return out
