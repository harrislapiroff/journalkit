"""Lengths and the modular grid.

Every internal length is a float in **millimetres**.  YAML may write bare
numbers (mm implied) or unit-suffixed strings: ``"0.25pt"``, ``"1in"``,
``"3.5mm"``, ``"12px"``.
"""

from __future__ import annotations

import math
import re

MM_PER_PT = 25.4 / 72.0
MM_PER_IN = 25.4
MM_PER_PX = 25.4 / 96.0

_UNITS = {"mm": 1.0, "cm": 10.0, "pt": MM_PER_PT, "in": MM_PER_IN, "px": MM_PER_PX}
_LENGTH = re.compile(r"^\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s*([a-z]*)\s*$")

#: Sentinel for a dimension that absorbs leftover space in its container.
FILL = "fill"

EPS = 1e-6


def mm(value, default=None) -> float:
    """Coerce a YAML length to millimetres."""
    if value is None:
        if default is None:
            raise ValueError("missing length")
        return mm(default)
    if isinstance(value, bool):
        raise ValueError("expected a length, got a boolean")
    if isinstance(value, (int, float)):
        return float(value)
    match = _LENGTH.match(str(value))
    if not match:
        raise ValueError("cannot parse length %r" % (value,))
    number, unit = float(match.group(1)), match.group(2) or "mm"
    if unit not in _UNITS:
        raise ValueError("unknown unit %r in %r (use %s)" % (unit, value, "/".join(_UNITS)))
    return number * _UNITS[unit]


def is_fill(value) -> bool:
    return isinstance(value, str) and value.strip().lower() == FILL


def snap(value: float, grid: float, mode: str = "nearest") -> float:
    """Snap ``value`` to the nearest/floor/ceil multiple of ``grid``."""
    if grid <= 0:
        return value
    q = value / grid
    if mode == "floor":
        q = math.floor(q + EPS)
    elif mode == "ceil":
        q = math.ceil(q - EPS)
    else:
        q = math.floor(q + 0.5 + EPS)
    return q * grid


def on_grid(value: float, grid: float) -> bool:
    if grid <= 0:
        return True
    return abs(value - snap(value, grid)) < 1e-6


def fmt(value: float) -> str:
    """Format a length for SVG output: short, no exponent, no trailing zeros."""
    if abs(value) < 1e-9:
        return "0"
    text = "%.4f" % value
    text = text.rstrip("0").rstrip(".")
    return text or "0"
