# pagekit

Structured page templates for a printable notebook. You describe a page as a
list of modules in YAML; pagekit lays them out on a modular grid and renders
print-ready SVG and PDF.

```
.venv/bin/pagekit build templates/daily.yaml --pdf
```

`templates/daily.yaml` reproduces the original Illustrator daily-journal
spread — 105 × 170 mm, 25 mm gutter, 0.25 pt rules, 5 mm dot grid — to within
0.15 mm of the source artwork.

## Setup

Everything is declared in `pyproject.toml`; there is no Makefile.

```sh
poetry install
```

`poetry.toml` pins the virtualenv to `./.venv`, which the rest of this repo
assumes. Without Poetry, the same result in two stdlib commands:

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
```

Either way you get PyYAML and two console scripts in `.venv/bin/`:

| script | purpose |
|---|---|
| `pagekit` | the renderer — `build`, `modules` |
| `pagekit-dev` | dev tasks — `doctor`, `smoke`, `test`, `clean`, `preview`, `grid`, `geom`, `fonts` |

Check your machine has everything (works before the venv exists):

```sh
python3 -m pagekit.dev doctor
```

PDF export shells out to **Inkscape** (font embedding) and, for multi-page
documents, **Ghostscript** (concatenation). SVG output has no dependencies
beyond PyYAML.

## Commands

```sh
pagekit build templates/daily.yaml -o out          # SVG per page
pagekit build templates/daily.yaml --pdf           # + one multi-page PDF
pagekit build templates/daily.yaml --png --dpi 150 # + preview PNGs
pagekit build templates/daily.yaml --debug --png   # overlay grid + margin box
pagekit build templates/daily.yaml --strict        # non-zero exit on any warning
pagekit modules                                    # list module types + params

pagekit-dev smoke      # build + tests + grid + font checks, end to end
pagekit-dev test       # the test suite
pagekit-dev grid       # assert every module placement is on the 2.5mm grid
pagekit-dev clean      # delete out/
```

`pagekit-dev preview` renders ad-hoc module YAML from stdin — the fastest way
to iterate on a module without writing a template file:

```sh
echo '- {type: box, label: HELLO, height: 20, dots: true}' | pagekit-dev preview
```

## The two grids

There are deliberately two, and they do different jobs:

| Grid | Default | Anchored to | Purpose |
|---|---|---|---|
| **module grid** | 2.5 mm | page origin | every module rect snaps to it |
| **dot lattice** | 5 mm | page origin + `origin` offset | printed dots inside modules |

Because the dot lattice is computed from the *page* origin rather than from
each module's own corner, dots line up across every module on the page — and
across pages — no matter where a module lands. Turn dots on per module with
`dots: true`; the module never chooses its own phase.

```yaml
grid:
  module: 2.5
  dots:
    spacing: 5
    origin: [0, 2.5]   # lattice passes through x ≡ 0, y ≡ 2.5 (mm, page coords)
    radius: 0.125
```

A module whose height isn't a multiple of the module grid is snapped to it and
a warning is printed; `--strict` turns that into a failure.

## Page geometry and mirroring

Margins are named `inner` (binding side) and `outer`, so a template is written
once and mirrors itself:

```yaml
page:
  size: [105, 170]      # or a name: a4, a5, a6, b6, letter, half-letter, pocket
  margins: {top: 2.5, bottom: 7.5, inner: 25, outer: 5}
```

`side: right` (recto) puts the binding on the left, `side: left` (verso) on the
right. Specifying `left:`/`right:` explicitly disables mirroring.

Modules never see which side they're on — mirroring is resolved once, when the
content rect is computed.

### Decorations

Page furniture that sits outside the content flow, e.g. the vertical rule 5 mm
inside the binding margin:

```yaml
decorations:
  - type: rule
    edge: inner      # inner | outer | left | right | top | bottom
    offset: 5        # measured away from the text block, so it mirrors
```

For anything else, place it explicitly. `x`/`y` accept a number (page mm) or
an anchor `{from: ..., offset: ...}`; `width`/`height` also accept `full` and
`content`:

```yaml
  - type: text
    text: "2026"
    above: true                    # draw over the content instead of under it
    at:
      x: {from: outer, offset: 2}
      y: {from: bottom, offset: 8}
      width: 20
      height: 5
```

x anchors: `left`, `right`, `center`, `inner`, `outer`, `content_left`,
`content_right`, `content_center`. y anchors: `top`, `bottom`, `middle`,
`content_top`, `content_bottom`, `content_middle`.

## Layout

A page's `content` is a vertical stack. Every module takes:

| Key | Meaning |
|---|---|
| `height` | mm, or `fill` to absorb leftover space |
| `width` | inside a `row`: mm, or `fill` |
| `gap` | space *before* this module, overriding `defaults.gap` |
| `flex` | relative share when several siblings are `fill` (default 1) |
| `valign` | inside a `row`: `top`, `middle`, `bottom` |
| `theme` | per-module theme overrides |
| `id` | a name for your own reference |

Leftover space goes to `fill` modules by weight, rounded down to the module
grid, with the remainder to the last one — so a stack always ends exactly on
its container's bottom edge. Nest `row` and `stack` freely:

```yaml
- type: row
  height: fill
  gap_between: 2.5
  content:
    - {type: stack, content: [{type: box, label: MON, height: fill}, ...]}
    - {type: stack, content: [{type: box, label: THU, height: fill}, ...]}
```

## Modules

Run `pagekit modules` for the full parameter list.

| Type | What it draws |
|---|---|
| `box` | bordered writing area, optional label and dot grid |
| `dotfield` | dot grid, no border |
| `fields` | one framed row split into labelled cells (`DATE | LOC.`) |
| `heading` | section title with an optional icon |
| `rating` | labelled row with a run of icons at the right (mood scale) |
| `checklist` | rows of marker + writing box |
| `lines` | ruled writing area |
| `rule` | a single hairline |
| `text` | a line of free text |
| `spacer` | empty space; `height: fill` pushes what follows down |
| `row`, `stack` | containers |

## Icons

Icons are plain SVG files in `icons/`, referenced by filename stem
(`icon: sunrise`). Requirements: the `viewBox` must be a *tight* bounding box
of the artwork, and paths that should take the theme colour use
`fill="currentColor"`. White fills are preserved as knockouts.

To bring in artwork from Illustrator or anywhere else:

```sh
inkscape --pdf-poppler --export-type=svg --export-filename=raw.svg drawing.ai
inkscape --export-id=path42 --export-id-only --export-area-drawing \
         --export-plain-svg --export-filename=raw/sunrise.svg raw.svg
python3 tools/extract_icons.py raw/sunrise.svg -o icons/
```

`tools/extract_icons.py` computes the tight bounding box by flattening the path
data and rewrites fills to `currentColor`. The current set (`sunrise`, `moon`,
`mood-1`…`mood-5`) was extracted from `Journal.ai` this way.

## Theme

Deep-merged over the defaults in `pagekit/theme.py`. Anything can be overridden
per document, per page (`theme:` on a template) or per module.

```yaml
theme:
  stroke: "#231F20"
  stroke_width: 0.25pt
  font: {family: Montserrat, cap_height: 0.7}
  label: {size: 8pt, weight: 500, dx: 1.8, dy: 3.55}
  heading: {size: 12pt, weight: 700, icon_box: 6, icon_height: 4.6}
```

`cap_height` is how baselines get placed: a label's baseline is `dy` below the
module's top edge, a heading's is centred on its cap height. Lengths accept
`mm` (default), `pt`, `cm`, `in`, `px`. Any module value may also point at the
theme: `stroke: $theme.dots.colour`.

## Adding a module type

One class, one decorator. `natural_height` gives the module an intrinsic size
(return `None` to mean "elastic"); `draw` gets a `Rect` already snapped to the
grid.

```python
from pagekit.modules import Module, register

@register("stamp")
class Stamp(Module):
    """A dashed box to stick a photo in."""
    params = {"label": "text drawn in the corner"}

    def natural_height(self, width):
        return 40.0

    def draw(self, canvas, rect):
        canvas.rect(rect.x, rect.y, rect.w, rect.h, fill="none",
                    stroke=self.stroke, stroke_width=self.stroke_width,
                    stroke_dasharray="1 1")
        self.draw_label(canvas, rect)
        self.draw_dots(canvas, rect)   # honours `dots:` for free
```

Point a document at the file and use it:

```yaml
modules: [../custom/habits.py]
```

Helpers available on `Module`: `self.opt(key, default)` (resolves
`$theme.` references), `self.length(key)`, `self.stroke`, `self.stroke_width`,
`self.text(...)`, `self.draw_label(...)`, `self.draw_dots(...)`,
`self.cap_height()`, and `self.ctx` for the theme, icon set, page/content rects
and the dot lattice. `custom/habits.py` is a worked example.

## Layout of the repo

```
pagekit/            the library
  units.py          lengths and grid snapping
  geometry.py       Rect
  spec.py           YAML -> document model
  layout.py         stack and row solving
  theme.py          defaults + deep merge
  icons.py          icon loading and placement
  svg.py            minimal SVG writer (1 user unit = 1 mm)
  render.py         page rendering, dot lattice, decorations
  cli.py            build / modules
  modules/          module registry and the built-in library
  dev.py            dev-task runner behind the `pagekit-dev` script
templates/          notebook definitions (daily, weekly)
custom/             example project-local module type
icons/              icon library
tools/              icon extraction helper
tests/              run with `pagekit-dev test`
```
