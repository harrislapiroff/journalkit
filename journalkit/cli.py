"""The ``journalkit`` command.

Every subcommand works on a *project directory* — a folder holding
``templates/*.yaml`` and optionally ``modules/*.py`` and ``icons/*.svg`` (see
:mod:`journalkit.project`). SOURCE arguments may be project directories or
single YAML files; with none, the working directory is the project.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import __version__, spec
from .modules import REGISTRY
from .project import Project, sources_to_documents
from .render import Renderer

SCAFFOLD = Path(__file__).resolve().parent / "scaffold"


# ---------------------------------------------------------------- export
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
        raise RuntimeError("inkscape not found on PATH; install it or drop --pdf")

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


# ---------------------------------------------------------------- build
def build_document(source: Path, out_dir: Path, project: Project | None = None, *,
                   pdf=False, png=False, dpi=300, debug=False, background=True,
                   log=print) -> list[str]:
    """Render one document into ``out_dir``. Returns its warnings."""
    document = spec.load(source, project)
    renderer = Renderer(document, debug=debug, background="#ffffff" if background else None)
    pages = renderer.render_all()
    if not pages:
        raise ValueError("no pages defined in %s" % source)

    out_dir.mkdir(parents=True, exist_ok=True)
    svg_paths = []
    for name, svg in pages:
        path = out_dir / ("%s-%s.svg" % (document.name, name))
        path.write_text(svg)
        svg_paths.append(path)
        log("wrote %s" % path)

    if png:
        for path in svg_paths:
            target = path.with_suffix(".png")
            svg_to_png(path, target, dpi)
            log("wrote %s" % target)

    if pdf:
        target = out_dir / ("%s.pdf" % document.name)
        svg_to_pdf(svg_paths, target)
        log("wrote %s" % target)

    return list(renderer.warnings)


def _pairs(args):
    """(project, template) pairs from the SOURCE arguments, honouring --project."""
    pairs = sources_to_documents(args.source)
    override = getattr(args, "project", None)
    if override:
        project = Project(Path(override).expanduser().resolve())
        pairs = [(project, template) for _, template in pairs]
    return pairs


def cmd_build(args) -> int:
    pairs = _pairs(args)
    warned = failed = False
    for project, template in pairs:
        out_dir = Path(args.out) if args.out else project.out_dir
        try:
            warnings = build_document(template, out_dir, project, pdf=args.pdf,
                                      png=args.png, dpi=args.dpi, debug=args.debug,
                                      background=not args.no_background)
        except (ValueError, FileNotFoundError, RuntimeError) as exc:
            print("error: %s: %s" % (template.name, exc), file=sys.stderr)
            failed = True
            continue
        for message in warnings:
            print("warning: %s: %s" % (template.stem, message), file=sys.stderr)
        warned = warned or bool(warnings)
    if failed:
        return 1
    if warned and args.strict:
        return 2
    return 0


# ---------------------------------------------------------------- watch / preview
def cmd_watch(args) -> int:
    from .watch import watch

    return watch(_pairs(args), Path(args.out) if args.out else None, pdf=args.pdf,
                 png=args.png, dpi=args.dpi, debug=args.debug, interval=args.interval)


def cmd_preview(args) -> int:
    from .watch import preview

    project = Project.locate(args.project)
    return preview(project, sys.stdin.read(), modules=args.modules, dpi=args.dpi,
                   debug=args.debug)


# ---------------------------------------------------------------- check
def cmd_check(args) -> int:
    from .checks import check_fonts, check_grid

    pairs = _pairs(args)
    print("== module grid ==")
    violations = check_grid([template for _, template in pairs])

    print("\n== embedded fonts ==")
    fonts = []
    for project, template in pairs:
        document = spec.load(template, project)
        out_dir = Path(args.out) if args.out else project.out_dir
        fonts.append((out_dir / ("%s.pdf" % document.name), document.theme.get("font.family")))
    substituted = check_fonts(fonts)

    return 1 if violations or substituted else 0


# ---------------------------------------------------------------- modules
def cmd_modules(args) -> int:
    project = Project.locate(args.source)
    project.load_modules()
    # Anything registered from the project's files is local; note where from.
    local = {}
    for name, cls in REGISTRY.items():
        module_file = sys.modules.get(cls.__module__)
        file = getattr(module_file, "__file__", None)
        if file and Path(file).resolve().parent == project.modules_dir.resolve():
            local[name] = Path(file).name

    for name in sorted(REGISTRY):
        cls = REGISTRY[name]
        doc = (cls.__doc__ or "").strip().splitlines()
        origin = "  [%s]" % local[name] if name in local else ""
        print("\n%s — %s%s" % (name, doc[0] if doc else "", origin))
        for line in doc[1:]:
            if line.strip():
                print("    %s" % line.strip())
        for key, description in getattr(cls, "params", {}).items():
            print("      %-14s %s" % (key, description))
    print("\nEvery module also accepts: height, width, gap, flex, valign, id, theme")
    if project.modules_dir.is_dir() and not local:
        print("(%s holds no module files)" % project.modules_dir)
    return 0


# ---------------------------------------------------------------- doctor
def _font_installed(family: str) -> bool:
    from .fontmetrics import find_font

    if find_font(family) is not None:
        return True
    fc = shutil.which("fc-list")
    if fc:
        listed = subprocess.run([fc, "-f", "%{family}\n"], capture_output=True, text=True).stdout
        return family.lower() in listed.lower()
    return False


def cmd_doctor(args) -> int:
    """Check the external things a build needs: tools and fonts."""
    project = Project.locate(args.source)
    problems = []

    def ok(msg):
        print("  ok   %s" % msg)

    def bad(msg):
        print("  FAIL %s" % msg)

    print("tools (only needed for --pdf and --png):")
    for tool, why, install in [
        ("inkscape", "SVG→PDF/PNG with font embedding", "brew install --cask inkscape"),
        ("gs", "merging per-page PDFs into one document", "brew install ghostscript"),
    ]:
        path = shutil.which(tool)
        if path:
            ok("%-9s %s" % (tool, path))
        else:
            bad("%-9s missing — %s (needed for %s)" % (tool, install, why))
            problems.append(tool)

    print("fonts:")
    for family in sorted(project.font_families()):
        if _font_installed(family):
            ok("%s installed" % family)
        else:
            # The font is the silent killer: Inkscape substitutes without warning.
            bad("%s NOT installed — Inkscape will silently substitute another font "
                "and every baseline will shift" % family)
            problems.append("font:%s" % family)

    print("project:")
    if project.is_project():
        ok("%s (%d template(s), %d module file(s))"
           % (project.root, len(project.templates()), len(project.module_files())))
    else:
        bad("%s has no templates/ — run `journalkit init` to start one" % project.root)
        problems.append("project")

    print("\n%s" % ("everything is in place" if not problems
                    else "MISSING: %s" % ", ".join(problems)))
    return 1 if problems else 0


# ---------------------------------------------------------------- init
def cmd_init(args, log=print) -> int:
    """Copy the starter project into DIR without overwriting anything."""
    target = Path(args.directory).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    written = []
    skipped = []
    files = sorted(p for p in SCAFFOLD.rglob("*")
                   if p.is_file() and "__pycache__" not in p.parts)
    for source in files:
        relative = source.relative_to(SCAFFOLD)
        dest = target / relative
        if dest.exists():
            skipped.append(relative)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        written.append(relative)
    for path in written:
        log("wrote %s" % (target / path))
    for path in skipped:
        log("kept  %s (already exists)" % (target / path))
    if written:
        where = "" if target == Path.cwd().resolve() else "cd %s && " % args.directory
        log("\nnext: %sjournalkit build --png    # then open out/" % where)
    return 0


# ---------------------------------------------------------------- main
def _add_sources(parser, help="a project directory or a YAML document (default: .)"):
    parser.add_argument("source", nargs="*", metavar="SOURCE", help=help)
    parser.add_argument("--project", metavar="DIR",
                        help="treat DIR as the project (modules/, icons/, out/) "
                             "instead of locating it from SOURCE")


def _add_render_options(parser, dpi_default):
    parser.add_argument("-o", "--out", metavar="DIR",
                        help="output directory (default: <project>/out)")
    parser.add_argument("--pdf", action="store_true", help="also write one multi-page PDF")
    parser.add_argument("--png", action="store_true", help="also write a PNG per page")
    parser.add_argument("--dpi", type=int, default=dpi_default,
                        help="PNG resolution (default %d)" % dpi_default)
    parser.add_argument("--debug", action="store_true",
                        help="overlay the module grid and margin box")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="journalkit",
        description="Render YAML page templates into print-ready SVG and PDF.")
    parser.add_argument("--version", action="version", version="journalkit %s" % __version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("build", help="render templates to SVG (and PDF/PNG)")
    _add_sources(p)
    _add_render_options(p, dpi_default=300)
    p.add_argument("--no-background", action="store_true", help="transparent page background")
    p.add_argument("--strict", action="store_true", help="exit non-zero if anything warned")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("watch", help="rebuild on every change until interrupted")
    _add_sources(p)
    _add_render_options(p, dpi_default=150)
    p.add_argument("--interval", type=float, default=0.4, help="poll seconds (default 0.4)")
    p.set_defaults(func=cmd_watch)

    p = sub.add_parser("preview", help="render ad-hoc module YAML from stdin to a PNG")
    p.add_argument("--project", metavar="DIR", default=None,
                   help="project whose modules/ and icons/ to use (default: .)")
    p.add_argument("--modules", action="append", default=[], metavar="FILE",
                   help="extra module file to load (repeatable)")
    p.add_argument("--dpi", type=int, default=150)
    p.add_argument("--debug", action="store_true", help="overlay the module grid and margin box")
    p.set_defaults(func=cmd_preview)

    p = sub.add_parser("check", help="assert placements are on the grid and PDFs embed the font")
    _add_sources(p)
    p.add_argument("-o", "--out", metavar="DIR", help="where the PDFs were built (default: <project>/out)")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("modules", help="list module types and their parameters")
    p.add_argument("source", nargs="?", metavar="DIR", help="project directory (default: .)")
    p.set_defaults(func=cmd_modules)

    p = sub.add_parser("doctor", help="check tools and fonts")
    p.add_argument("source", nargs="?", metavar="DIR", help="project directory (default: .)")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("init", help="start a project directory from the built-in scaffold")
    p.add_argument("directory", nargs="?", default=".", help="where to create it (default: .)")
    p.set_defaults(func=cmd_init)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
