#!/usr/bin/env python3
"""Normalise raw SVG exports into JournalKit icons.

Icons in ``icons/`` are plain SVGs whose viewBox is a *tight* bounding box of
their artwork and whose paths use ``fill="currentColor"``.  Anything that meets
those two conditions is a valid icon; this script just makes it easy to get
there from an Illustrator/Inkscape export, which typically leaves the artwork
floating somewhere inside a page-sized viewBox.

    python3 tools/extract_icons.py raw/*.svg -o icons/

The bounding box is computed by flattening the path data, so no external
dependency is required.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PT_PER_MM = 72 / 25.4

NUM = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
CMD = re.compile(r"([MmZzLlHhVvCcSsQqTtAa])")


def _numbers(text: str) -> list[float]:
    return [float(m.group()) for m in NUM.finditer(text)]


def _bezier(p0, p1, p2, p3, steps=48):
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        yield (
            u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0],
            u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1],
        )


def _quad(p0, p1, p2, steps=32):
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        yield (
            u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
            u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1],
        )


def path_points(d: str):
    """Yield sampled points along a path's outline (adequate for a bbox)."""
    tokens = [t for t in CMD.split(d) if t.strip()]
    cur = (0.0, 0.0)
    start = (0.0, 0.0)
    prev_cubic_ctrl = None
    prev_quad_ctrl = None
    i = 0
    while i < len(tokens):
        cmd = tokens[i]
        args = _numbers(tokens[i + 1]) if i + 1 < len(tokens) and not CMD.fullmatch(tokens[i + 1]) else []
        i += 2 if args else 1
        rel = cmd.islower()
        c = cmd.upper()

        def pt(x, y):
            return (cur[0] + x, cur[1] + y) if rel else (x, y)

        if c == "M":
            for j in range(0, len(args) - 1, 2):
                cur = pt(args[j], args[j + 1])
                if j == 0:
                    start = cur
                yield cur
            prev_cubic_ctrl = prev_quad_ctrl = None
        elif c == "L":
            for j in range(0, len(args) - 1, 2):
                cur = pt(args[j], args[j + 1])
                yield cur
            prev_cubic_ctrl = prev_quad_ctrl = None
        elif c == "H":
            for v in args:
                cur = (cur[0] + v, cur[1]) if rel else (v, cur[1])
                yield cur
            prev_cubic_ctrl = prev_quad_ctrl = None
        elif c == "V":
            for v in args:
                cur = (cur[0], cur[1] + v) if rel else (cur[0], v)
                yield cur
            prev_cubic_ctrl = prev_quad_ctrl = None
        elif c in ("C", "S"):
            stride = 6 if c == "C" else 4
            for j in range(0, len(args) - stride + 1, stride):
                a = args[j : j + stride]
                if c == "C":
                    c1, c2, end = pt(a[0], a[1]), pt(a[2], a[3]), pt(a[4], a[5])
                else:
                    c1 = (2 * cur[0] - prev_cubic_ctrl[0], 2 * cur[1] - prev_cubic_ctrl[1]) if prev_cubic_ctrl else cur
                    c2, end = pt(a[0], a[1]), pt(a[2], a[3])
                yield from _bezier(cur, c1, c2, end)
                cur, prev_cubic_ctrl = end, c2
            prev_quad_ctrl = None
        elif c in ("Q", "T"):
            stride = 4 if c == "Q" else 2
            for j in range(0, len(args) - stride + 1, stride):
                a = args[j : j + stride]
                if c == "Q":
                    c1, end = pt(a[0], a[1]), pt(a[2], a[3])
                else:
                    c1 = (2 * cur[0] - prev_quad_ctrl[0], 2 * cur[1] - prev_quad_ctrl[1]) if prev_quad_ctrl else cur
                    end = pt(a[0], a[1])
                yield from _quad(cur, c1, end)
                cur, prev_quad_ctrl = end, c1
            prev_cubic_ctrl = None
        elif c == "A":
            # Approximate: the endpoint alone is enough for icon bboxes in
            # practice, and Illustrator exports never emit arcs.
            for j in range(0, len(args) - 6, 7):
                cur = pt(args[j + 5], args[j + 6])
                yield cur
        elif c == "Z":
            cur = start
            yield cur


def bbox(paths: list[str]):
    xs, ys = [], []
    for d in paths:
        for x, y in path_points(d):
            xs.append(x)
            ys.append(y)
    if not xs:
        raise ValueError("no drawable geometry found")
    return min(xs), min(ys), max(xs), max(ys)


def normalise(src: Path, dest_dir: Path, pad: float = 0.0) -> Path:
    text = src.read_text()
    body = re.sub(r"<defs.*?</defs>", "", text, flags=re.S)
    paths = re.findall(r"<path\b[^>]*?/>", body, re.S)
    if not paths:
        raise ValueError(f"{src}: no <path> elements")

    ds = [re.search(r'\sd="([^"]*)"', p, re.S).group(1) for p in paths]
    x0, y0, x1, y1 = bbox(ds)
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    w, h = x1 - x0, y1 - y0

    out_paths = []
    for p in paths:
        d = re.search(r'\sd="([^"]*)"', p, re.S).group(1)
        fill = re.search(r'\sfill="([^"]*)"', p)
        stroke = re.search(r'\sstroke="([^"]*)"', p)
        attrs = ['d="%s"' % d]
        if stroke and stroke.group(1) != "none":
            sw = re.search(r'\sstroke-width="([^"]*)"', p)
            attrs.append('fill="none" stroke="currentColor"')
            attrs.append('stroke-width="%s"' % (sw.group(1) if sw else "1"))
        else:
            # White fills are knockouts (e.g. a checkbox sitting on a dot
            # grid) and must stay white; everything else follows the theme.
            colour = "#ffffff" if fill and fill.group(1).lower() in ("#ffffff", "white") else "currentColor"
            attrs.append('fill="%s"' % colour)
        rule = re.search(r'\sfill-rule="([^"]*)"', p)
        if rule:
            attrs.append('fill-rule="%s"' % rule.group(1))
        out_paths.append("  <path %s/>" % " ".join(attrs))

    dest = dest_dir / src.name
    dest.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'viewBox="%.4f %.4f %.4f %.4f" width="%.4fmm" height="%.4fmm">\n%s\n</svg>\n'
        % (x0, y0, w, h, w / PT_PER_MM, h / PT_PER_MM, "\n".join(out_paths))
    )
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sources", nargs="+", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=Path("icons"))
    ap.add_argument("--pad", type=float, default=0.0, help="padding in source units")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    for src in args.sources:
        try:
            dest = normalise(src, args.out, args.pad)
        except ValueError as exc:
            print("skip %s: %s" % (src, exc), file=sys.stderr)
            continue
        print("wrote %s" % dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
