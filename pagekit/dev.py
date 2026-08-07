#!/usr/bin/env python3
"""Drive pagekit: render, look, and verify.

pagekit has no GUI and no server — its "running app" is a set of print
artifacts. So driving it means three things, and this script does all three:

    render   turn YAML into SVG/PDF/PNG — once, or on every change (`watch`)
    look     rasterise a page so an agent can Read() the image
    verify   assert the invariants that make the output correct

The verify half is the part you can't do by eye. `grid` proves every module
still lands on the 2.5mm grid; `fonts` proves Inkscape embedded Montserrat
instead of silently substituting; `geom` reports rendered ink positions in
millimetres so a layout change can be diffed numerically.

Exposed as the `pagekit-dev` console script (see pyproject.toml).  Before the
package is installed, run it from the project root as::

    python3 -m pagekit.dev doctor

`doctor` deliberately touches only the standard library so it can diagnose a
machine that has not been set up yet.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    """The checkout we are driving.

    Normally the parent of this package.  Falls back to the working directory
    so a non-editable install still drives whatever project you stand in.
    """
    here = Path(__file__).resolve().parents[1]
    if (here / "templates").is_dir():
        return here
    return Path.cwd()


ROOT = _project_root()
OUT = ROOT / "out"
PX_PER_MM = 96 / 25.4
GRID = 2.5
FONT = "Montserrat"
PIP_SETUP = "python3 -m venv .venv && .venv/bin/pip install -e ."


def _setup_hint() -> str:
    """The setup command to suggest, for whichever toolchain is available."""
    if (ROOT / "poetry.lock").exists() and shutil.which("poetry"):
        return "poetry install"
    return PIP_SETUP

sys.path.insert(0, str(ROOT))


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def _python() -> str:
    """Interpreter to run pagekit with.

    Prefer the project's venv so `python3 -m pagekit.dev` works before the
    package is installed; otherwise whatever is running us already has it.
    """
    venv = ROOT / ".venv" / "bin" / "python"
    return str(venv) if venv.exists() else sys.executable


def ok(msg):
    print("  ok   %s" % msg)


def bad(msg):
    print("  FAIL %s" % msg)


# ---------------------------------------------------------------- doctor
def cmd_doctor(args) -> int:
    """Check every external thing this project needs before you waste time."""
    problems = []

    print("prerequisites:")
    for tool, why, install in [
        ("inkscape", "SVG->PDF/PNG with font embedding", "brew install --cask inkscape"),
        ("gs", "merging per-page PDFs into one document", "brew install ghostscript"),
    ]:
        path = shutil.which(tool)
        if path:
            ok("%-9s %s" % (tool, path))
        else:
            bad("%-9s missing — %s (needed for %s)" % (tool, install, why))
            problems.append(tool)

    venv_py = ROOT / ".venv" / "bin" / "python"
    if venv_py.exists():
        ok("venv      %s" % venv_py)
    else:
        bad("venv      missing — run: %s" % _setup_hint())
        problems.append("venv")

    if (ROOT / ".venv" / "bin" / "pagekit").exists():
        ok("pagekit   console script installed (cwd-independent)")
    else:
        bad("pagekit   console script missing — run: %s" % _setup_hint())
        problems.append("pagekit-script")

    # Check pyyaml *in the venv*, not in whichever interpreter is running this
    # script — doctor is meant to be runnable with system python3 before the
    # venv exists, and importing here would report the wrong environment.
    if venv_py.exists():
        probe = sh([str(venv_py), "-c", "import yaml; print(yaml.__version__)"])
        if probe.returncode == 0:
            ok("pyyaml    %s (in venv)" % probe.stdout.strip())
        else:
            bad("pyyaml    missing from venv — run: %s" % _setup_hint())
            problems.append("pyyaml")
    else:
        bad("pyyaml    unknown — no venv to check")
        problems.append("pyyaml")

    # The font is the silent killer: Inkscape substitutes without warning.
    fc = shutil.which("fc-list")
    if fc:
        found = sh([fc, "-f", "%{family}\n"]).stdout
        if FONT.lower() in found.lower():
            ok("%s font installed" % FONT)
        else:
            bad("%s NOT installed — text will silently render as Verdana" % FONT)
            problems.append("font")
    else:
        # macOS without fontconfig: fall back to the font directories.
        hits = list((Path.home() / "Library/Fonts").glob("%s*" % FONT))
        hits += list(Path("/Library/Fonts").glob("%s*" % FONT))
        if hits:
            ok("%s font installed (%d files)" % (FONT, len(hits)))
        else:
            bad("%s NOT found in ~/Library/Fonts or /Library/Fonts" % FONT)
            problems.append("font")

    print("\n%s" % ("all prerequisites satisfied" if not problems
                    else "MISSING: %s" % ", ".join(problems)))
    return 1 if problems else 0


# ---------------------------------------------------------------- render
def _templates(args):
    if args.template:
        return [Path(t) if Path(t).is_absolute() else ROOT / t for t in args.template]
    return sorted((ROOT / "templates").glob("*.yaml"))


def _build(template: Path, out_dir: Path, pdf=False, png=False, dpi=150, debug=False):
    cmd = [_python(), "-m", "pagekit", "build", str(template), "-o", str(out_dir)]
    if pdf:
        cmd.append("--pdf")
    if png:
        cmd += ["--png", "--dpi", str(dpi)]
    if debug:
        cmd.append("--debug")
    # cwd=ROOT matters: `python -m pagekit` resolves the package from cwd
    # unless `pip install -e .` has been run.
    return sh(cmd, cwd=ROOT)


def cmd_build(args) -> int:
    failed = 0
    for template in _templates(args):
        result = _build(template, OUT, pdf=args.pdf, png=args.png, dpi=args.dpi,
                        debug=args.debug)
        print("== %s (exit %d)" % (template.name, result.returncode))
        print(result.stdout.rstrip() or "(no output)")
        if result.stderr.strip():
            print(result.stderr.rstrip())
        failed += result.returncode != 0
    return 1 if failed else 0


# ---------------------------------------------------------------- watch
# Everything a build reads. Templates are the obvious input, but a layout
# change in the library or a re-extracted icon changes the output just as
# much, so all of it is watched.
WATCH_GLOBS = ("templates/*.yaml", "custom/*.py", "icons/*.svg",
               "pagekit/*.py", "pagekit/modules/*.py")
SETTLE = 0.3    # quiet period before building, so one save is one build


def _stamps(extra=()):
    """{path: mtime} for every watched file, re-globbed so new files appear."""
    paths = set(extra)
    for pattern in WATCH_GLOBS:
        paths.update(ROOT.glob(pattern))
    found = {}
    for path in paths:
        try:
            found[path] = path.stat().st_mtime
        except OSError:
            pass  # deleted mid-scan; the next poll reports it as a change
    return found


def cmd_watch(args) -> int:
    """Rebuild whenever an input file changes, until interrupted.

    Polls mtimes rather than using an OS watch API: the file count here is in
    the dozens, and polling keeps the harness on the standard library.

    Editing a template rebuilds only that template; touching the library,
    icons or a custom module rebuilds everything, because any of those can
    change every page.
    """
    import time

    # Flush every line: the watcher is long-lived, and its stdout is often a
    # pipe (an agent tailing a log), where print would otherwise block-buffer
    # and show nothing until it exits.
    def say(text=""):
        print(text, flush=True)

    pdf, png = not args.no_pdf, args.png
    what = "svg" + (" + pdf" if pdf else "") + (" + png" if png else "")
    targets = _templates(args)
    watched = dict.fromkeys(g.split("/")[0] for g in WATCH_GLOBS)
    say("watching %s for changes → %s (%s)"
        % (", ".join(watched), what, OUT))
    say("ctrl-c to stop\n")

    def build(templates):
        for template in templates:
            started = time.monotonic()
            result = _build(template, OUT, pdf=pdf, png=png, dpi=args.dpi,
                            debug=args.debug)
            written = sum(line.startswith("wrote")
                          for line in result.stdout.splitlines())
            say("  %-18s %-7s %d file(s)  %4.1fs"
                % (template.name, "ok" if result.returncode == 0 else "FAILED",
                   written, time.monotonic() - started))
            # Warnings (off-grid snapping, overflow) come back on stderr with
            # exit code 0 — surfacing them is most of the point of watching.
            for line in result.stderr.splitlines():
                if line.strip():
                    say("      %s" % line)

    seen = _stamps(targets)
    say("[%s] initial build" % time.strftime("%H:%M:%S"))
    build(targets)

    try:
        while True:
            time.sleep(args.interval)
            now = _stamps(targets)
            changed = sorted(p for p in set(seen) | set(now)
                             if seen.get(p) != now.get(p))
            if not changed:
                continue

            # Let a burst of writes settle, so saving several files at once —
            # or an editor's write-temp-then-rename — is a single rebuild.
            while True:
                time.sleep(SETTLE)
                settled = _stamps(targets)
                if settled == now:
                    break
                changed = sorted(set(changed) | {p for p in set(now) | set(settled)
                                                 if now.get(p) != settled.get(p)})
                now = settled
            seen = now

            targets = _templates(args)
            touched = [t for t in targets if t in changed]
            rebuild = touched if len(touched) == len(changed) else targets

            say("\n[%s] %s" % (time.strftime("%H:%M:%S"),
                               ", ".join(p.name for p in changed[:4])
                               + (" +%d more" % (len(changed) - 4) if len(changed) > 4 else "")))
            build(rebuild)
    except KeyboardInterrupt:
        say("\nstopped")
        return 0


def cmd_shot(args) -> int:
    """Render a template and rasterise a page — the 'look at it' path."""
    template = Path(args.template) if Path(args.template).is_absolute() else ROOT / args.template
    dest = OUT / "shots"
    dest.mkdir(parents=True, exist_ok=True)
    result = _build(template, dest, png=True, dpi=args.dpi, debug=args.debug)
    if result.returncode != 0:
        print(result.stdout + result.stderr)
        return 1
    shots = sorted(dest.glob("*.png"))
    if args.page is not None:
        shots = [s for s in shots if "-%02d-" % args.page in s.name]
    for shot in shots:
        print(shot)
    if not shots:
        print("no PNGs produced", file=sys.stderr)
        return 1
    return 0


PREVIEW_DOC = """document: preview
page:
  size: [105, 170]
  margins: {top: 2.5, bottom: 7.5, inner: 25, outer: 5}
grid:
  module: 2.5
  dots: {spacing: 5, origin: [0, 2.5], radius: 0.125}
defaults: {gap: 2.5}
theme:
  font: {family: Montserrat}
  label: {size: 8pt, weight: 500}
  heading: {size: 12pt, weight: 700}
templates:
  preview:
    side: right
    content:
%s
pages: [{template: preview}]
"""


def cmd_preview(args) -> int:
    """Render an ad-hoc module list from stdin — the module-dev loop.

    Feed it just the `content:` entries; everything else is boilerplate:

        echo '- {type: box, label: HELLO, height: 20, dots: true}' | pagekit-dev preview
    """
    snippet = sys.stdin.read().strip()
    if not snippet:
        print("nothing on stdin", file=sys.stderr)
        return 1
    indented = "\n".join("      " + line for line in snippet.splitlines())

    dest = OUT / "preview"
    dest.mkdir(parents=True, exist_ok=True)
    doc = dest / "preview.yaml"
    header = ""
    if args.modules:
        # Resolve against the project root, not the temp doc's directory, so
        # `--modules custom/habits.py` reads the way you'd expect.
        paths = [Path(m) if Path(m).is_absolute() else (ROOT / m).resolve()
                 for m in args.modules]
        header = "modules:\n" + "".join("  - %s\n" % p for p in paths)
    doc.write_text(header + PREVIEW_DOC % indented)

    result = _build(doc, dest, png=True, dpi=args.dpi, debug=args.debug)
    print(result.stdout.rstrip())
    # Always surface stderr: pagekit reports grid snapping and overflow there
    # on a *successful* build, and those warnings are the point of previewing.
    if result.stderr.strip():
        print(result.stderr.rstrip(), file=sys.stderr)
    if result.returncode != 0:
        return 1
    for shot in sorted(dest.glob("*.png")):
        print(shot)
    return 0


# ---------------------------------------------------------------- verify
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


def _walk(module, rect, depth=0):
    """Yield (depth, module, rect) for a module and any children it lays out."""
    yield depth, module, rect
    place = getattr(module, "_place", None)
    if callable(place):
        for placement in place(rect):
            yield from _walk(placement.module, placement.rect, depth + 1)


def cmd_grid(args) -> int:
    """Assert the core invariant: every *module placement* is on the 2.5mm grid.

    This drives the layout engine directly rather than parsing the SVG, because
    the invariant is about where the engine puts modules — not about every rect
    that ends up in the file. A module is free to draw sub-grid detail inside
    its own box (habit_grid divides 50mm into 7 columns of 7.1429mm, and that
    is correct). Parsing the SVG cannot tell those two cases apart.
    """
    from pagekit import spec as pk_spec
    from pagekit.layout import layout_stack
    from pagekit.modules import build as build_module
    from pagekit.render import Renderer

    sources = [Path(p) for p in args.svg] or sorted((ROOT / "templates").glob("*.yaml"))
    violations = 0
    checked = 0

    for source in sources:
        document = pk_spec.load(source)
        renderer = Renderer(document)
        for page_spec in document.pages:
            _, content = renderer.content_rect(page_spec)
            canvas, ctx = renderer.render_page(page_spec)
            children = [build_module(s, ctx) for s in page_spec.content]
            placements = layout_stack(children, content, ctx.default_gap, ctx.grid, ctx)

            offenders = []
            for placement in placements:
                for depth, module, rect in _walk(placement.module, placement.rect):
                    checked += 1
                    for label, value in (("x", rect.x), ("y", rect.y),
                                         ("w", rect.w), ("h", rect.h)):
                        if abs(value - round(value / GRID) * GRID) > 1e-6:
                            offenders.append((depth, module.name, label, value, rect))
                            break
            label = "%s / %s" % (source.stem, page_spec.name)
            print("%-34s %3d placements, %d off-grid" % (label, len(placements), len(offenders)))
            for depth, name, key, value, rect in offenders[:10]:
                print("    %s%s: %s=%.4f  %s" % ("  " * depth, name, key, value, rect))
            violations += len(offenders)

    print("\n%d placements checked; %s"
          % (checked, "all on the %.1fmm grid" % GRID if not violations
             else "%d off-grid" % violations))
    return 1 if violations else 0


def cmd_ink(args) -> int:
    """Report sub-grid geometry *inside* modules — informational, never fails.

    Useful when you want to know what a module draws internally (habit_grid's
    7.1429mm columns, icon placements), which `grid` deliberately ignores.
    """
    svgs = [Path(p) for p in args.svg] or sorted(OUT.glob("*.svg"))
    if not svgs:
        print("no SVGs — run `pagekit-dev build` first", file=sys.stderr)
        return 1
    for svg in svgs:
        rects = list(_rects(svg.read_text()))
        off = [r for r in rects[1:]
               if any(abs(v - round(v / GRID) * GRID) > 1e-6 for v in r)]
        print("%-42s %3d rects, %d sub-grid" % (svg.name, len(rects) - 1, len(off)))
        for x, y, w, h in off[:6]:
            print("    rect(%.3f, %.3f, %.3f, %.3f)" % (x, y, w, h))
    return 0


def cmd_geom(args) -> int:
    """Rendered object geometry in millimetres, via inkscape --query-all.

    Unlike `grid` (which parses the source SVG) this reports *ink* bounds,
    so it includes text and placed icons. It is the tool for checking a
    layout change against measured artwork.
    """
    if not shutil.which("inkscape"):
        print("inkscape not found — see `pagekit-dev doctor`", file=sys.stderr)
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


def cmd_fonts(args) -> int:
    """Prove the PDF embeds Montserrat rather than a silent substitute.

    Inkscape does not warn when a font is missing; it substitutes (Verdana on
    this machine) and exits 0. The page still looks plausible, but pagekit's
    baseline maths assumes Montserrat's cap-height ratio, so every label
    shifts. This is the only cheap way to catch it.
    """
    pdfs = [Path(p) for p in args.pdf] or sorted(OUT.glob("*.pdf"))
    if not pdfs:
        print("no PDFs — run `pagekit-dev build --pdf` first", file=sys.stderr)
        return 1

    failed = 0
    for pdf in pdfs:
        data = pdf.read_bytes()
        fonts = sorted({f.decode() for f in re.findall(rb"/BaseFont\s*/([A-Za-z0-9+#-]+)", data)})
        stripped = {f.split("+")[-1] for f in fonts}
        good = all(f.startswith(FONT) for f in stripped) and stripped
        print("%-28s %s" % (pdf.name, ", ".join(fonts) or "(no embedded fonts)"))
        if not good:
            bad("expected only %s subsets — got %s" % (FONT, sorted(stripped)))
            failed += 1
    print("\n%s" % ("fonts ok" if not failed else "%d PDF(s) with substituted fonts" % failed))
    return 1 if failed else 0


def cmd_pages(args) -> int:
    """Page count and MediaBox of a PDF, in mm — checks the physical size."""
    pdf = Path(args.pdf) if Path(args.pdf).is_absolute() else ROOT / args.pdf
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


def cmd_test(args) -> int:
    """Run the test suite (replaces `make test`)."""
    result = sh([_python(), str(ROOT / "tests" / "test_pagekit.py")], cwd=ROOT)
    print(result.stdout.rstrip() or result.stderr.rstrip())
    return result.returncode


def cmd_clean(args) -> int:
    """Delete the output directory (replaces `make clean`)."""
    if OUT.exists():
        shutil.rmtree(OUT)
        print("removed %s" % OUT)
    else:
        print("nothing to remove (%s does not exist)" % OUT)
    return 0


# ---------------------------------------------------------------- smoke
def cmd_smoke(args) -> int:
    """Everything, end to end. Non-zero exit on any failure."""
    steps = []

    print("=== doctor ===")
    steps.append(("doctor", cmd_doctor(argparse.Namespace())))

    print("\n=== build (svg + pdf + png) ===")
    ns = argparse.Namespace(template=None, pdf=True, png=True, dpi=110, debug=False)
    steps.append(("build", cmd_build(ns)))

    print("\n=== tests ===")
    result = sh([_python(), str(ROOT / "tests" / "test_pagekit.py")], cwd=ROOT)
    print(result.stdout.rstrip().splitlines()[-1] if result.stdout.strip() else result.stderr)
    steps.append(("tests", result.returncode))

    print("\n=== grid invariant ===")
    steps.append(("grid", cmd_grid(argparse.Namespace(svg=[], verbose=False))))

    print("\n=== embedded fonts ===")
    steps.append(("fonts", cmd_fonts(argparse.Namespace(pdf=[]))))

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
        prog="pagekit-dev", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("doctor", help="check prerequisites (tools, venv, font)")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("build", help="render templates to SVG (optionally PDF/PNG)")
    p.add_argument("template", nargs="*", help="default: every templates/*.yaml")
    p.add_argument("--pdf", action="store_true")
    p.add_argument("--png", action="store_true")
    p.add_argument("--dpi", type=int, default=150)
    p.add_argument("--debug", action="store_true", help="overlay grid + margin box")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("watch", help="rebuild on every change until interrupted")
    p.add_argument("template", nargs="*", help="default: every templates/*.yaml")
    p.add_argument("--no-pdf", action="store_true", help="SVG only — much faster")
    p.add_argument("--png", action="store_true", help="also rasterise a preview PNG")
    p.add_argument("--dpi", type=int, default=150)
    p.add_argument("--debug", action="store_true", help="overlay grid + margin box")
    p.add_argument("--interval", type=float, default=0.4, help="poll seconds (default 0.4)")
    p.set_defaults(func=cmd_watch)

    p = sub.add_parser("shot", help="render a template and print PNG paths to Read()")
    p.add_argument("template")
    p.add_argument("--dpi", type=int, default=150)
    p.add_argument("--page", type=int, help="only this page number")
    p.add_argument("--debug", action="store_true")
    p.set_defaults(func=cmd_shot)

    p = sub.add_parser("preview", help="render ad-hoc module YAML from stdin")
    p.add_argument("--dpi", type=int, default=150)
    p.add_argument("--debug", action="store_true")
    p.add_argument("--modules", action="append", default=[],
                   help="path to a custom module file to load (repeatable)")
    p.set_defaults(func=cmd_preview)

    p = sub.add_parser("grid", help="assert every module placement is on the 2.5mm grid")
    p.add_argument("svg", nargs="*", metavar="YAML", help="default: every templates/*.yaml")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(func=cmd_grid)

    p = sub.add_parser("ink", help="report sub-grid geometry drawn inside modules")
    p.add_argument("svg", nargs="*", help="default: out/*.svg")
    p.set_defaults(func=cmd_ink)

    p = sub.add_parser("geom", help="rendered ink geometry in mm (inkscape)")
    p.add_argument("svg")
    p.add_argument("--min-size", type=float, default=3.0, help="hide objects smaller than this")
    p.set_defaults(func=cmd_geom)

    p = sub.add_parser("fonts", help="assert PDFs embed Montserrat, not a substitute")
    p.add_argument("pdf", nargs="*", help="default: out/*.pdf")
    p.set_defaults(func=cmd_fonts)

    p = sub.add_parser("pages", help="page count + MediaBox in mm")
    p.add_argument("pdf")
    p.set_defaults(func=cmd_pages)

    p = sub.add_parser("test", help="run the test suite")
    p.set_defaults(func=cmd_test)

    p = sub.add_parser("clean", help="delete out/")
    p.set_defaults(func=cmd_clean)

    p = sub.add_parser("smoke", help="run everything, exit non-zero on failure")
    p.set_defaults(func=cmd_smoke)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
