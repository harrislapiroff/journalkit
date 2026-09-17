#!/usr/bin/env python3
"""Repo-only tasks for working *on* JournalKit — not installed with the tool.

    .venv/bin/python tools/dev.py smoke

The things a user of JournalKit needs (build, watch, preview, check, doctor)
live in the ``journalkit`` command. This script holds what only the checkout
needs: the test suite, the end-to-end smoke run, and a few measurement tools
for checking rendered geometry while changing the renderer.

    doctor   `journalkit doctor` on the example, plus the venv
    test     run tests/
    smoke    build the example journal, tests, check, pdf geometry
    clean    delete the example's out/
    geom     rendered ink geometry in mm, via inkscape --query-all
    ink      sub-grid rects drawn *inside* modules (informational)
    pages    page count + MediaBox of a PDF, in mm

`doctor` deliberately touches only the standard library so it can diagnose a
machine that has not been set up yet: ``python3 tools/dev.py doctor``.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "journal"
OUT = EXAMPLE / "out"
PX_PER_MM = 96 / 25.4
PIP_SETUP = "python3 -m venv .venv && .venv/bin/pip install -e ."


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def _python() -> str:
    """Interpreter to run journalkit with: the project venv when it exists."""
    venv = ROOT / ".venv" / "bin" / "python"
    return str(venv) if venv.exists() else sys.executable


def _journalkit(*args) -> subprocess.CompletedProcess:
    return sh([_python(), "-m", "journalkit", *args], cwd=ROOT)


def _setup_hint() -> str:
    if (ROOT / "poetry.lock").exists() and shutil.which("poetry"):
        return "poetry install"
    return PIP_SETUP


def ok(msg):
    print("  ok   %s" % msg)


def bad(msg):
    print("  FAIL %s" % msg)


# ---------------------------------------------------------------- doctor
def cmd_doctor(args) -> int:
    problems = []
    print("checkout:")
    venv_py = ROOT / ".venv" / "bin" / "python"
    if venv_py.exists():
        ok("venv       %s" % venv_py)
    else:
        bad("venv       missing — run: %s" % _setup_hint())
        problems.append("venv")
    if (ROOT / ".venv" / "bin" / "journalkit").exists():
        ok("journalkit console script installed")
    else:
        bad("journalkit console script missing — run: %s" % _setup_hint())
        problems.append("script")

    if venv_py.exists():
        print()
        result = _journalkit("doctor", str(EXAMPLE))
        print(result.stdout.rstrip())
        if result.stderr.strip():
            print(result.stderr.rstrip())
        if result.returncode:
            problems.append("journalkit doctor")
    print("\n%s" % ("all prerequisites satisfied" if not problems
                    else "MISSING: %s" % ", ".join(problems)))
    return 1 if problems else 0


# ---------------------------------------------------------------- measure
RECT = re.compile(r"<rect\s[^>]*/>")
ATTR = re.compile(r'([\w-]+)="([^"]*)"')


def _rects(svg_text: str):
    for tag in RECT.findall(svg_text):
        attrs = dict(ATTR.findall(tag))
        try:
            yield (float(attrs["x"]), float(attrs["y"]),
                   float(attrs["width"]), float(attrs["height"]))
        except (KeyError, ValueError):
            continue


def cmd_ink(args) -> int:
    """Report sub-grid geometry *inside* modules — informational, never fails.

    `journalkit check` deliberately ignores what a module draws inside its own
    rect (habit_grid's 6mm columns, icon placements). This shows it.
    """
    svgs = [Path(p) for p in args.svg] or sorted(OUT.glob("*.svg"))
    if not svgs:
        print("no SVGs — build the example first", file=sys.stderr)
        return 1
    for svg in svgs:
        rects = list(_rects(svg.read_text()))
        off = [r for r in rects[1:]
               if any(abs(v - round(v / args.grid) * args.grid) > 1e-6 for v in r)]
        print("%-42s %3d rects, %d sub-grid" % (svg.name, len(rects) - 1, len(off)))
        for x, y, w, h in off[:6]:
            print("    rect(%.3f, %.3f, %.3f, %.3f)" % (x, y, w, h))
    return 0


def cmd_geom(args) -> int:
    """Rendered object geometry in millimetres, via inkscape --query-all.

    Reports *ink* bounds, so it includes text and placed icons — the tool for
    checking a layout change against measured artwork.
    """
    if not shutil.which("inkscape"):
        print("inkscape not found — see `journalkit doctor`", file=sys.stderr)
        return 1
    svg = Path(args.svg) if Path(args.svg).is_absolute() else ROOT / args.svg
    if not svg.exists():
        print("no such SVG: %s" % svg, file=sys.stderr)
        return 1
    result = sh(["inkscape", "--query-all", str(svg)])
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return 1
    rows = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(",")
        if len(parts) != 5:
            continue
        try:
            values = [float(v) / PX_PER_MM for v in parts[1:]]
        except ValueError:
            continue
        rows.append((parts[0], *values))
    print("%-14s %8s %8s %8s %8s %8s %8s" % ("id", "x", "y", "w", "h", "right", "bottom"))
    for ident, x, y, w, h in rows:
        if w < args.min_size and h < args.min_size:
            continue
        print("%-14s %8.2f %8.2f %8.2f %8.2f %8.2f %8.2f" % (ident, x, y, w, h, x + w, y + h))
    return 0


def cmd_pages(args) -> int:
    """Page count and MediaBox of a PDF, in mm — checks the physical size."""
    pdf = Path(args.pdf) if Path(args.pdf).is_absolute() else ROOT / args.pdf
    if not pdf.exists():
        print("no such PDF: %s" % pdf, file=sys.stderr)
        return 1
    data = pdf.read_bytes()
    boxes = set()
    for match in re.findall(rb"/MediaBox\s*\[([^\]]*)\]", data):
        nums = [float(v) for v in match.split()]
        if len(nums) == 4:
            boxes.add((round((nums[2] - nums[0]) * 25.4 / 72, 2),
                       round((nums[3] - nums[1]) * 25.4 / 72, 2)))
    count = len(re.findall(rb"/Type\s*/Page[^s]", data))
    print("%s: %d page(s)" % (pdf.name, count))
    for w, h in sorted(boxes):
        print("  MediaBox %.2f x %.2f mm" % (w, h))
    return 0 if boxes else 1


# ---------------------------------------------------------------- test / clean / smoke
def cmd_test(args) -> int:
    result = sh([_python(), str(ROOT / "tests" / "test_journalkit.py")], cwd=ROOT)
    print(result.stdout.rstrip() or result.stderr.rstrip())
    return result.returncode


def cmd_clean(args) -> int:
    for path in (OUT, ROOT / "dist"):
        if path.exists():
            shutil.rmtree(path)
            print("removed %s" % path)
    return 0


def _step(title, result: subprocess.CompletedProcess, tail=None) -> int:
    print("\n=== %s ===" % title)
    text = result.stdout.rstrip()
    if tail and text:
        text = "\n".join(text.splitlines()[-tail:])
    print(text or "(no output)")
    if result.stderr.strip():
        print(result.stderr.rstrip())
    return result.returncode


def cmd_smoke(args) -> int:
    """Everything, end to end, against the example journal."""
    steps = []
    print("=== doctor ===")
    steps.append(("doctor", cmd_doctor(argparse.Namespace())))
    steps.append(("build", _step("build (svg + pdf + png)",
                                 _journalkit("build", str(EXAMPLE), "--pdf", "--png", "--dpi", "110"))))
    steps.append(("tests", _step("tests", sh([_python(), str(ROOT / "tests" / "test_journalkit.py")],
                                             cwd=ROOT), tail=1)))
    steps.append(("check", _step("check (grid + fonts)", _journalkit("check", str(EXAMPLE)))))
    print("\n=== pdf geometry ===")
    steps.append(("pages", cmd_pages(argparse.Namespace(pdf=str(OUT / "daily.pdf")))))

    print("\n" + "=" * 46)
    for name, code in steps:
        print("%-8s %s" % (name, "ok" if code == 0 else "FAILED"))
    failed = [n for n, c in steps if c != 0]
    print("\n%s" % ("SMOKE PASSED" if not failed else "SMOKE FAILED: %s" % ", ".join(failed)))
    return 1 if failed else 0


# ---------------------------------------------------------------- main
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="tools/dev.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="venv + `journalkit doctor` on the example").set_defaults(func=cmd_doctor)
    sub.add_parser("test", help="run the test suite").set_defaults(func=cmd_test)
    sub.add_parser("smoke", help="build the example, tests, check, pdf geometry").set_defaults(func=cmd_smoke)
    sub.add_parser("clean", help="delete examples/journal/out and dist/").set_defaults(func=cmd_clean)

    p = sub.add_parser("geom", help="rendered ink geometry in mm (inkscape)")
    p.add_argument("svg")
    p.add_argument("--min-size", type=float, default=3.0, help="hide objects smaller than this")
    p.set_defaults(func=cmd_geom)

    p = sub.add_parser("ink", help="report sub-grid geometry drawn inside modules")
    p.add_argument("svg", nargs="*", help="default: examples/journal/out/*.svg")
    p.add_argument("--grid", type=float, default=2.0, help="grid to compare against (default 2)")
    p.set_defaults(func=cmd_ink)

    p = sub.add_parser("pages", help="page count + MediaBox in mm")
    p.add_argument("pdf")
    p.set_defaults(func=cmd_pages)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
