# pagekit

YAML page definitions → print-ready SVG/PDF for a hand-bound notebook.
Pure Python + PyYAML; Inkscape and Ghostscript are only needed for PDF/PNG.

@../README.md

## Working here

Setup and the task runner live in `pyproject.toml` — **there is no Makefile.**

```sh
poetry install                  # or: python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/pagekit-dev smoke     # build + tests + grid + font checks
```

`poetry.toml` pins the virtualenv to `./.venv`. Don't remove it — `doctor`,
the run skill's documented paths and the permission allowlist all assume
`.venv/bin/`, and Poetry otherwise hides the venv in its global cache.

To drive, screenshot, or verify the renderer, use the `run-pagekit` skill
(`.claude/skills/run-pagekit/SKILL.md`) — it documents the `pagekit-dev`
harness, including `preview` for iterating on a module from stdin and `geom`
for checking layout against the original artwork in millimetres.

## Invariants worth not breaking

- **Module placements snap to the module grid** — 2 mm in `templates/`, and
  read per document, never assumed. What a module draws *inside* its own rect
  need not. `pagekit-dev grid` asserts the former by driving the layout engine;
  `pagekit-dev ink` reports the latter, informationally.
- **A page can only hold a grid it is commensurate with.** Both grids are
  page-anchored, and mirroring means `inner`, `outer` and the page dimension
  must all be multiples of it. 105 mm is 42 × 2.5 but not a multiple of 2, so
  on the 2 mm grid the daily verso is knowingly 1 mm off the lattice.
  `pagekit-dev grid` prints that as a per-page note and then checks placements
  *relative to* the page's offset — a module drifting off the grid still fails.
  Don't "fix" the note by loosening the check.
- **The dot lattice is anchored to the page**, not to the module — that is what
  makes dots line up across modules and across pages. Never phase it per module.
  Dots that would collide with a label are *dropped*, never shifted, so the
  survivors stay on the lattice (`theme.dots.reserve_label`).
- **Mirroring is resolved once**, when the content rect is computed from
  `inner`/`outer` margins. No module should ever branch on `side`.
- **Text is positioned from `font.cap_height`.** It assumes Montserrat. A
  missing font substitutes silently and shifts every baseline — see the Gotchas
  in the run skill, and run `pagekit-dev fonts` after any PDF build.
- `templates/daily.yaml` began as a 0.15 mm reproduction of the source
  Illustrator artwork and was redrawn on the 2 mm grid; the test that pinned
  the artwork coordinates is gone. Nothing pins the templates' exact geometry
  now — `test_back_page_is_mirrored` and `pagekit-dev grid` derive every figure
  from the document, so a redesign changes the output without breaking them.
  Keep it that way: assert properties, not coordinates.

- **Colour flows from one value.** `theme.ink` stands behind stroke, label,
  heading, dots and lines via `$theme.ink`; a new colour role should point at
  it rather than hard-code a hex. White knockouts are not themed on purpose.

## Conventions

- All internal lengths are floats in **millimetres**; one SVG user unit = 1 mm.
- YAML lengths may carry units (`0.25pt`, `1in`, `12px`); parse via
  `pagekit.units.mm`.
- New module types: one class + `@register("name")` in `pagekit/modules/`, or a
  project-local file referenced by `modules:` in a document. See
  `custom/habits.py`.
- Warnings (off-grid snapping, overflow) go to stderr with exit code 0; `--strict`
  makes them fatal. Only sizes written in a template warn — a module's intrinsic
  height is snapped silently, since no template could act on it.
