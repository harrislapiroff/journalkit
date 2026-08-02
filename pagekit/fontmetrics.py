"""Advance widths and cap height, read straight out of the font file.

Only used to decide how much room a label needs so the dot lattice can keep
clear of it.  That job wants a real number, not a guess, but it does not want a
dependency either — so this is a deliberately small sfnt reader over the four
tables that matter (``head``, ``hhea``, ``hmtx``, ``cmap``, plus ``OS/2`` for
the cap height).  It reads TrueType and CFF/OpenType alike, since both carry
horizontal metrics in the same tables.

Everything here fails soft: if the font cannot be found or parsed,
:func:`load` returns ``None`` and the caller falls back to an estimate.  A
missing font must never be the reason a page fails to render.

    >>> metrics = load("Montserrat", weight=500)
    >>> metrics.text_width("GRATITUDE", 2.822)   # size in mm -> width in mm
    16.87...

Kerning (``GPOS``) is not applied.  Kerning almost always pulls glyphs closer
together, so a plain sum of advances errs wide — the safe direction when the
number is used to reserve space.
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
    return FontMetrics(path, units_per_em, advances, space, cap_height)


# ---------------------------------------------------------------- lookup
def find_font(family: str, weight=400) -> Path | None:
    """Locate a font file for ``family`` at ``weight``."""
    try:
        weight = int(weight)
    except (TypeError, ValueError):
        weight = 400
    style = WEIGHT_NAMES.get(weight, "Regular")

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

    compact = family.replace(" ", "")
    for directory in FONT_DIRS:
        if not directory.is_dir():
            continue
        for pattern in ("%s-%s" % (compact, style), "%s%s" % (compact, style), compact):
            for suffix in (".ttf", ".otf", ".ttc"):
                hit = directory / (pattern + suffix)
                if hit.is_file():
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
