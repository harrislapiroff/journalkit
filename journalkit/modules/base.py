"""Module base class and registry.

Adding a module type is one class and one decorator::

    from ..geometry import Rect
    from .base import Module, register

    @register("stamp")
    class Stamp(Module):
        \"\"\"A dashed box to stick a photo in.\"\"\"
        params = {"label": "text drawn above the box"}

        def natural_height(self, width):
            return 40.0

        def draw(self, canvas, rect):
            canvas.rect(rect.x, rect.y, rect.w, rect.h,
                        fill="none", stroke=self.stroke,
                        stroke_width=self.stroke_width, stroke_dasharray="1 1")

Import the file from ``journalkit/modules/__init__.py`` and it is usable as
``type: stamp`` in YAML.

Everything a module needs beyond its own spec comes from ``self.ctx``
(:class:`journalkit.render.RenderContext`): the theme, the icon set, the page
geometry and the page-wide dot lattice.
"""

from __future__ import annotations

from .. import fontmetrics
from ..geometry import Rect
from ..units import is_fill, mm

REGISTRY: dict[str, type] = {}


def is_builtin(cls) -> bool:
    """Was this class defined inside the journalkit package itself?"""
    return (cls.__module__ or "").startswith("journalkit.")


def register(name: str):
    """Class decorator: make ``type: <name>`` available in YAML.

    A built-in name can never be taken over — a project module that tries to
    redefine ``box`` is a mistake worth stopping. Two *project* files
    registering the same name is different: it happens whenever two projects
    are built in one process, so the later one simply replaces the earlier.
    """
    def decorate(cls):
        cls.name = name
        existing = REGISTRY.get(name)
        if existing is not None and existing is not cls:
            if is_builtin(existing):
                raise ValueError("module type %r is built in and cannot be redefined" % name)
            if is_builtin(cls):
                raise ValueError("module type %r registered twice" % name)
        REGISTRY[name] = cls
        return cls

    return decorate


def build(spec, ctx) -> "Module":
    """Instantiate a module from its YAML mapping."""
    if isinstance(spec, str):  # bare "spacer" style shorthand
        spec = {"type": spec}
    if not isinstance(spec, dict):
        raise ValueError("module must be a mapping, got %r" % (spec,))
    kind = spec.get("type")
    if not kind:
        raise ValueError("module is missing 'type': %r" % (spec,))
    if kind not in REGISTRY:
        raise ValueError("unknown module type %r (known: %s)" % (kind, ", ".join(sorted(REGISTRY))))
    return REGISTRY[kind](spec, ctx)


class Module:
    """Base class for everything that can appear in a page's ``content``."""

    name = "module"
    #: ``{param: description}`` — documentation only, surfaced by --list-modules.
    params: dict[str, str] = {}

    def __init__(self, spec: dict, ctx):
        self.spec = spec
        self.ctx = ctx
        self.theme = ctx.theme.derive(spec.get("theme"))
        self.id = spec.get("id")

    # -- convenience accessors --------------------------------------------
    def opt(self, key, default=None):
        """A spec value, with ``$theme.x`` references expanded."""
        return self.theme.resolve(self.spec.get(key, default), default)

    def length(self, key, default=None):
        value = self.spec.get(key, default)
        if value is None:
            return None
        return mm(self.theme.resolve(value))

    @property
    def stroke(self) -> str:
        return self.opt("stroke", self.theme.get("stroke"))

    @property
    def stroke_width(self) -> float:
        return mm(self.opt("stroke_width", self.theme.get("stroke_width")))

    # -- sizing ------------------------------------------------------------
    def natural_height(self, width: float):
        """Intrinsic height in mm, or ``None`` if the module has no opinion."""
        return None

    def natural_width(self, height: float):
        return None

    def requested_height(self, width: float):
        """Resolved ``height``: a float, or the string ``"fill"``."""
        value = self.spec.get("height")
        if is_fill(value):
            return "fill"
        if value is not None:
            return mm(self.theme.resolve(value))
        natural = self.natural_height(width)
        return "fill" if natural is None else natural

    def requested_width(self, height: float):
        value = self.spec.get("width")
        if is_fill(value):
            return "fill"
        if value is not None:
            return mm(self.theme.resolve(value))
        natural = self.natural_width(height)
        return "fill" if natural is None else natural

    def fill_weight(self) -> float:
        """Relative share of leftover space when this module is ``fill``."""
        weight = self.spec.get("flex", 1)
        try:
            return max(float(weight), 0.0) or 1.0
        except (TypeError, ValueError):
            return 1.0

    # -- drawing -----------------------------------------------------------
    def draw(self, canvas, rect):  # pragma: no cover - abstract
        raise NotImplementedError("%s.draw" % type(self).__name__)

    # -- shared helpers ----------------------------------------------------
    def text(self, canvas, x, y, content, style="label", **overrides):
        """Draw themed text with its baseline at ``(x, y)``."""
        size = mm(overrides.pop("size", None) or self.theme.get("%s.size" % style))
        weight = overrides.pop("weight", None) or self.theme.get("%s.weight" % style)
        colour = overrides.pop("colour", None) or self.theme.get("%s.colour" % style)
        tracking = mm(overrides.pop("tracking", None) or self.theme.get("%s.tracking" % style, 0))
        family = overrides.pop("family", None) or self.theme.get("font.family")
        attrs = dict(
            font_family=family,
            font_size=size,
            font_weight=weight,
            fill=colour,
            **overrides,
        )
        if tracking:
            attrs["letter_spacing"] = tracking
        canvas.text(x, y, content, **attrs)

    def font_metrics(self, style="label"):
        """Parsed metrics for the font this style renders in, or ``None``."""
        return fontmetrics.load(self.theme.get("font.family"),
                                self.theme.get("%s.weight" % style, 400))

    def cap_ratio(self, style="label") -> float:
        """Cap height as a fraction of the em.

        An explicit ``theme.font.cap_height`` wins; otherwise it comes from the
        font's own ``OS/2`` table, and only failing that from a sane default.
        """
        configured = self.theme.get("font.cap_height", None)
        if configured is not None:
            return float(configured)
        metrics = self.font_metrics(style)
        if metrics and metrics.cap_ratio:
            return metrics.cap_ratio
        return fontmetrics.FALLBACK_CAP_RATIO

    def cap_height(self, style="label") -> float:
        return mm(self.theme.get("%s.size" % style)) * self.cap_ratio(style)

    def text_width(self, text: str, size: float, style="label") -> float:
        """Width of ``text`` at ``size``, measured from the font where possible.

        Falls back to a character-count estimate when the font file cannot be
        read.  The estimate is coarse — real advances for capitals range from
        0.5em to over 0.9em — so it is only ever a safety net.
        """
        if not text:
            return 0.0
        tracking = mm(self.theme.get("%s.tracking" % style, 0) or 0)
        metrics = self.font_metrics(style)
        if metrics:
            return metrics.text_width(text, size, tracking)
        advance = float(self.theme.get("font.avg_advance", 0.75))
        return len(text) * size * advance + tracking * len(text)

    def draw_label(self, canvas, rect, text=None):
        """Top-left label, positioned by ``theme.label.dx`` / ``dy``."""
        text = self.opt("label") if text is None else text
        if not text:
            return
        self.text(
            canvas,
            rect.x + self.theme.mm("label.dx"),
            rect.y + self.theme.mm("label.dy"),
            text,
            style="label",
        )

    def draw_marker(self, canvas, box, marker=None):
        """Draw a checkbox marker centred in ``box``, at ``theme.marker.shape``.

        The shape is one of ``circle-slash``, ``circle``, ``square``, ``none``
        or ``icon:<name>``; its diameter is whichever of ``box``'s sides is
        shorter, so the caller sizes it by handing over the right rect.  The
        fill is a knockout rather than the page colour, so a marker sitting on
        a rule or the dot lattice masks it.
        """
        if marker is None:
            marker = self.opt("marker", self.theme.get("marker.shape"))
        if not marker or marker == "none":
            return
        colour = self.stroke
        width = self.stroke_width
        if isinstance(marker, str) and marker.startswith("icon:"):
            icon = self.ctx.icons.get(marker[5:])
            icon.place(canvas, box, colour=colour, align="center", valign="middle")
            return
        knockout = self.opt("marker_fill", self.theme.get("marker.fill"))
        size = min(box.w, box.h)
        cx, cy = box.cx, box.cy
        if marker == "square":
            canvas.rect(cx - size / 2, cy - size / 2, size, size,
                        fill=knockout, stroke=colour, stroke_width=width)
            return
        canvas.circle(cx, cy, size / 2, fill=knockout, stroke=colour, stroke_width=width)
        if marker == "circle-slash":
            # The slash is a full diameter at 45 degrees, low-left to top-right.
            offset = size / 2 / (2 ** 0.5)
            canvas.line(cx - offset, cy + offset, cx + offset, cy - offset,
                        stroke=colour, stroke_width=width)

    def label_band(self, rect, text=None):
        """The area a top-left label occupies, for dots to keep clear of.

        Returns ``None`` when there is no label or clearance is switched off.
        Two modes, set by ``theme.dots.reserve_label``:

        ``band`` (default)
            The full width of the module, for the height of the label's line.
            The label then sits in a clean strip with the grid starting below
            it — which reads as deliberate, and needs no font metrics.
        ``text``
            Only as wide as the label is estimated to be, so dots continue to
            the right of a short label.  The width is approximated from the
            character count (see ``theme.font.avg_advance``), so it is padded
            generously rather than measured.
        """
        text = self.opt("label") if text is None else text
        if not text:
            return None
        mode = self.theme.get("dots.reserve_label", "band")
        if mode in (None, False, "none"):
            return None

        size = mm(self.theme.get("label.size"))
        cap = self.cap_height("label")
        pad = self.theme.mm("dots.label_pad", 0.75)
        baseline = rect.y + self.theme.mm("label.dy")
        top = baseline - cap - pad
        # Allow for descenders, since a label is not necessarily all caps.
        bottom = baseline + max(pad, 0.2 * size)

        if mode == "text":
            width = self.text_width(str(text), size, style="label") + 2 * pad
            left = rect.x + self.theme.mm("label.dx") - pad
            return Rect(left, top, min(width, rect.right - left), bottom - top)
        return Rect(rect.x, top, rect.w, bottom - top)

    def draw_dots(self, canvas, rect, reserve=(), label=None):
        """Fill ``rect`` with the page-wide dot lattice, if ``dots`` is on.

        Dots are omitted where they would run into the module's label, rather
        than the label being drawn over them — on a printed page a dot behind
        a title reads as a smudge.
        """
        if not self.spec.get("dots"):
            return
        exclude = list(reserve)
        band = self.label_band(rect, label)
        if band:
            exclude.append(band)
        self.ctx.draw_dots(canvas, rect, options=self.spec.get("dots"), exclude=exclude)
