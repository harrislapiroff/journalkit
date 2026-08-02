"""A very small SVG writer.

One user unit is one millimetre, so every number a module computes can be
written straight out.  Nothing here knows about notebooks; it is just enough
primitives for the module library to draw with.
"""

from __future__ import annotations

from xml.sax.saxutils import escape, quoteattr

from .units import fmt


def _attrs(pairs: dict) -> str:
    out = []
    for key, value in pairs.items():
        if value is None:
            continue
        key = key.replace("_", "-")
        if isinstance(value, float):
            value = fmt(value)
        out.append("%s=%s" % (key, quoteattr(str(value))))
    return " ".join(out)


class Canvas:
    """Collects SVG elements for one page."""

    def __init__(self, width: float, height: float, background: str | None = "#ffffff"):
        self.width = width
        self.height = height
        self.background = background
        self._parts: list[str] = []
        self._defs: list[str] = []
        self._depth = 1

    # -- structure ---------------------------------------------------------
    def _emit(self, text: str) -> None:
        self._parts.append("  " * self._depth + text)

    def defs(self, text: str) -> None:
        self._defs.append("    " + text)

    def open_group(self, **attrs) -> None:
        self._emit("<g %s>" % _attrs(attrs) if attrs else "<g>")
        self._depth += 1

    def close_group(self) -> None:
        self._depth -= 1
        self._emit("</g>")

    def comment(self, text: str) -> None:
        self._emit("<!-- %s -->" % text.replace("--", "- -"))

    def raw(self, text: str) -> None:
        self._emit(text)

    # -- primitives --------------------------------------------------------
    def rect(self, x, y, w, h, **attrs) -> None:
        self._emit("<rect %s/>" % _attrs(dict(x=x, y=y, width=w, height=h, **attrs)))

    def line(self, x1, y1, x2, y2, **attrs) -> None:
        self._emit("<line %s/>" % _attrs(dict(x1=x1, y1=y1, x2=x2, y2=y2, **attrs)))

    def circle(self, cx, cy, r, **attrs) -> None:
        self._emit("<circle %s/>" % _attrs(dict(cx=cx, cy=cy, r=r, **attrs)))

    def path(self, d, **attrs) -> None:
        self._emit("<path %s/>" % _attrs(dict(d=d, **attrs)))

    def text(self, x, y, content, **attrs) -> None:
        self._emit("<text %s>%s</text>" % (_attrs(dict(x=x, y=y, **attrs)), escape(str(content))))

    # -- output ------------------------------------------------------------
    def to_svg(self, title: str | None = None) -> str:
        head = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<svg xmlns="http://www.w3.org/2000/svg" version="1.1"',
            '     width="%smm" height="%smm" viewBox="0 0 %s %s">'
            % (fmt(self.width), fmt(self.height), fmt(self.width), fmt(self.height)),
        ]
        if title:
            head.append("  <title>%s</title>" % escape(title))
        if self._defs:
            head.append("  <defs>")
            head.extend(self._defs)
            head.append("  </defs>")
        if self.background:
            head.append(
                '  <rect x="0" y="0" width="%s" height="%s" fill="%s"/>'
                % (fmt(self.width), fmt(self.height), self.background)
            )
        return "\n".join(head + self._parts + ["</svg>", ""])
