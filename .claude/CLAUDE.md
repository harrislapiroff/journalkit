# journalkit

YAML page definitions → print-ready SVG/PDF for a hand-bound journal, as a
pipx-installable tool that runs on a *project directory* (`templates/`,
optional `modules/` and `icons/`). Pure Python + PyYAML; Inkscape and
Ghostscript are only needed for PDF/PNG.

@../README.md

## Working here

Setup and the entry point live in `pyproject.toml` — **there is no Makefile.**

```sh
poetry install                  # or: python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python tools/dev.py smoke     # build the example + tests + check + pdf size
```

`poetry.toml` pins the virtualenv to `./.venv`. Don't remove it — the run
skill's documented paths and the permission allowlist assume `.venv/bin/`.

Two layers, deliberately:

- **`journalkit`** (`journalkit/cli.py`) is the product. `build`, `watch`,
  `preview`, `check`, `modules`, `doctor`, `init`. It never assumes a
  checkout: built-in icons come from `journalkit/icons/` as package data,
  the `init` scaffold from `journalkit/scaffold/`, and everything else from
  the user's project (`journalkit/project.py`).
- **`tools/dev.py`** is for working on the repo: `test`, `smoke`, `clean`,
  and the measurement tools `geom`, `ink`, `pages`. pipx never installs it.

`examples/journal/` is the notebook this started as, kept as a real project
so the tests and smoke run exercise both grids, mirroring, the habit tracker
and the packaged icons. Its templates are the test fixtures — keep them
building.

To drive, screenshot, or verify the renderer, use the `run-journalkit` skill
(`.claude/skills/run-journalkit/SKILL.md`).

## Invariants worth not breaking

- **Module placements snap to the module grid** — 2 mm in the example, and
  read per document, never assumed. What a module draws *inside* its own rect
  need not. `journalkit check` asserts the former by driving the layout
  engine; `tools/dev.py ink` reports the latter, informationally.
- **A page can only hold a grid it is commensurate with.** Both grids are
  page-anchored, and mirroring means `inner`, `outer` and the page dimension
  must all be multiples of it. 105 mm is 42 × 2.5 but not a multiple of 2, so
  on the 2 mm grid the example's verso is knowingly 1 mm off the lattice.
  `journalkit check` prints that as a per-page note and then checks placements
  *relative to* the page's offset — a module drifting off the grid still fails.
  Don't "fix" the note by loosening the check.
- **The dot lattice is anchored to the page**, not to the module — that is what
  makes dots line up across modules and across pages. Never phase it per module.
  Dots that would collide with a label are *dropped*, never shifted, so the
  survivors stay on the lattice (`theme.dots.reserve_label`).
- **Mirroring is resolved once**, when the content rect is computed from
  `inner`/`outer` margins. No module should ever branch on `side`.
- **Text is positioned from `font.cap_height`**, read from whatever family
  the theme names. A missing font substitutes silently in Inkscape and shifts
  every baseline — `journalkit check` verifies the PDF's embedded fonts against
  the document's own `theme.font.family`; run it after any PDF build.
- **Nothing pins the example's exact geometry.** `test_back_page_is_mirrored`
  and `journalkit check` derive every figure from the document, so a redesign
  changes the output without breaking them. Keep it that way: assert
  properties, not coordinates.
- **Colour flows from one value.** `theme.ink` stands behind stroke, label,
  heading, dots and lines via `$theme.ink`; a new colour role should point at
  it rather than hard-code a hex. White knockouts are not themed on purpose.
- **The registry protects built-ins.** A project module may not redefine
  `box`; two *project* files registering the same name replace one another,
  because two projects are routinely built in one process
  (`journalkit/modules/base.py:register`).

## Conventions

- All internal lengths are floats in **millimetres**; one SVG user unit = 1 mm.
- YAML lengths may carry units (`0.25pt`, `1in`, `12px`); parse via
  `journalkit.units.mm`.
- New built-in module types: one class + `@register("name")` in
  `journalkit/modules/`, imported from its `__init__.py`. Project-local types
  go in the project's `modules/*.py` and are auto-loaded; a document can also
  list one-off files under `modules:`. `journalkit/scaffold/modules/stamp.py`
  is the worked example users get.
- Warnings (off-grid snapping, overflow) go to stderr with exit code 0; `--strict`
  makes them fatal. Only sizes written in a template warn — a module's intrinsic
  height is snapped silently, since no template could act on it.
- Anything a user needs to know goes in `README.md`; anything only the
  checkout needs goes here or in the skill.
