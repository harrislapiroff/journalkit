# Document format

A document is one YAML file in a project's `templates/`. Every key is
optional except that you need at least one template or page to render
anything. Lengths are millimetres unless suffixed; see
[units](units.md).

```yaml
document: daily                 # name; default: the file stem
modules: [../shared/extra.py]   # extra module files, relative to this file
icons: [../shared/icons]        # extra icon directories, relative to this file

page:
  size: [105, 170]              # [w, h] | {width, height} | a named size
  margins:
    top: 2.5
    bottom: 7.5
    inner: 15                   # binding side
    outer: 5
    # all: 10                   # sets the four above at once
    # left: 10                  # with right: disables mirroring
    # right: 10

grid:
  module: 2.5                   # module grid step
  dots:
    spacing: 5
    origin: [0, 2.5]            # or a single number for both axes
    radius: 0.125
    colour: "#231F20"
    opacity: 1
    inset: 0

defaults:
  gap: 2.5                      # default space between modules; default: the module grid

theme: {}                       # see the theme reference

decorations: []                 # drawn on every page; see below

templates:
  <name>:
    side: right                 # right (recto, default) | left (verso)
    content: []                 # the stack of modules
    decorations: []             # this template only, in addition to the document's
    theme: {}                   # merged over the document theme
    margins: {}                 # replaces the document margins for this template
    gap: 2.5                    # replaces defaults.gap for this template

pages:
  - front                       # a template name
  - {template: back}            # or a mapping…
  - {template: daily, repeat: 31}          # …repeated: daily-01 … daily-31
  - {template: daily, side: left, name: x} # …with any template key overridden
```

## Top level

| key | type | default | |
|---|---|---|---|
| `document` | string, or `{name: …}` | file stem | output file prefix |
| `modules` | list of paths | `[]` | Python files to import; the project's `modules/` is loaded regardless |
| `icons` | list of paths | `[]` | icon directories searched before the project's `icons/` and the built-ins |
| `page` | mapping | a5, default margins | |
| `grid` | mapping or number | `2.5` | a bare number is the module grid |
| `dots` | mapping | | accepted at top level as an alias for `grid.dots` |
| `defaults.gap` | length | module grid | |
| `theme` | mapping | | deep-merged over the defaults |
| `decorations` | list | `[]` | |
| `templates` | mapping | `{}` | |
| `pages` | list | one page per template, in order | |

## `page`

`size` is a named size (`a4` … `hobonichi-weeks`, see [units](units.md)), a
two-element list, or `{width, height}`.

`margins` default to `{top: 10, bottom: 10, inner: 15, outer: 10}`. `inner`
is the binding side and mirrors with `side`; `left`/`right`, if given,
replace the mirrored pair and disable mirroring.

## `grid`

`module` is the step every module rectangle snaps to. `dots` describes the
page-anchored dot lattice: the lattice consists of points
`(origin.x + i·spacing, origin.y + j·spacing)` in page coordinates; modules
with `dots: true` draw the points strictly inside their rectangle.
`colour`, `radius` and `opacity` default to `theme.dots.*`.

## Templates and pages

A **template** is a page definition. A **page** is an instance of one, and
the `pages` list is what gets rendered, in order. A page entry may be a bare
template name or a mapping with `template` plus any template key to
override; `repeat: N` expands it to `N` pages named `<name>-01` … `<name>-NN`.
Without `pages`, every template renders once in declaration order.

Page names become part of output file names: `<document>-<nn>-<name>.svg`.

## Modules in `content`

Each entry is a mapping with `type` and that module's parameters (see the
[module reference](modules.md)), plus these common keys:

| key | |
|---|---|
| `height` | length, or `fill` |
| `width` | inside a `row`: length, or `fill` |
| `gap` | space before this module, overriding the default |
| `flex` | weight among sibling `fill` modules; default 1 |
| `valign` | inside a `row`: `top` (default), `middle`, `bottom` |
| `theme` | per-module theme overrides |
| `id` | a name for your own reference; unused by JournalKit |
| `stroke`, `stroke_width` | per-module overrides where the module draws a frame |

A bare string is shorthand for `{type: <string>}`, so `- spacer` works.

Any value may reference the theme as `$theme.<path>`.

## Decorations

Each entry is a module spec drawn outside the content flow. Two placement
forms:

```yaml
- {type: rule, edge: inner, offset: 4}      # full-length rule beside an edge
- type: text                                # explicit rectangle
  text: "2026"
  above: true                               # over the content; default under
  at:
    x: {from: outer, offset: 2}             # number | anchor name | {from, offset}
    y: {from: bottom, offset: 6}
    width: 20                               # length | full | content
    height: 5
```

`edge` accepts `inner`, `outer`, `left`, `right`, `center` (vertical, full
height) and `top`, `bottom` (horizontal, full width). Anchors for `at` are
listed in the [decorations guide](../guide/decorations.md).

## Errors

A YAML syntax error is reported as `<file>: <message>`; an unknown module
type lists the known ones; an unknown template, page size, unit or anchor
names the offending value. All exit 1.
