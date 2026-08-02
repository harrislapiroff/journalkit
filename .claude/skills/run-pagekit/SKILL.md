---
name: run-pagekit
description: Build, run, and drive pagekit — the notebook page-template renderer that turns YAML into printable SVG/PDF. Use when asked to run pagekit or the notebook generator, render or preview a template, screenshot a page, add or test a module type, check the 2.5mm grid, or verify PDF output.
---

pagekit renders YAML page definitions into print-ready SVG and PDF. It has no
GUI and no server — the "running app" is a set of print artifacts — so driving
it means rendering, *looking* at the result, and asserting the invariants that
make it correct. All three are in one harness — the `pagekit-dev` console
script (source: **`pagekit/dev.py`**).

All paths below are relative to the project root (the directory holding
`pyproject.toml`). Verified on macOS 26.5 / arm64 / Python 3.12.0 /
Inkscape 1.3.2.

## Prerequisites

Two external tools. SVG output needs neither; PDF and PNG need both.

```bash
brew install --cask inkscape      # SVG -> PDF/PNG, embeds fonts
brew install ghostscript          # merges per-page PDFs into one document
```

The **Montserrat** font must be installed system-wide (`~/Library/Fonts/`).
This is not optional — see Gotchas.

Check everything at once. `doctor` is stdlib-only, so run it with **system
python3** — it works before the venv exists, which is the point:

```bash
python3 -m pagekit.dev doctor
```

On a clean checkout it tells you exactly what to do next, and exits 1:

```
prerequisites:
  ok   inkscape  /opt/homebrew/bin/inkscape
  ok   gs        /opt/homebrew/bin/gs
  FAIL venv      missing — run: python3 -m venv .venv && .venv/bin/pip install -e .
  FAIL pagekit   console script missing — run: .venv/bin/pip install -e .
  FAIL pyyaml    unknown — no venv to check
  ok   Montserrat font installed

MISSING: venv, pagekit-script, pyyaml
```

After setup all six lines read `ok` and it exits 0. Every other command needs
the venv, so use `.venv/bin/pagekit-dev` for those.

## Setup

There is no Makefile — the entry points live in `pyproject.toml`.

```bash
poetry install
```

Takes ~1.5s from clean. Without Poetry, two stdlib commands do the same job
in ~6s:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

Either path pulls PyYAML and installs two console scripts into `.venv/bin/`:
`pagekit` (the renderer) and `pagekit-dev` (this harness). The editable
install is what makes both cwd-independent — see Gotchas.

## Run (agent path)

Everything goes through the driver. Run it from the project root:

```bash
.venv/bin/pagekit-dev <command>
```

| command | what it does |
|---|---|
| `doctor` | check tools, venv, font; non-zero if anything is missing |
| `smoke` | **everything end to end** — build, tests, grid, fonts, PDF size |
| `build [tmpl…] [--pdf] [--png] [--dpi N] [--debug]` | render; default is every `templates/*.yaml` |
| `shot <tmpl> [--page N] [--dpi N] [--debug]` | render + rasterise, prints PNG paths to `Read()` |
| `preview [--modules F] [--debug]` | render ad-hoc module YAML **from stdin** |
| `grid [tmpl…]` | assert every module placement is on the 2.5mm grid |
| `ink [svg…]` | report sub-grid geometry *inside* modules (informational) |
| `geom <svg> [--min-size N]` | rendered ink geometry in mm, via Inkscape |
| `fonts [pdf…]` | assert PDFs embed Montserrat, not a substitute |
| `pages <pdf>` | page count + MediaBox in mm |

Artifacts land in `out/` — `out/shots/` for `shot`, `out/preview/` for `preview`.

### Start here

```bash
.venv/bin/pagekit-dev smoke
```

```
==============================================
doctor   ok
build    ok
tests    ok
grid     ok
fonts    ok
pages    ok

SMOKE PASSED
```

### Look at a page

`shot` prints PNG paths; open them with `Read()`.

```bash
.venv/bin/pagekit-dev shot templates/daily.yaml --page 1 --dpi 130
# → /Users/harris/Projects/Personal/notebook/out/shots/daily-01-daily-front.png
```

Add `--debug` to overlay the 2.5mm grid and the margin box — the fastest way to
see *why* something sits where it does.

### Iterate on a module (the main dev loop)

`preview` takes just the `content:` entries on stdin and wraps them in a
throwaway document, so you never write a template file to try something:

```bash
cat <<'YAML' | .venv/bin/pagekit-dev preview
- {type: heading, text: PREVIEW, icon: sunrise}
- {type: fields, columns: [ALPHA, BETA, GAMMA]}
- {type: rating, label: SCALE, icon: mood, count: 5}
- {type: checklist, rows: 3}
- {type: lines, height: 20, border: true, label: RULED}
- {type: box, label: DOTS, height: fill, dots: true}
YAML
# → /Users/harris/Projects/Personal/notebook/out/preview/preview-01-preview.png
```

For a project-local module type, point at the file (path relative to the
project root):

```bash
echo '- {type: habit_grid, headers: [M,T,W,T,F,S,S], habits: [MOVE, READ]}' \
  | .venv/bin/pagekit-dev preview --modules custom/habits.py
```

### Verify a layout change numerically

Don't eyeball layout regressions. `grid` proves the core invariant by driving
the layout engine directly:

```bash
.venv/bin/pagekit-dev grid
```

```
daily / daily-front                  9 placements, 0 off-grid
daily / daily-back                   1 placements, 0 off-grid
weekly / week-plan                   7 placements, 0 off-grid
weekly / week-notes                  4 placements, 0 off-grid

29 placements checked; all on the 2.5mm grid
```

`geom` gives rendered *ink* positions in millimetres — this is how the daily
template was matched to the original Illustrator artwork to within 0.15mm:

```bash
.venv/bin/pagekit-dev geom out/daily-01-daily-front.svg --min-size 5
```

```
id                    x        y        w        h    right   bottom
svg61              0.00     0.00   105.00   170.00   105.00   170.00
rect1              0.00     0.00   105.00   170.00   105.00   170.00
line1             19.96     0.00     0.09   170.00    20.04   170.00
rect2             24.96     2.46    75.09     5.09   100.04     7.54
text2             27.10     4.07     7.36     1.98    34.46     6.05
```

Reference values from the source artwork: content block x 25→100, binding rule
at x=20, first field row y 2.5→7.5. Bounds include the 0.0882mm stroke, hence
24.96 rather than 25.00.

## Run (human path)

The product CLI, separate from the dev harness:

```bash
.venv/bin/pagekit build templates/daily.yaml -o out --pdf
.venv/bin/pagekit build templates/daily.yaml -o out --png --dpi 150
.venv/bin/pagekit build templates/daily.yaml -o out --debug   # grid overlay
.venv/bin/pagekit modules          # list module types and their parameters
```

Housekeeping:

```bash
.venv/bin/pagekit-dev clean        # deletes out/
```

## Test

```bash
.venv/bin/pagekit-dev test
# → 15 "ok" lines, then: all tests passed     (~1s)
```

The suite renders in memory and writes nothing. `test_daily_matches_the_original_artwork`
asserts real coordinates measured from the source Illustrator file — if you
change layout maths, that is the test that will catch it.

## Gotchas

- **A missing font is silent and corrupts the layout.** Inkscape substitutes
  without any warning and exits 0. Probed directly: an SVG asking for a
  nonexistent family produced `XQLOTU+Verdana` in the PDF, no diagnostic. Since
  pagekit places baselines using Montserrat's cap-height ratio (0.7), a
  substituted font shifts every label while still *looking* like a valid page.
  `pagekit-dev fonts` is the only cheap detection — it asserts every embedded
  `/BaseFont` is a Montserrat subset. Run it after any PDF build.

- **Skipping `pip install -e .` leaves you cwd-dependent.** `python -m pagekit`
  only resolves the package when cwd is the project root; from anywhere else it
  is `No module named pagekit`. The editable install fixes that and provides
  both console scripts. If `doctor` reports the console script missing, run
  `.venv/bin/pip install -e .`. The one command that works *without* it is
  `python3 -m pagekit.dev doctor` from the project root — deliberately, so a
  broken machine can still be diagnosed.

- **`grid` deliberately ignores geometry drawn inside a module.** The invariant
  is that the *layout engine* snaps module placements to 2.5mm — a module may
  draw whatever it likes inside its own box. `habit_grid` divides 50mm into 7
  columns of 7.1429mm, and that is correct. Parsing the SVG cannot tell those
  cases apart, which is why `grid` drives the layout engine instead. Use `ink`
  if you actually want to see the sub-grid detail.

- **Warnings arrive on stderr with exit code 0.** Off-grid snapping and content
  overflow are warnings, not errors — a build "succeeds" while silently
  resizing your module. `pagekit-dev preview` and `build` always print stderr for
  this reason. Pass `--strict` to the `pagekit` CLI to turn warnings into a
  non-zero exit.

- **Bounding boxes include the stroke.** Every `geom` figure is offset by half
  the 0.0882mm (0.25pt) stroke — a box at x=25 reports 24.96. Don't chase that
  0.04mm; compare like with like.

- **`--png` and `--pdf` shell out to Inkscape per page**, ~1–2s each. SVG-only
  builds are instant. Use plain `build` while iterating and add `--png` only
  when you need to look.

## Troubleshooting

- **`No module named pagekit`**: you ran `python -m pagekit` from outside the
  project root without an editable install. Fix: `.venv/bin/pip install -e .`,
  then use `.venv/bin/pagekit`. The driver is immune — it resolves the project
  root from its own file location and passes `cwd=ROOT`.

- **`error: unknown module type 'X' (known: box, checklist, dotfield, fields,
  heading, lines, rating, row, rule, spacer, stack, text)`**: typo, or a custom
  module file that wasn't loaded. Add `modules: [../custom/habits.py]` to the
  document, or pass `--modules custom/habits.py` to `pagekit-dev preview`.

- **`warning: ...: content overflows its container by 240.00mm`**: fixed heights
  in the stack exceed the content area. Give one module `height: fill` so it
  absorbs the remainder, or reduce a fixed height.

- **`warning: box: height 11.000mm is off the 2.500mm grid, snapped to
  10.000mm`**: working as designed — use a multiple of 2.5.

- **`inkscape not found on PATH; install it or use --svg-only`**: PDF/PNG export
  needs Inkscape. SVG rendering still works without it.

- **Blank or near-blank PNG**: check the template actually has `pages:`. A
  document with `templates:` but no `pages:` renders one page per template; a
  document with neither renders nothing and exits 1 with
  `no pages defined in <file>`.
