"""Command line: ``python -m pagekit build templates/daily.yaml --pdf``."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import spec
from .modules import REGISTRY
from .render import Renderer


def _tool(name: str) -> str | None:
    return shutil.which(name)


def _run(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("%s failed:\n%s%s" % (command[0], result.stdout, result.stderr))


def svg_to_pdf(svg_paths: list[Path], out_pdf: Path) -> None:
    """Convert with Inkscape (fonts embedded), then concatenate with Ghostscript."""
    inkscape = _tool("inkscape")
    if not inkscape:
        raise RuntimeError("inkscape not found on PATH; install it or use --svg-only")

    with tempfile.TemporaryDirectory() as tmp:
        parts = []
        for index, svg in enumerate(svg_paths):
            part = Path(tmp) / ("%03d.pdf" % index)
            _run([inkscape, "--export-type=pdf", "--export-area-page",
                  "--export-filename=%s" % part, str(svg)])
            parts.append(part)

        if len(parts) == 1:
            shutil.copyfile(parts[0], out_pdf)
            return
        gs = _tool("gs")
        if not gs:
            raise RuntimeError("ghostscript (gs) not found; needed to merge %d pages" % len(parts))
        _run([gs, "-dQUIET", "-dNOPAUSE", "-dBATCH", "-sDEVICE=pdfwrite",
              "-dPDFSETTINGS=/prepress", "-dAutoRotatePages=/None",
              "-sOutputFile=%s" % out_pdf] + [str(p) for p in parts])


def svg_to_png(svg_path: Path, out_png: Path, dpi: int) -> None:
    inkscape = _tool("inkscape")
    if not inkscape:
        raise RuntimeError("inkscape not found on PATH; needed for --png")
    _run([inkscape, "--export-type=png", "--export-area-page", "--export-dpi=%d" % dpi,
          "--export-filename=%s" % out_png, str(svg_path)])


def cmd_build(args) -> int:
    document = spec.load(args.source)
    renderer = Renderer(document, debug=args.debug,
                        background=None if args.no_background else "#ffffff")
    pages = renderer.render_all()
    if not pages:
        print("no pages defined in %s" % args.source, file=sys.stderr)
        return 1

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    svg_paths = []
    for name, svg in pages:
        path = out_dir / ("%s-%s.svg" % (document.name, name))
        path.write_text(svg)
        svg_paths.append(path)
        print("wrote %s" % path)

    if args.png:
        for path in svg_paths:
            png = path.with_suffix(".png")
            svg_to_png(path, png, args.dpi)
            print("wrote %s" % png)

    if args.pdf:
        pdf = out_dir / ("%s.pdf" % document.name)
        svg_to_pdf(svg_paths, pdf)
        print("wrote %s" % pdf)

    for message in renderer.warnings:
        print("warning: %s" % message, file=sys.stderr)
    if renderer.warnings and args.strict:
        return 2
    return 0


def cmd_modules(args) -> int:
    for name in sorted(REGISTRY):
        cls = REGISTRY[name]
        doc = (cls.__doc__ or "").strip().splitlines()
        print("\n%s — %s" % (name, doc[0] if doc else ""))
        for line in doc[1:]:
            if line.strip():
                print("    %s" % line.strip())
        for key, description in getattr(cls, "params", {}).items():
            print("      %-14s %s" % (key, description))
    print("\nEvery module also accepts: height, width, gap, flex, valign, id, theme")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="pagekit", description="Render notebook page templates.")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="render a YAML document to SVG (and PDF/PNG)")
    build.add_argument("source", help="path to the YAML document")
    build.add_argument("-o", "--out", default="out", help="output directory (default: out)")
    build.add_argument("--pdf", action="store_true", help="also write a single multi-page PDF")
    build.add_argument("--png", action="store_true", help="also write a PNG per page (preview)")
    build.add_argument("--dpi", type=int, default=300, help="PNG resolution (default 300)")
    build.add_argument("--debug", action="store_true", help="overlay the module grid and margin box")
    build.add_argument("--no-background", action="store_true", help="transparent page background")
    build.add_argument("--strict", action="store_true", help="exit non-zero if anything warned")
    build.set_defaults(func=cmd_build)

    modules = sub.add_parser("modules", help="list available module types and their parameters")
    modules.set_defaults(func=cmd_modules)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
