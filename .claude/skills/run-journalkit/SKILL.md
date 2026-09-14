---
name: run-journalkit
description: Build, run, and drive journalkit — the journal page-template renderer that turns YAML into printable SVG/PDF. Use when asked to run journalkit or the notebook generator, render or preview a template, screenshot a page, add or test a module type, check the module grid, or verify PDF output.
---

journalkit renders YAML page definitions into print-ready SVG and PDF. It has
no GUI and no server — the "running app" is a set of print artifacts — so
driving it means rendering, *looking* at the result, and asserting the
invariants that make it correct.

Two entry points, and the split matters:

- **`.venv/bin/journalkit`** — the product (`journalkit/cli.py`). Runs on a
  *project directory*; in this repo that is `examples/journal`.
- **`.venv/bin/python tools/dev.py`** — repo-only tasks: tests, smoke, and
  geometry measurement. Never installed for users.

All paths below are relative to the project root (the directory holding
`pyproject.toml`). Verified on macOS / arm64 / Python 3.12 / Inkscape 1.3.2.

## Prerequisites

Two external tools. SVG output needs neither; PDF and PNG need both.

```bash
brew install --cask inkscape      # SVG -> PDF/PNG, embeds fonts
brew install ghostscript          # merges per-page PDFs into one document
```

The **Montserrat** font must be installed system-wide (`~/Library/Fonts/`)
for the example project. This is not optional — see Gotchas.

`tools/dev.py doctor` is stdlib-only up to the venv check, so it runs with
**system python3** on a clean checkout and tells you what to do next:

```bash
python3 tools/dev.py doctor
```

## Setup

There is no Makefile — the entry point lives in `pyproject.toml`.

```bash
poetry install
```

Or without Poetry:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

Either installs PyYAML and the `journalkit` console script into `.venv/bin/`.
The editable install is what makes it cwd-independent.

## Run (agent path)

### Start here

```bash
.venv/bin/python tools/dev.py smoke
```

```
==============================================
doctor   ok
build    ok
tests    ok
check    ok
pages    ok

SMOKE PASSED
```

### The product CLI

| command | what it does |
|---|---|
| `journalkit build [SRC…] [-o DIR] [--pdf] [--png] [--dpi N] [--debug] [--strict]` | render; a directory builds every `templates/*.yaml`, default is `.` |
| `journalkit watch [SRC…] [--pdf] [--png] [--debug]` | rebuild on every change; runs until interrupted |
| `journalkit preview [--project DIR] [--modules F] [--debug]` | render ad-hoc module YAML **from stdin** to a PNG |
| `journalkit check [SRC…]` | assert every placement is on the document's grid, and PDFs embed the theme's font |
| `journalkit modules [DIR]` | module types + parameters, project-local ones marked with their file |
| `journalkit doctor [DIR]` | inkscape, ghostscript, and the fonts the project's templates use |
| `journalkit init [DIR]` | scaffold a new project (templates/daily.yaml, modules/stamp.py, README) |

Output lands in `<project>/out/` — `examples/journal/out/` for the example —
unless `-o` says otherwise. `--project DIR` overrides where `modules/` and
`icons/` are looked up, which is how `preview` gives a snippet the project's
custom types.

### The repo harness

| command | what it does |
|---|---|
| `tools/dev.py doctor` | venv + console script, then `journalkit doctor` on the example |
| `tools/dev.py test` | the test suite |
| `tools/dev.py smoke` | **everything end to end** on `examples/journal` |
| `tools/dev.py clean` | delete `examples/journal/out` and `dist/` |
| `tools/dev.py geom <svg> [--min-size N]` | rendered ink geometry in mm, via Inkscape |
| `tools/dev.py ink [svg…] [--grid N]` | sub-grid geometry drawn *inside* modules (informational) |
| `tools/dev.py pages <pdf>` | page count + MediaBox in mm |

### Look at a page

`build --png` prints the PNG paths; open them with `Read()`.

```bash
.venv/bin/journalkit build examples/journal/templates/daily.yaml --png --dpi 130
# → .../examples/journal/out/daily-01-daily-front.png
```

Add `--debug` to overlay the module grid and the margin box — the fastest way to
see *why* something sits where it does.

### Iterate on a module (the main dev loop)

`preview` takes just the `content:` entries on stdin and wraps them in a
throwaway 2.5 mm-grid document, so you never write a template file to try
something:

```bash
cat <<'YAML' | .venv/bin/journalkit preview --project examples/journal
- {type: heading, text: PREVIEW, icon: sunrise}
- {type: fields, columns: [ALPHA, BETA, GAMMA]}
- {type: rating, label: SCALE, icon: mood, count: 5}
- {type: checklist, rows: 3}
- {type: habit_grid, headers: [M,T,W,T,F,S,S], habits: [MOVE, READ]}
- {type: box, label: DOTS, height: fill, dots: true}
YAML
# → .../examples/journal/out/preview/preview-01-preview.png
```

Every `.py` in the project's `modules/` is loaded automatically; `--modules
FILE` adds one from elsewhere.

### Keep the artifacts fresh while editing

`watch` is the one long-running command. Run it **in the background** and read
its output; never in the foreground, where it will block the session forever.

```bash
.venv/bin/journalkit watch examples/journal            # SVG only while iterating
.venv/bin/journalkit watch examples/journal --pdf      # the real document
```

```
watching /…/examples/journal for changes → svg
ctrl-c to stop

[18:17:35] initial build
  daily.yaml         ok      2 file(s)   0.1s
  weekly.yaml        ok      2 file(s)   0.1s

[18:17:41] daily.yaml
  daily.yaml         ok      2 file(s)   0.1s
      warning: daily: daily-front: box: height 25.000mm is off the 2.000mm grid, snapped to 26.000mm
```

It watches the project's `templates/`, `modules/`, `icons/` **and** the
installed `journalkit/` package (so a library edit in this checkout rebuilds
too). A template edit rebuilds that template; anything else rebuilds all of
them. Warnings appear indented under the file that caused them, and a build
failure (bad YAML, say) is printed without stopping the watcher.

For a one-shot check prefer `build` — `watch` is for a human editing YAML.

### Verify a layout change numerically

Don't eyeball layout regressions. `check` proves the core invariant by
driving the layout engine directly:

```bash
.venv/bin/journalkit check examples/journal
```

```
== module grid ==
daily / daily-front             2.0mm  11 placements, 0 off-grid
daily / daily-back              2.0mm   2 placements, 0 off-grid
    note: content rect is off the lattice by x+1.00mm — placements
          checked relative to it, not to the page
weekly / week-plan              2.0mm   6 placements, 0 off-grid
weekly / week-notes             2.0mm   3 placements, 0 off-grid
    note: …

30 placements checked; all on the 2.0mm grid; 2 page(s) on an off-lattice content rect

== embedded fonts ==
daily.pdf                    Montserrat-Bold, Montserrat-Medium, Montserrat-Regular
weekly.pdf                   Montserrat-Bold, Montserrat-Medium

fonts ok
```

The grid comes from each document's `grid.module`, not from a constant. The
`note:` lines are expected: a 95 mm page cannot put both mirrored margins on a
2 mm grid, so every verso is 1 mm off the lattice by design. Placements are
then checked against that offset, so a module that really drifts still fails.

`geom` gives rendered *ink* positions in millimetres:

```bash
.venv/bin/python tools/dev.py geom examples/journal/out/daily-01-daily-front.svg --min-size 5
```

Bounds include the 0.0882 mm stroke, so a box at x=16 reports 15.96.

### Prove the pipx deliverable

The checkout working is not the same as the wheel working — package data
(icons, scaffold) only shows up in the latter.

```bash
.venv/bin/python -m build --wheel
pipx install --force dist/journalkit-*.whl
cd "$(mktemp -d)" && journalkit init && journalkit build --png --dpi 110 && journalkit check
```

Read the PNG: the `sunrise` icon proves package data shipped; the dashed
`stamp` frame proves `modules/` auto-loading works from an installed wheel.

## Docs

```bash
.venv/bin/pip install zensical                 # or: poetry install --with docs
.venv/bin/zensical build --strict --clean      # must report "No issues found"
.venv/bin/zensical serve                       # http://localhost:8000, live reload
```

`docs/` follows Diátaxis: `tutorial/`, `guide/`, `reference/`,
`explanation/`. The reference pages mirror the code — `reference/modules.md`
must agree with `journalkit modules`, `reference/theme.md` with
`journalkit/theme.py`, `reference/cli.md` with `journalkit --help`.

## Test

```bash
.venv/bin/python tools/dev.py test
# → 30 "ok" lines, then: all tests passed     (~1s)
```

The suite renders in memory; the only files it writes are scaffolded
projects in temp dirs. It pins no template coordinates: every geometric
assertion derives its figures from the document, so redesigning the example
does not break the tests.

## Gotchas

- **A missing font is silent and corrupts the layout.** Inkscape substitutes
  without any warning and exits 0. Since baselines are placed from the font's
  cap-height ratio, a substituted font shifts every label while still
  *looking* like a valid page. `journalkit check` is the cheap detection —
  it asserts every embedded `/BaseFont` is a subset of the document's
  `theme.font.family`. Run it after any PDF build.

- **`check` deliberately ignores geometry drawn inside a module.** The
  invariant is that the *layout engine* snaps placements — a module may draw
  whatever it likes inside its own box (`habit_grid` divides its width into
  seven columns). Use `tools/dev.py ink` to see the sub-grid detail.

- **Warnings arrive on stderr with exit code 0.** Off-grid snapping and
  content overflow are warnings, not errors. Pass `--strict` to make them
  fatal.

- **`--png` and `--pdf` shell out to Inkscape per page**, ~1–2s each. SVG-only
  builds are instant.

- **Project modules register into a process-global registry.** A project
  file may not redefine a built-in name (`box`) — that raises. Two projects
  both defining `stamp` is fine; the later replaces the earlier.

## Troubleshooting

- **`error: unknown module type 'X' (known: …)`**: typo, or the module file is
  not in the project's `modules/`. Check `journalkit modules DIR` lists it;
  pass `--project DIR` to `preview`, or list the file under `modules:` in the
  document.

- **`… has no templates/*.yaml — run journalkit init`**: the SOURCE resolved
  to a directory without a `templates/` folder. Pass the project directory,
  not its parent.

- **`warning: …: content overflows its container by 240.00mm`**: fixed heights
  in the stack exceed the content area. Give one module `height: fill`.

- **`inkscape not found on PATH`**: PDF/PNG export needs Inkscape. SVG
  rendering still works without it.

- **Blank or near-blank PNG**: check the template actually has `pages:`. A
  document with `templates:` but no `pages:` renders one page per template; a
  document with neither exits 1 with `no pages defined in <file>`.
