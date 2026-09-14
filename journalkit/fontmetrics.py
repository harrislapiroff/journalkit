"""Font files, read directly: advance widths, cap height and glyph outlines.

journalkit draws text as **outlines** — every glyph becomes an SVG ``<path>``
— so the finished page depends on no installed font, and Inkscape has nothing
to substitute.  That needs the glyph data, so this is a small sfnt reader over
the tables that matter: ``head``, ``hhea``, ``hmtx``, ``cmap`` and ``OS/2``
for metrics, ``loca`` and ``glyf`` for TrueType outlines.  CFF-flavoured
OpenType carries its outlines elsewhere; for those the metrics are read and
text falls back to an SVG ``<text>`` element.

Montserrat Regular, Medium and Bold ship inside the package (``fonts/``, SIL
Open Font License) and are found before anything installed on the system, so
the default theme works everywhere.  Any other family is looked up in the
usual font directories.

Everything here fails soft: if the font cannot be found or parsed,
:func:`load` returns ``None`` and the caller falls back to an estimate.  A
missing font must never be the reason a page fails to render.

    >>> metrics = load("Montserrat", weight=500)
    >>> metrics.text_width("GRATITUDE", 2.822)   # size in mm -> width in mm
    16.87...

Kerning (``GPOS``) is not applied.  Labels here are short runs of capitals,
where its absence is hard to see, and a plain sum of advances errs wide — the
safe direction when the number is used to reserve space.
"""

from __future__ import annotations

import shutil
import struct
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

#: CSS weight -> the style name font files are usually called after.
WEIGHT_NAMES = {
    100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular",
    500: "Medium", 600: "SemiBold", 700: "Bold", 800: "ExtraBold", 900: "Black",
}

#: Fonts shipped with journalkit, searched before the system.
BUNDLED_FONTS = Path(__file__).resolve().parent / "fonts"

FONT_DIRS = [
    Path.home() / "Library" / "Fonts",
    Path("/Library/Fonts"),
    Path("/System/Library/Fonts"),
    Path.home() / ".local" / "share" / "fonts",
    Path.home() / ".fonts",
    Path("/usr/share/fonts"),
    Path("/usr/local/share/fonts"),
]

#: Used when a font publishes no cap height and none is configured.
FALLBACK_CAP_RATIO = 0.7

_CACHE: dict[tuple, "FontMetrics | None"] = {}


@dataclass
class FontMetrics:
    path: Path
    units_per_em: int
    advances: dict = field(repr=False)      # codepoint -> advance in font units
    default_advance: int = 0
    cap_height_units: int | None = None
    glyph_ids: dict = field(default_factory=dict, repr=False)   # codepoint -> glyph id
    _glyf: "tuple | None" = field(default=None, repr=False)     # (data, loca offsets, glyf offset)
    _paths: dict = field(default_factory=dict, repr=False)       # glyph id -> path (font units)

    def text_width(self, text: str, size: float, tracking: float = 0.0) -> float:
        """Width of ``text`` set at ``size``, in whatever unit ``size`` is."""
        if not text:
            return 0.0
        total = sum(self.advances.get(ord(ch), self.default_advance) for ch in text)
        width = total * size / self.units_per_em
        if tracking:
            width += tracking * len(text)
        return width

    @property
    def cap_ratio(self) -> float | None:
        """Cap height as a fraction of the em, or ``None`` if unpublished."""
        if not self.cap_height_units:
            return None
        return self.cap_height_units / self.units_per_em

    # -- outlines ----------------------------------------------------------
    @property
    def has_outlines(self) -> bool:
        """True for TrueType (``glyf``) fonts; CFF outlines are not read."""
        return self._glyf is not None

    def glyph_path(self, glyph_id: int) -> str:
        """SVG path data for one glyph in font units, y up.  Cached."""
        if glyph_id in self._paths:
            return self._paths[glyph_id]
        path = _glyph_outline(self, glyph_id, 0) if self._glyf else ""
        self._paths[glyph_id] = path
        return path

    def outline(self, text: str, size: float, tracking: float = 0.0,
                anchor: str = "start") -> str:
        """SVG path data for ``text`` at ``size``, baseline at the origin.

        ``size`` and ``tracking`` are in output units (mm); the returned path
        is in those units with y pointing down, ready to ``translate()`` to
        the baseline start.  ``anchor`` is ``start``, ``middle`` or ``end``.
        """
        scale = size / self.units_per_em
        track = tracking / scale if scale else 0.0
        pen = 0.0
        if anchor in ("middle", "end"):
            width = self.text_width(text, size, tracking) / scale
            pen = -width / 2.0 if anchor == "middle" else -width
        parts = []
        for ch in text:
            glyph = self.glyph_ids.get(ord(ch))
            if glyph is not None:
                d = self.glyph_path(glyph)
                if d:
                    parts.append(_shift_path(d, pen, scale))
            pen += self.advances.get(ord(ch), self.default_advance) + track
        return " ".join(parts)


# ---------------------------------------------------------------- sfnt
def _tables(data: bytes) -> dict:
    """Map table tag -> (offset, length), following a TTC header if present."""
    offset = 0
    if data[:4] == b"ttcf":
        offset = struct.unpack_from(">I", data, 12)[0]  # first font in collection
    count = struct.unpack_from(">H", data, offset + 4)[0]
    out = {}
    for i in range(count):
        base = offset + 12 + 16 * i
        tag, _checksum, off, length = struct.unpack_from(">4sIII", data, base)
        out[tag.decode("latin1").strip()] = (off, length)
    return out


def _parse_cmap(data: bytes, offset: int) -> dict:
    """Codepoint -> glyph id, from the best available cmap subtable."""
    count = struct.unpack_from(">H", data, offset + 2)[0]
    best = None
    for i in range(count):
        platform, encoding, sub = struct.unpack_from(">HHI", data, offset + 4 + 8 * i)
        # Prefer a full-repertoire Unicode table, then BMP, then anything.
        rank = {(3, 10): 0, (0, 4): 0, (0, 6): 0,
                (3, 1): 1, (0, 3): 1, (0, 2): 1, (0, 1): 1, (0, 0): 1}.get(
                    (platform, encoding), 2)
        if best is None or rank < best[0]:
            best = (rank, offset + sub)
    if best is None:
        return {}

    table = best[1]
    fmt = struct.unpack_from(">H", data, table)[0]
    mapping: dict[int, int] = {}

    if fmt == 4:
        seg_x2 = struct.unpack_from(">H", data, table + 6)[0]
        segs = seg_x2 // 2
        ends = table + 14
        starts = ends + seg_x2 + 2
        deltas = starts + seg_x2
        ranges = deltas + seg_x2
        for s in range(segs):
            end = struct.unpack_from(">H", data, ends + 2 * s)[0]
            start = struct.unpack_from(">H", data, starts + 2 * s)[0]
            delta = struct.unpack_from(">h", data, deltas + 2 * s)[0]
            range_off = struct.unpack_from(">H", data, ranges + 2 * s)[0]
            if start > end:
                continue
            for cp in range(start, min(end, 0xFFFF) + 1):
                if range_off == 0:
                    glyph = (cp + delta) & 0xFFFF
                else:
                    pos = ranges + 2 * s + range_off + 2 * (cp - start)
                    if pos + 2 > len(data):
                        continue
                    glyph = struct.unpack_from(">H", data, pos)[0]
                    if glyph:
                        glyph = (glyph + delta) & 0xFFFF
                if glyph:
                    mapping[cp] = glyph

    elif fmt == 12:
        groups = struct.unpack_from(">I", data, table + 12)[0]
        for g in range(groups):
            start, end, glyph = struct.unpack_from(">III", data, table + 16 + 12 * g)
            for cp in range(start, min(end, start + 0x10000) + 1):
                mapping[cp] = glyph + (cp - start)

    elif fmt == 6:
        first, count6 = struct.unpack_from(">HH", data, table + 6)
        for i in range(count6):
            mapping[first + i] = struct.unpack_from(">H", data, table + 10 + 2 * i)[0]

    elif fmt == 0:
        for cp in range(256):
            mapping[cp] = data[table + 6 + cp]

    return mapping


def _parse(path: Path) -> "FontMetrics | None":
    data = path.read_bytes()
    tables = _tables(data)
    if not {"head", "hhea", "hmtx", "cmap"} <= set(tables):
        return None

    units_per_em = struct.unpack_from(">H", data, tables["head"][0] + 18)[0]
    if not units_per_em:
        return None
    num_h_metrics = struct.unpack_from(">H", data, tables["hhea"][0] + 34)[0]
    if not num_h_metrics:
        return None

    hmtx = tables["hmtx"][0]
    widths = []
    for i in range(num_h_metrics):
        widths.append(struct.unpack_from(">H", data, hmtx + 4 * i)[0])
    # Glyphs past numberOfHMetrics all reuse the final advance (monospace tail).
    last = widths[-1]

    cmap = _parse_cmap(data, tables["cmap"][0])
    advances = {}
    for cp, glyph in cmap.items():
        advances[cp] = widths[glyph] if glyph < len(widths) else last

    cap_height = None
    if "OS/2" in tables:
        os2, length = tables["OS/2"]
        version = struct.unpack_from(">H", data, os2)[0]
        if version >= 2 and length >= 90:
            cap_height = struct.unpack_from(">h", data, os2 + 88)[0] or None

    space = advances.get(ord(" "), units_per_em // 4)
    metrics = FontMetrics(path, units_per_em, advances, space, cap_height, glyph_ids=cmap)

    if {"loca", "glyf", "maxp"} <= set(tables):
        long_offsets = struct.unpack_from(">h", data, tables["head"][0] + 50)[0] == 1
        n_glyphs = struct.unpack_from(">H", data, tables["maxp"][0] + 4)[0]
        loca_off = tables["loca"][0]
        if long_offsets:
            loca = struct.unpack_from(">%dI" % (n_glyphs + 1), data, loca_off)
        else:
            loca = tuple(v * 2 for v in struct.unpack_from(">%dH" % (n_glyphs + 1), data, loca_off))
        metrics._glyf = (data, loca, tables["glyf"][0])
    return metrics



# ---------------------------------------------------------------- glyf
_ON_CURVE, _X_SHORT, _Y_SHORT, _REPEAT, _X_SAME, _Y_SAME = 1, 2, 4, 8, 16, 32
_ARGS_WORDS, _ARGS_XY, _HAVE_SCALE, _MORE, _HAVE_XY_SCALE, _HAVE_2X2 = 1, 2, 8, 32, 64, 128


def _fmt_units(value: float) -> str:
    text = "%.1f" % value
    return text[:-2] if text.endswith(".0") else text


def _glyph_points(metrics, glyph_id, depth):
    """Contours of one glyph as lists of (x, y, on_curve), font units."""
    data, loca, glyf = metrics._glyf
    if glyph_id + 1 >= len(loca) or depth > 8:
        return []
    start, end = glyf + loca[glyph_id], glyf + loca[glyph_id + 1]
    if end <= start:
        return []  # empty glyph, e.g. space
    contours_n = struct.unpack_from(">h", data, start)[0]
    pos = start + 10

    if contours_n < 0:  # composite: assemble from components
        out = []
        while True:
            flags, component = struct.unpack_from(">HH", data, pos)
            pos += 4
            if flags & _ARGS_WORDS:
                dx, dy = struct.unpack_from(">hh", data, pos)
                pos += 4
            else:
                dx, dy = struct.unpack_from(">bb", data, pos)
                pos += 2
            a = d = 1.0
            b = c = 0.0
            if flags & _HAVE_SCALE:
                a = d = struct.unpack_from(">h", data, pos)[0] / 16384.0
                pos += 2
            elif flags & _HAVE_XY_SCALE:
                a, d = (v / 16384.0 for v in struct.unpack_from(">hh", data, pos))
                pos += 4
            elif flags & _HAVE_2X2:
                a, b, c, d = (v / 16384.0 for v in struct.unpack_from(">hhhh", data, pos))
                pos += 8
            if not flags & _ARGS_XY:
                dx = dy = 0  # point-matching placement: rare, approximated as no offset
            for contour in _glyph_points(metrics, component, depth + 1):
                out.append([(a * x + c * y + dx, b * x + d * y + dy, on) for x, y, on in contour])
            if not flags & _MORE:
                break
        return out

    ends = struct.unpack_from(">%dH" % contours_n, data, pos)
    pos += 2 * contours_n
    n_points = (ends[-1] + 1) if contours_n else 0
    instr_len = struct.unpack_from(">H", data, pos)[0]
    pos += 2 + instr_len

    flags = []
    while len(flags) < n_points:
        flag = data[pos]
        pos += 1
        flags.append(flag)
        if flag & _REPEAT:
            count = data[pos]
            pos += 1
            flags.extend([flag] * count)
    flags = flags[:n_points]

    def coords(short_bit, same_bit):
        nonlocal pos
        values, value = [], 0
        for flag in flags:
            if flag & short_bit:
                delta = data[pos]
                pos += 1
                value += delta if flag & same_bit else -delta
            elif not flag & same_bit:
                value += struct.unpack_from(">h", data, pos)[0]
                pos += 2
            values.append(value)
        return values

    xs = coords(_X_SHORT, _X_SAME)
    ys = coords(_Y_SHORT, _Y_SAME)
    points = [(x, y, bool(f & _ON_CURVE)) for x, y, f in zip(xs, ys, flags)]
    contours, first = [], 0
    for last in ends:
        contours.append(points[first:last + 1])
        first = last + 1
    return contours


def _contour_path(points) -> str:
    """One closed TrueType contour -> SVG path commands (quadratic splines)."""
    if not points:
        return ""
    # Rotate so we start on an on-curve point; if there is none, start at
    # the implied midpoint between the first two off-curve points.
    on = [i for i, p in enumerate(points) if p[2]]
    if on:
        points = points[on[0]:] + points[:on[0]]
        start = points[0][:2]
        seq = points[1:] + [points[0]]
    else:
        start = ((points[0][0] + points[1][0]) / 2.0, (points[0][1] + points[1][1]) / 2.0)
        seq = points[1:] + points[:1]
    out = ["M%s %s" % (_fmt_units(start[0]), _fmt_units(start[1]))]
    control = None
    for x, y, on_curve in seq:
        if on_curve:
            if control is None:
                out.append("L%s %s" % (_fmt_units(x), _fmt_units(y)))
            else:
                out.append("Q%s %s %s %s" % (_fmt_units(control[0]), _fmt_units(control[1]),
                                              _fmt_units(x), _fmt_units(y)))
                control = None
        else:
            if control is not None:  # implied on-curve midpoint
                mx, my = (control[0] + x) / 2.0, (control[1] + y) / 2.0
                out.append("Q%s %s %s %s" % (_fmt_units(control[0]), _fmt_units(control[1]),
                                              _fmt_units(mx), _fmt_units(my)))
            control = (x, y)
    if control is not None:
        out.append("Q%s %s %s %s" % (_fmt_units(control[0]), _fmt_units(control[1]),
                                      _fmt_units(start[0]), _fmt_units(start[1])))
    out.append("Z")
    return "".join(out)


def _glyph_outline(metrics, glyph_id, depth) -> str:
    return "".join(_contour_path(c) for c in _glyph_points(metrics, glyph_id, depth))


_NUMBER = None


def _shift_path(d: str, dx_units: float, scale: float) -> str:
    """Re-emit a font-unit path shifted by ``dx_units`` and scaled to output
    units with y flipped, so the result sits on a y-down canvas."""
    import re
    global _NUMBER
    if _NUMBER is None:
        _NUMBER = re.compile(r"[MLQZ]|-?\d+(?:\.\d+)?")
    tokens = _NUMBER.findall(d)
    out, i = [], 0
    while i < len(tokens):
        cmd = tokens[i]
        i += 1
        if cmd == "Z":
            out.append("Z")
            continue
        n = {"M": 1, "L": 1, "Q": 2}[cmd]
        coords = []
        for _ in range(n):
            x = (float(tokens[i]) + dx_units) * scale
            y = -float(tokens[i + 1]) * scale
            i += 2
            coords.append("%s %s" % (_fmt_mm(x), _fmt_mm(y)))
        out.append(cmd + " ".join(coords))
    return "".join(out)


def _fmt_mm(value: float) -> str:
    text = "%.3f" % value
    text = text.rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


# ---------------------------------------------------------------- lookup
def find_font(family: str, weight=400) -> Path | None:
    """Locate a font file for ``family`` at ``weight``."""
    try:
        weight = int(weight)
    except (TypeError, ValueError):
        weight = 400
    style = WEIGHT_NAMES.get(weight, "Regular")
    compact = family.replace(" ", "")

    def scan(directory: Path) -> Path | None:
        for pattern in ("%s-%s" % (compact, style), "%s%s" % (compact, style), compact):
            for suffix in (".ttf", ".otf", ".ttc"):
                hit = directory / (pattern + suffix)
                if hit.is_file():
                    return hit
        return None

    # The bundled fonts win, so the default theme renders identically on
    # every machine regardless of what happens to be installed.
    bundled = scan(BUNDLED_FONTS)
    if bundled:
        return bundled

    if shutil.which("fc-match"):
        query = "%s:style=%s" % (family, style)
        result = subprocess.run(["fc-match", "-f", "%{file}", query],
                                capture_output=True, text=True)
        candidate = Path(result.stdout.strip()) if result.stdout.strip() else None
        # fc-match always answers, even with an unrelated font, so only trust
        # a result whose filename actually looks like the family we asked for.
        if candidate and candidate.exists():
            stem = candidate.stem.replace(" ", "").lower()
            if family.replace(" ", "").lower() in stem:
                return candidate

    for directory in FONT_DIRS:
        if directory.is_dir():
            hit = scan(directory)
            if hit:
                return hit
    return None


def load(family: str, weight=400) -> "FontMetrics | None":
    """Metrics for ``family`` at ``weight``, or ``None``.  Cached; never raises."""
    key = (family, str(weight))
    if key in _CACHE:
        return _CACHE[key]
    metrics = None
    try:
        path = find_font(family, weight)
        if path:
            metrics = _parse(path)
    except Exception:  # noqa: BLE001 - a broken font must not break rendering
        metrics = None
    _CACHE[key] = metrics
    return metrics
