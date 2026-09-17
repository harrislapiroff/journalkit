# Custom modules

A module type is one Python class in your project's `modules/`. The file is
imported before every build, and `@register` makes its name available as
`type:` in YAML. The [tutorial](../tutorial/write-a-module.md) writes one
from scratch; this page lists what a module can use.

## Skeleton

```python
from journalkit.modules import Module, register

@register("stamp")
class Stamp(Module):
    """One line shown by `journalkit modules`.

    Further lines are shown too.
    """
    params = {"label": "text drawn in the corner"}     # documentation only

    def natural_height(self, width):
        return 40.0                                      # or None: elastic

    def draw(self, canvas, rect):
        ...
```

`rect` is a `Rect` in page millimetres, already snapped to the module grid.
`canvas` is the SVG writer. Draw anything you like inside the rect — the grid
invariant is about placement, not about what you draw.

## Reading options

| helper | does |
|---|---|
| `self.opt("key", default)` | the YAML value, with `$theme.…` references expanded |
| `self.length("key", default)` | the same, converted to millimetres (`"0.5pt"` → float) |
| `self.spec` | the raw YAML mapping |
| `self.theme` | the module's theme — the page theme with this module's `theme:` merged in |
| `self.theme.get("dots.colour")`, `self.theme.mm("label.dy")` | theme lookups |
| `self.stroke`, `self.stroke_width` | the module's `stroke` / `stroke_width` options, defaulting to the theme |

## Drawing helpers

| helper | draws |
|---|---|
| `self.text(canvas, x, y, text, style="label", **overrides)` | themed text with its baseline at `(x, y)`, drawn as outlines; `style` is `label` or `heading`; `size=`, `weight=`, `colour=`, `text_anchor="middle"` override |
| `self.draw_label(canvas, rect, text=None)` | the top-left label at `theme.label.dx` / `dy`; `text` defaults to the `label` option |
| `self.draw_dots(canvas, rect, reserve=(), label=None)` | the page dot lattice inside `rect`, honouring the `dots:` option and keeping clear of the label per `theme.dots.reserve_label` |
| `self.draw_marker(canvas, box, marker=None)` | the checkbox marker centred in `box`, shape from the option or `theme.marker.shape` |
| `self.ctx.icons.get(name).place(canvas, box, colour, height=None, align=…, valign=…)` | an icon fitted into `box` |

Raw canvas calls, all in millimetres, attributes as keyword arguments with
underscores for hyphens (`stroke_width`, `stroke_dasharray`):

```python
canvas.rect(x, y, w, h, fill="none", stroke=..., stroke_width=...)
canvas.line(x1, y1, x2, y2, stroke=..., stroke_width=...)
canvas.circle(cx, cy, r, ...)
canvas.path("M 0 0 L 10 10", ...)
canvas.text(x, y, "string", font_family=..., font_size=..., fill=...)
canvas.open_group(**attrs); canvas.close_group()
```

## Measuring text

| helper | returns |
|---|---|
| `self.cap_height(style)` | cap height in mm for that style's size, read from the font |
| `self.cap_ratio(style)` | cap height as a fraction of the em |
| `self.text_width(text, size, style)` | advance width in mm, from the font's `hmtx` table |
| `self.label_band(rect, text=None)` | the `Rect` the top-left label occupies, or `None` |

Placing a baseline at `y_centre + self.cap_height("label") / 2` centres a
capital label on `y_centre`. That is how every built-in centres text in a
row.

## The context

`self.ctx` is the page's `RenderContext`:

| attribute | |
|---|---|
| `grid` | the module grid in mm |
| `default_gap` | the page's default gap |
| `dots` | the `DotGrid` (spacing, origin, radius, colour) |
| `page`, `content` | the page and content `Rect`s |
| `theme`, `icons` | the page theme and `IconSet` |
| `dot_points(rect, spacing=None, origin=None, inset=0, exclude=())` | lattice points strictly inside `rect` |
| `warn(message)` | emit a build warning |

Don't read `ctx.side` to decide how to draw. Mirroring is resolved before
your module runs, and a template is meant to work on either side unchanged.

## Sizing

- Return a height from `natural_height(width)` and a template can omit
  `height:`. The engine snaps it to the grid silently.
- Return `None` to make the module elastic — it behaves as `height: fill`.
- `natural_width(height)` does the same for children of a `row`.
- Do not snap your own result; the engine does.

## Containers

To lay out children of your own, look at `journalkit/modules/containers.py`.
A container builds its children with `journalkit.modules.build(spec, ctx)`,
solves them with `journalkit.layout.layout_stack` or `layout_row`, and
exposes a `_place(rect)` method returning `Placement`s so `journalkit check`
can walk into it.

## Registering

- Every `.py` in `modules/` whose name does not start with `_` is imported,
  in sorted order.
- A document can also list files under `modules:`; relative paths resolve
  against the document.
- A project module may **not** redefine a built-in name (`box`, `heading`,
  …); that raises. Two project files defining the same name is allowed and
  the later replaces the earlier, because two projects are routinely built in
  one process.
- Imports of `journalkit.…` work because the module runs inside JournalKit's
  process. Third-party imports need to be installed in the same environment
  as the `journalkit` package (`pipx inject journalkit <package>`).

## Documenting

`journalkit modules` prints each class's docstring and `params`, and marks
project modules with their file name.
