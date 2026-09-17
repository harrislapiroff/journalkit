"""Theme: the shared look every module draws with.

A theme is a nested dict, deep-merged over :data:`DEFAULT_THEME`.  Modules read
it through :class:`Theme`, which resolves dotted keys and understands the
``$theme.path`` indirection so a module spec can say ``stroke: $theme.rule``.
"""

from __future__ import annotations

import copy

from .units import mm

DEFAULT_THEME = {
    # The one colour everything else points at.  Override `ink` to recolour a
    # whole document; override any individual role below to pin just that one.
    # #231F20 is a rich black that prints a little softer than "#000".
    "ink": "#231F20",
    "stroke": "$theme.ink",
    "stroke_width": "0.25pt",
    "fill": "none",
    "font": {
        # Montserrat Regular/Medium/Bold ship with JournalKit; any other
        # family must be installed on the machine doing the build.
        "family": "Montserrat",
        # Draw text as glyph outlines read from the font file, so the output
        # depends on no installed font.  False emits SVG <text> instead.
        "outline": True,
        # Fraction of the em occupied by capitals, used to place baselines
        # from a box edge or centre.  Left null, it is read from the font's
        # OS/2 table (Montserrat publishes 0.700); set it to override.
        "cap_height": None,
        # Fallback mean advance per character, used to estimate label widths
        # only when the font file cannot be read.  Real Montserrat capitals
        # range from 0.5em to over 0.9em, so this is a safety net, not a
        # substitute for journalkit.fontmetrics.
        "avg_advance": 0.75,
    },
    "label": {
        "size": "8pt",
        "weight": 500,
        "tracking": 0,
        "colour": "$theme.ink",
        # Baseline offset from the module's top-left corner.  dx is the text
        # anchor, so the visible ink starts ~0.3mm further right.
        "dx": 1.8,
        "dy": 3.55,
    },
    "heading": {
        "size": "12pt",
        "weight": 700,
        "tracking": 0,
        "colour": "$theme.ink",
        "icon_box": 6.0,
        "icon_height": 4.6,
        "icon_gap": 1.0,
    },
    "dots": {
        "radius": 0.125,
        "colour": "$theme.ink",
        "opacity": 1.0,
        # Keep dots clear of a module's label: "band" clears the label's full
        # line, "text" clears only the estimated width of the text, "none"
        # lets dots run underneath it.
        "reserve_label": "band",
        "label_pad": 0.75,
    },
    # The checkbox, shared by every module that draws one (checklist,
    # habit_grid), so a habit is ticked the same way as a task.
    "marker": {
        "shape": "circle-slash",   # circle-slash | circle | square | none | icon:<name>
        "size": 5.0,
        # A knockout, so it masks whatever is under it: not themed on purpose.
        "fill": "#ffffff",
    },
    "checklist": {
        "marker_gap": 2.5,
    },
    "rating": {
        "icon_size": 3.0,
        "icon_gap": 2.0,
        "pad_right": 1.5,
    },
    "lines": {
        "spacing": 5.0,
        "colour": "$theme.ink",
        "opacity": 0.45,
    },
}


def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge ``override`` into a copy of ``base``."""
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


_MISSING = object()


class Theme:
    def __init__(self, data: dict | None = None):
        self.data = deep_merge(DEFAULT_THEME, data or {})

    def _lookup(self, path: str, default=_MISSING):
        node = self.data
        for part in path.split("."):
            if not isinstance(node, dict) or part not in node:
                if default is _MISSING:
                    raise KeyError("theme has no key %r" % path)
                return default
            node = node[part]
        return node

    def get(self, path: str, default=_MISSING):
        """A theme value, following any ``$theme.other.key`` indirection.

        Indirection is what lets one value stand behind many: every colour in
        the defaults points at ``ink``, so setting ``ink`` recolours the whole
        page while any individual role can still be pinned to its own value.
        """
        value = self._lookup(path, default)
        seen = set()
        while isinstance(value, str) and value.startswith("$theme."):
            ref = value[len("$theme."):]
            if ref in seen:
                raise ValueError("circular theme reference: %s -> %s" % (path, ref))
            seen.add(ref)
            value = self._lookup(ref, default)
        return value

    def mm(self, path: str, default=_MISSING) -> float:
        return mm(self.get(path, default))

    def resolve(self, value, default=_MISSING):
        """Expand a ``$theme.some.key`` reference; pass anything else through."""
        if isinstance(value, str) and value.startswith("$theme."):
            return self.get(value[len("$theme.") :], default)
        if value is None and default is not _MISSING:
            return default
        return value

    def derive(self, override: dict | None) -> "Theme":
        """A child theme, for per-page or per-module overrides."""
        if not override:
            return self
        child = Theme.__new__(Theme)
        child.data = deep_merge(self.data, override)
        return child
