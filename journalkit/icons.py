"""Icon loading.

An icon is a plain SVG file in ``icons/`` whose ``viewBox`` is a tight bounding
box of its artwork.  Paths that should follow the theme colour use
``fill="currentColor"``; anything else (a white knockout, say) is left alone.

Placing an icon emits a ``<g transform="translate(...) scale(...)">`` wrapper,
so no path data is ever rewritten and the source file stays editable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .geometry import Rect
from .units import fmt

_VIEWBOX = re.compile(r'viewBox\s*=\s*"([^"]+)"')
_SVG_OPEN = re.compile(r"<svg\b[^>]*>", re.S)
_SVG_CLOSE = re.compile(r"</svg\s*>\s*$", re.S)
_XML_DECL = re.compile(r"<\?xml[^>]*\?>", re.S)
_COMMENT = re.compile(r"<!--.*?-->", re.S)


@dataclass
class Icon:
    name: str
    vx: float
    vy: float
    vw: float
    vh: float
    body: str

    @property
    def aspect(self) -> float:
        return self.vw / self.vh if self.vh else 1.0

    def place(self, canvas, box: Rect, colour: str, height: float | None = None,
              align: str = "center", valign: str = "middle") -> Rect:
        """Draw the icon inside ``box``, preserving aspect ratio.

        ``height`` fixes the drawn height (the common case for a run of icons
        that must look optically equal); otherwise the icon is fitted to the
        box.  Returns the rect actually occupied.
        """
        if height is None:
            scale = min(box.w / self.vw, box.h / self.vh)
        else:
            scale = height / self.vh
            if self.vw * scale > box.w:
                scale = box.w / self.vw
        w, h = self.vw * scale, self.vh * scale

        if align == "left":
            x = box.x
        elif align == "right":
            x = box.right - w
        else:
            x = box.cx - w / 2.0
        if valign == "top":
            y = box.y
        elif valign == "bottom":
            y = box.bottom - h
        else:
            y = box.cy - h / 2.0

        canvas.raw(
            '<g transform="translate(%s,%s) scale(%s) translate(%s,%s)" fill="%s" color="%s">'
            % (fmt(x), fmt(y), fmt(scale), fmt(-self.vx), fmt(-self.vy), colour, colour)
        )
        canvas.raw("  " + self.body.strip().replace("\n", "\n  "))
        canvas.raw("</g>")
        return Rect(x, y, w, h)


class IconSet:
    def __init__(self, roots: list[Path]):
        self.roots = [Path(r) for r in roots]
        self._cache: dict[str, Icon] = {}

    def _find(self, name: str) -> Path:
        stem = name[:-4] if name.endswith(".svg") else name
        for root in self.roots:
            candidate = root / (stem + ".svg")
            if candidate.is_file():
                return candidate
        searched = ", ".join(str(r) for r in self.roots) or "(no icon directories)"
        raise FileNotFoundError("icon %r not found in %s" % (name, searched))

    def get(self, name: str) -> Icon:
        if name in self._cache:
            return self._cache[name]
        path = self._find(name)
        text = path.read_text()

        match = _VIEWBOX.search(text)
        if not match:
            raise ValueError("%s: icon needs a viewBox (run tools/extract_icons.py)" % path)
        vx, vy, vw, vh = (float(v) for v in match.group(1).replace(",", " ").split())

        body = _XML_DECL.sub("", text)
        body = _COMMENT.sub("", body)
        body = _SVG_OPEN.sub("", body, count=1)
        body = _SVG_CLOSE.sub("", body).strip()

        icon = Icon(name, vx, vy, vw, vh, body)
        self._cache[name] = icon
        return icon

    def names(self) -> list[str]:
        found: set[str] = set()
        for root in self.roots:
            if root.is_dir():
                found.update(p.stem for p in root.glob("*.svg"))
        return sorted(found)
