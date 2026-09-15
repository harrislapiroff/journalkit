# journalkit

Page templates for a printable, hand-bound journal. You describe each page as
a list of modules in YAML — a dated header, a rating scale, a dotted notes box,
a checklist — and journalkit lays them out on a modular grid and renders
print-ready SVG and PDF.

```sh
pipx install https://github.com/harrislapiroff/journalkit/archive/refs/heads/main.tar.gz
journalkit init my-journal && cd my-journal
journalkit build --pdf
```

Pure Python plus PyYAML. PDF and PNG export shell out to **Inkscape** (for
font embedding) and, for multi-page documents, **Ghostscript**; SVG output
needs neither.

**Documentation: <https://harrislapiroff.github.io/journalkit/>** — a
tutorial, task guides, the full reference, and the reasoning behind the
design. This README is the short version.

## Install

With [pipx](https://pipx.pypa.io/), straight from GitHub — no git needed,
pip downloads the archive:

```sh
pipx install https://github.com/harrislapiroff/journalkit/archive/refs/heads/main.tar.gz
```

Upgrade the same way with `pipx install --force …`. To pin a release instead
of following `main`, use a tag: `…/archive/refs/tags/v0.2.0.tar.gz`.

Then the tools for PDF output, if you want it:

```sh
brew install --cask inkscape
brew install ghostscript
```

Text is drawn as outlines from a bundled copy of Montserrat, so there is no
font to install. To use a different font, set `theme.font.family` and have
it installed on the machine that builds; `journalkit doctor` reports whether
it was found.

## A project

journalkit runs on a directory. `journalkit init` creates one:

```
my-journal/
  templates/   one YAML document per printable thing (a spread, a section)
  modules/     optional: Python files adding module types with @register
  icons/       optional: SVG icons, looked up by stem before the built-ins
  out/         what `journalkit build` writes
```

Every command takes zero or more sources — a project directory or a single
YAML file — and defaults to the directory you are in:

```sh
journalkit build                      # every templates/*.yaml → out/*.svg
journalkit build --pdf                # + one multi-page PDF per document
journalkit build --png --dpi 150      # + a preview PNG per page
journalkit build --debug --png        # overlay the module grid and margin box
journalkit build --strict             # non-zero exit on any warning
journalkit build templates/daily.yaml -o ~/Desktop/proofs

journalkit watch --png                # rebuild on every save; ctrl-c to stop
journalkit check                      # placements on the grid, fonts embedded
journalkit modules                    # module types + parameters, yours included
journalkit doctor                     # inkscape, ghostscript, fonts
```

`preview` renders ad-hoc module YAML from stdin — the fastest way to try a
module without writing a template:

```sh
echo '- {type: box, label: HELLO, height: 20, dots: true}' | journalkit preview
# → out/preview/preview-01-preview.png
```

Warnings — a height snapped to the grid, content that overflows — go to stderr
with exit code 0; `watch` prints them under the file that produced them, and
`--strict` makes them fatal.

## A document

```yaml
document: daily

page:
  size: [105, 170]                  # or a name: a5, a6, b6, pocket, half-letter …
  margins: {top: 2.5, bottom: 7.5, inner: 15, outer: 5}

grid:
  module: 2.5                       # every module snaps to this
  dots: {spacing: 5, origin: [0, 2.5], radius: 0.125}

theme:
  font: {family: Montserrat}

templates:
  front:
    side: right
    content:
      - {type: fields, columns: [{label: DATE, width: 25}, {label: "LOC."}]}
      - {type: heading, text: MORNING, icon: sunrise}
      - {type: rating, label: MOOD, icon: mood, count: 5}
      - {type: box, label: NOTES, height: fill, dots: true}
      - {type: checklist, rows: 3}
  back:
    side: left
    content:
      - {type: lines, height: fill, label: REFLECTION}

pages: [front, back]
```

`examples/journal/` in this repository is a complete project with two
documents, and `journalkit init` writes a smaller one to start from.

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
  module: 2          # what templates/ uses; the built-in default is 2.5
  dots:
    spacing: 4
    origin: [0, 2]   # lattice passes through x ≡ 0, y ≡ 2 (mm, page coords)
    radius: 0.125
```

A module whose height isn't a multiple of the module grid is snapped to it and
a warning is printed; `--strict` turns that into a failure. That applies to
heights *you* wrote. A module's own intrinsic height — a heading's 7.5 mm —
is snapped silently, because no template could fix it.

### Choosing a grid your page can actually hold

Both grids are anchored to the page, so the page has to be commensurate with
them, and mirrored margins make that stricter than it looks:

* on a recto the text block starts at `inner`, so `inner` must be a multiple
  of the grid;
* on a verso it starts at `outer`, so `outer` must be too;
* the block's width is `page − inner − outer`, so the **page dimension** must
  be a multiple of the grid as well.

Check the arithmetic before choosing a grid. A 105 mm page is 42 × 2.5, so it
sits perfectly on a 2.5 mm grid; it is *not* a multiple of 2, so on a 2 mm
grid one of the two margins has to be odd and the verso is unavoidably half a
grid step off the lattice. You can accept that — the dots on a verso will then
sit 1 mm closer to one border than to the other — but it should be a choice.

`journalkit check` reports such a page as a per-page note rather than a
failure, and checks module placements against the page's own offset — so it
still catches the thing that is a bug (a module drifting off the grid) on a
page that has knowingly given up the thing that is a choice.

### Dots and labels

Dots are omitted where they would collide with a module's label, rather than
the label being drawn on top of them — on a printed page a dot behind a title
reads as a smudge. Only points that actually fall in the label's line are
dropped, so the rest of the grid stays exactly on the lattice.

```yaml
theme:
  dots:
    reserve_label: band   # band (default) | text | none
    label_pad: 0.75       # extra clearance around the label, mm
```

| mode | effect |
|---|---|
| `band` | clears the label's whole line across the module — the grid starts below the title |
| `text` | clears only the label's own width, so dots continue to its right |
| `none` | dots run underneath the label |

`text` measures the label from the font file (`journalkit/fontmetrics.py`, a
small sfnt reader with no dependencies). The same reader supplies the cap
height used to place baselines, and the glyph outlines text is drawn with.

## Page geometry and mirroring

Margins are named `inner` (binding side) and `outer`, so a template is written
once and mirrors itself:

```yaml
page:
  size: [105, 170]      # or a name: a4, a5, a6, b6, letter, half-letter, pocket
  margins: {top: 2, bottom: 8, inner: 16, outer: 5}
```

`side: right` (recto) puts the binding on the left, `side: left` (verso) on the
right. Specifying `left:`/`right:` explicitly disables mirroring.

Modules never see which side they're on — mirroring is resolved once, when the
content rect is computed.

### Decorations

Page furniture that sits outside the content flow, e.g. the vertical rule 4 mm
inside the binding margin:

```yaml
decorations:
  - type: rule
    edge: inner      # inner | outer | left | right | top | bottom
    offset: 4        # measured away from the text block, so it mirrors
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

Run `journalkit modules` for the full parameter list, including any types your
project's `modules/` adds.

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
| `habit_grid` | habit tracker: one labelled row per habit, one marker per day |
| `row`, `stack` | containers |

## Icons

Icons are plain SVG files referenced by filename stem (`icon: sunrise`). The
built-in set — `sunrise`, `moon`, `mood-1` … `mood-5` — ships with journalkit;
drop your own into your project's `icons/` and they take precedence.
Requirements: the `viewBox` must be a *tight* bounding box of the artwork, and
paths that should take the theme colour use
`fill="currentColor"`. White fills are preserved as knockouts.

To bring in artwork from Illustrator or anywhere else:

```sh
inkscape --pdf-poppler --export-type=svg --export-filename=raw.svg drawing.ai
inkscape --export-id=path42 --export-id-only --export-area-drawing \
         --export-plain-svg --export-filename=raw/sunrise.svg raw.svg
python3 tools/extract_icons.py raw/sunrise.svg -o my-journal/icons/
```

`tools/extract_icons.py` computes the tight bounding box by flattening the path
data and rewrites fills to `currentColor`. The built-in set was produced this
way from an Illustrator file, so it is a fair template for your own.

## Theme

Deep-merged over the defaults in `journalkit/theme.py`. Anything can be overridden
per document, per page (`theme:` on a template) or per module.

### Colour

One value, `ink`, stands behind every mark on the page — strokes, label and
heading text, dots and rules all default to `$theme.ink`. To recolour a whole
document, set it once:

```yaml
theme:
  ink: "#000"        # pure black everywhere
```

Any single role can still be pinned without disturbing the rest, which is the
usual way to soften the dot grid relative to the text:

```yaml
theme:
  ink: "#000"
  dots: {colour: "#999"}
```

The default `ink` is `#231F20`, a rich black that prints a little softer than
`#000`.
Knockouts (the page background, the white fill behind a checklist marker) are
deliberately not themed — they have to stay white to mask what is under them.

Any value may point at another with `$theme.<path>`, and chains resolve;
a cycle raises rather than hanging.

```yaml
theme:
  ink: "#231F20"
  stroke_width: 0.25pt
  font: {family: Montserrat}   # bundled; outlines and cap height read from the file
  label: {size: 8pt, weight: 500, dx: 1.8, dy: 3.55}
  heading: {size: 12pt, weight: 700, icon_box: 6, icon_height: 4.6}
```

`cap_height` is how baselines get placed: a label's baseline is `dy` below the
module's top edge, a heading's is centred on its cap height. Leave it null to
read the true value from the font. Lengths accept
`mm` (default), `pt`, `cm`, `in`, `px`. Any module value may also point at the
theme: `stroke: $theme.dots.colour`.

## Adding a module type

One class, one decorator. `natural_height` gives the module an intrinsic size
(return `None` to mean "elastic"); `draw` gets a `Rect` already snapped to the
grid.

```python
from journalkit.modules import Module, register

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

Save that as `modules/stamp.py` in your project and `type: stamp` is available
in every template there — every `.py` in `modules/` is imported before a
build. A file that lives somewhere else can be listed in one document instead:

```yaml
modules: [../shared/stamp.py]
```

`journalkit init` writes exactly this module into a new project as a worked
example. A project module may not redefine a built-in name.

Helpers available on `Module`: `self.opt(key, default)` (resolves
`$theme.` references), `self.length(key)`, `self.stroke`, `self.stroke_width`,
`self.text(...)`, `self.draw_label(...)`, `self.draw_dots(...)`,
`self.draw_marker(...)` (the checkbox, centred in the rect you hand it),
`self.cap_height()`, and `self.ctx` for the theme, icon set, page/content rects
and the dot lattice. `journalkit/modules/trackers.py` (the habit grid) is the
shortest complete built-in.

## Layout of the repo

```
journalkit/         the library — what `pipx install journalkit` ships
  cli.py            build · watch · preview · check · modules · doctor · init
  project.py        the project directory: templates/, modules/, icons/, out/
  units.py          lengths and grid snapping
  geometry.py       Rect
  spec.py           YAML -> document model
  layout.py         stack and row solving
  theme.py          defaults + deep merge
  icons.py          icon loading and placement
  icons/            the built-in icon set (package data)
  fontmetrics.py    sfnt reader: advance widths, cap height, glyph outlines
  fonts/            Montserrat Regular/Medium/Bold (OFL), bundled
  svg.py            minimal SVG writer (1 user unit = 1 mm)
  render.py         page rendering, dot lattice, decorations
  checks.py         the grid and font checks behind `journalkit check`
  watch.py          rebuild-on-change and stdin preview
  modules/          module registry and the built-in library
  scaffold/         what `journalkit init` copies into a new project
examples/journal/   a complete two-document project
tools/
  dev.py            repo-only tasks: test, smoke, clean, geom, ink, pages
  extract_icons.py  icon extraction helper
tests/              run with `.venv/bin/python tools/dev.py test`
docs/ + zensical.toml  the documentation site (Zensical); `zensical serve`
```
