"""Rebuild-on-change and stdin preview, behind ``journalkit watch``/``preview``.

Both shell out to ``python -m journalkit build`` in a fresh process rather
than calling the renderer in-process: a project's ``modules/*.py`` are
imported with ``@register`` decorators that refuse to run twice, so the only
way to pick up an edit to one is to start over.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from .project import Project

SETTLE = 0.3    # quiet period before building, so one save is one build

#: Where the library itself lives. Watched too, so an editable checkout
#: rebuilds when the renderer changes, not only when a template does.
PACKAGE_DIR = Path(__file__).resolve().parent


def build_command(template: Path, out_dir: Path, pdf=False, png=False, dpi=150,
                  debug=False, project: Project | None = None) -> list[str]:
    cmd = [sys.executable, "-m", "journalkit", "build", str(template), "-o", str(out_dir)]
    if project is not None:
        cmd += ["--project", str(project.root)]
    if pdf:
        cmd.append("--pdf")
    if png:
        cmd += ["--png", "--dpi", str(dpi)]
    if debug:
        cmd.append("--debug")
    return cmd


def run_build(template: Path, out_dir: Path, **options) -> subprocess.CompletedProcess:
    return subprocess.run(build_command(template, out_dir, **options),
                          capture_output=True, text=True)


def _say(text: str = "") -> None:
    # Flush every line: the watcher is long-lived and its stdout is often a
    # pipe, where print would otherwise block-buffer until exit.
    print(text, flush=True)


def _watched_files(projects: set[Project], templates: list[Path]) -> dict[Path, float]:
    """{path: mtime} for every input a build reads, re-globbed each time so
    new files appear."""
    paths: set[Path] = set(templates)
    for project in projects:
        for directory, pattern in ((project.templates_dir, "*.y*ml"),
                                   (project.modules_dir, "*.py"),
                                   (project.icons_dir, "*.svg")):
            if directory.is_dir():
                paths.update(directory.glob(pattern))
    paths.update(PACKAGE_DIR.rglob("*.py"))
    paths.update(PACKAGE_DIR.glob("icons/*.svg"))
    found = {}
    for path in paths:
        try:
            found[path] = path.stat().st_mtime
        except OSError:
            pass  # deleted mid-scan; the next poll reports it as a change
    return found


def watch(pairs: list[tuple[Project, Path]], out_dir: Path | None, *, pdf: bool,
          png: bool, dpi: int, debug: bool, interval: float) -> int:
    """Rebuild whenever an input file changes, until interrupted.

    Polls mtimes rather than using an OS watch API: the file count is in the
    dozens, and polling keeps the tool on the standard library.

    Editing a template rebuilds only that template; touching a module, an
    icon or the library rebuilds everything, because any of those can change
    every page.
    """
    projects = {project for project, _ in pairs}
    templates = [template for _, template in pairs]
    what = "svg" + (" + pdf" if pdf else "") + (" + png" if png else "")
    roots = sorted({str(p.root) for p in projects})
    _say("watching %s for changes → %s" % (", ".join(roots), what))
    _say("ctrl-c to stop\n")

    def destination(project: Project) -> Path:
        return out_dir if out_dir is not None else project.out_dir

    def build(selected):
        for project, template in selected:
            started = time.monotonic()
            result = run_build(template, destination(project), pdf=pdf, png=png,
                               dpi=dpi, debug=debug)
            written = sum(line.startswith("wrote") for line in result.stdout.splitlines())
            _say("  %-18s %-7s %d file(s)  %4.1fs"
                 % (template.name, "ok" if result.returncode == 0 else "FAILED",
                    written, time.monotonic() - started))
            # Warnings (off-grid snapping, overflow) arrive on stderr with
            # exit code 0 — surfacing them is most of the point of watching.
            for line in result.stderr.splitlines():
                if line.strip():
                    _say("      %s" % line)

    seen = _watched_files(projects, templates)
    _say("[%s] initial build" % time.strftime("%H:%M:%S"))
    build(pairs)

    try:
        while True:
            time.sleep(interval)
            now = _watched_files(projects, templates)
            changed = sorted(p for p in set(seen) | set(now) if seen.get(p) != now.get(p))
            if not changed:
                continue

            # Let a burst of writes settle, so saving several files at once —
            # or an editor's write-temp-then-rename — is a single rebuild.
            while True:
                time.sleep(SETTLE)
                settled = _watched_files(projects, templates)
                if settled == now:
                    break
                changed = sorted(set(changed) | {p for p in set(now) | set(settled)
                                                 if now.get(p) != settled.get(p)})
                now = settled
            seen = now

            # Templates that appeared since we started join the set.
            current = []
            for project in projects:
                current += [(project, t) for t in project.templates()]
            for pair in pairs:
                if pair not in current and pair[1].exists():
                    current.append(pair)
            pairs = current

            touched = [(p, t) for p, t in pairs if t in changed]
            rebuild = touched if len(touched) == len(changed) else pairs

            _say("\n[%s] %s" % (time.strftime("%H:%M:%S"),
                                ", ".join(p.name for p in changed[:4])
                                + (" +%d more" % (len(changed) - 4) if len(changed) > 4 else "")))
            build(rebuild)
    except KeyboardInterrupt:
        _say("\nstopped")
        return 0


PREVIEW_DOC = """document: preview
page:
  size: [105, 170]
  margins: {top: 2.5, bottom: 7.5, inner: 25, outer: 5}
grid:
  module: 2.5
  dots: {spacing: 5, origin: [0, 2.5], radius: 0.125}
defaults: {gap: 2.5}
templates:
  preview:
    side: right
    content:
%s
pages: [{template: preview}]
"""


def preview(project: Project, snippet: str, *, modules: list[str], dpi: int,
            debug: bool, png: bool = True) -> int:
    """Render an ad-hoc ``content:`` list inside a throwaway document.

    The document is written into ``<project>/out/preview/`` and built with
    ``--project`` pointing back at the project, so its ``modules/`` and
    ``icons/`` are available to the snippet.
    """
    snippet = snippet.strip()
    if not snippet:
        print("nothing on stdin", file=sys.stderr)
        return 1
    indented = "\n".join("      " + line for line in snippet.splitlines())

    dest = project.out_dir / "preview"
    dest.mkdir(parents=True, exist_ok=True)
    doc = dest / "preview.yaml"
    header = ""
    if modules:
        paths = [Path(m).resolve() for m in modules]
        header = "modules:\n" + "".join("  - %s\n" % p for p in paths)
    doc.write_text(header + PREVIEW_DOC % indented)

    result = run_build(doc, dest, png=png, dpi=dpi, debug=debug, project=project)
    if result.stdout.strip():
        print(result.stdout.rstrip())
    # Always surface stderr: grid snapping and overflow are reported there on
    # a *successful* build, and those warnings are the point of previewing.
    if result.stderr.strip():
        print(result.stderr.rstrip(), file=sys.stderr)
    return 0 if result.returncode == 0 else 1
