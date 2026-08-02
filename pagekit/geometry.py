"""Rectangles, in page millimetres with y increasing downwards."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.h / 2.0

    def inset(self, top=0.0, right=None, bottom=None, left=None) -> "Rect":
        """CSS-ish shorthand: inset(a), inset(v, h), inset(t, r, b, l)."""
        if right is None:
            right = bottom = left = top
        elif bottom is None:
            bottom, left = top, right
        elif left is None:
            left = right
        return Rect(self.x + left, self.y + top, self.w - left - right, self.h - top - bottom)

    def moved(self, dx=0.0, dy=0.0) -> "Rect":
        return Rect(self.x + dx, self.y + dy, self.w, self.h)

    def resized(self, w=None, h=None) -> "Rect":
        return Rect(self.x, self.y, self.w if w is None else w, self.h if h is None else h)

    def contains_point(self, x: float, y: float, strict: bool = True) -> bool:
        if strict:
            return self.x < x < self.right and self.y < y < self.bottom
        return self.x <= x <= self.right and self.y <= y <= self.bottom

    def __str__(self) -> str:  # debugging aid
        return "Rect(%.2f, %.2f, %.2f x %.2f)" % (self.x, self.y, self.w, self.h)
