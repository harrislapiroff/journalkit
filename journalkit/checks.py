"""Checks that prove the output is right, beyond what the eye can see.

Two things, behind ``journalkit check``:

* ``grid`` — every *module placement* lands on the document's module grid.
  Drives the layout engine rather than parsing SVG, because the invariant is
  about where the engine puts modules, not about every rect in the file; a
  module is free to draw sub-grid detail inside its own box.
* ``fonts`` — the PDFs carry text the way the theme asked. With outlined
  text (the default) that means no fonts embedded at all; with
  ``font.outline: false`` it means only the theme's family. Either way a
  stray substitution shows up as an unexpected ``/BaseFont``.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import spec as jk_spec
from .layout import layout_stack
from .modules import build as build_module
from .render import Renderer


def _phase(value: float, grid: float) -> float:
    """How far ``value`` sits from the nearest grid line, signed."""
    return value - round(value / grid) * grid


def _walk(module, rect, depth=0):
    """Yield (depth, module, rect) for a module and any children it lays out."""
    yield depth, module, rect
    place = getattr(module, "_place", None)
    if callable(place):
        for placement in place(rect):
            yield from _walk(placement.module, placement.rect, depth + 1)


def check_grid(sources: list[Path], out=print) -> int:
    """Assert every module placement is on its document's grid.

    Two different things can be off the grid, and they are not equally bad:

    * the *content rect* — page geometry the template author chose. A 105mm
      page cannot put both mirrored margins on a 2mm grid, so one side sits
      1mm off the lattice by design. Reported per page as a note, never
      fatal.
    * a *module placement*, relative to that content rect. That is the
      layout engine failing to snap, and it is fatal.

    Returns the number of off-grid placements.
    """
    violations = 0
    checked = 0
    skewed = 0
    grids: set[float] = set()

    for source in sources:
        document = jk_spec.load(source)
        grid = document.grid
        grids.add(grid)
        renderer = Renderer(document)
        for page_spec in document.pages:
            _, content = renderer.content_rect(page_spec)
            canvas, ctx = renderer.render_page(page_spec)
            children = [build_module(s, ctx) for s in page_spec.content]
            placements = layout_stack(children, content, ctx.default_gap, ctx.grid, ctx)

            offsets = {"x": _phase(content.x, grid), "y": _phase(content.y, grid),
                       "w": _phase(content.w, grid), "h": _phase(content.h, grid)}
            askew = {k: v for k, v in offsets.items() if abs(v) > 1e-6}

            offenders = []
            for placement in placements:
                for depth, module, rect in _walk(placement.module, placement.rect):
                    checked += 1
                    for label, value in (("x", rect.x), ("y", rect.y),
                                         ("w", rect.w), ("h", rect.h)):
                        if abs(_phase(value, grid) - offsets[label]) > 1e-6:
                            offenders.append((depth, module.name, label, value, rect))
                            break
            label = "%s / %s" % (source.stem, page_spec.name)
            out("%-30s %4.1fmm %3d placements, %d off-grid"
                % (label, grid, len(placements), len(offenders)))
            if askew:
                skewed += 1
                out("    note: content rect is off the lattice by %s — placements"
                    % ", ".join("%s%+.2fmm" % (k, v) for k, v in sorted(askew.items())))
                out("          checked relative to it, not to the page")
            for depth, name, key, value, rect in offenders[:10]:
                out("    %s%s: %s=%.4f  %s" % ("  " * depth, name, key, value, rect))
            violations += len(offenders)

    on = "/".join("%.1f" % g for g in sorted(grids))
    summary = "all on the %smm grid" % on if not violations else "%d off-grid" % violations
    if skewed:
        summary += "; %d page(s) on an off-lattice content rect" % skewed
    out("\n%d placements checked; %s" % (checked, summary))
    return violations


_BASEFONT = re.compile(rb"/BaseFont\s*/([A-Za-z0-9+#-]+)")


def embedded_fonts(pdf: Path) -> list[str]:
    """Every ``/BaseFont`` name in the PDF, subset prefixes stripped."""
    names = {f.decode() for f in _BASEFONT.findall(pdf.read_bytes())}
    return sorted({n.split("+")[-1] for n in names})


def check_fonts(pairs: list[tuple[Path, str, bool]], out=print) -> int:
    """Assert each PDF carries the text it was designed with.

    ``pairs`` is ``(pdf_path, family, outlined)``. A document rendered with
    outlined text (the default) must embed **no** fonts at all: any font in
    the PDF means an SVG ``<text>`` slipped through and Inkscape set it in
    whatever it had. A document rendered with ``font.outline: false`` must
    embed only its own family. Returns the number of PDFs that fail.
    """
    failed = 0
    for pdf, family, outlined in pairs:
        if not pdf.exists():
            out("%-28s (not built — run `journalkit build --pdf`)" % pdf.name)
            continue
        fonts = embedded_fonts(pdf)
        if outlined:
            good = not fonts
            shown = "text outlined, no fonts embedded" if not fonts else ", ".join(fonts)
        else:
            wanted = family.replace(" ", "")
            good = bool(fonts) and all(f.startswith(wanted) for f in fonts)
            shown = ", ".join(fonts) or "(no embedded fonts)"
        out("%-28s %s" % (pdf.name, shown))
        if not good:
            if outlined:
                out("  FAIL text should be outlined but %s was embedded" % ", ".join(fonts))
            else:
                out("  FAIL expected only %s — got %s" % (family, fonts))
            failed += 1
    out("\n%s" % ("fonts ok" if not failed else "%d PDF(s) with substituted fonts" % failed))
    return failed
