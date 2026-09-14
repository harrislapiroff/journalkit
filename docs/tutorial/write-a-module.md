# Write a module

The built-in modules cover the common furniture of a journal page. When you
want something they do not draw, a module is one Python class in your
project's `modules/` directory. This walk-through writes a **timeline**: a
vertical rule with hour marks down the left of a box, for a day plan.

## The shape of a module

Open `modules/stamp.py`, which `journalkit init` wrote for you. Stripped of
comments it is:

```python
from journalkit.modules import Module, register

@register("stamp")
class Stamp(Module):
    """A dashed frame to stick a photo or a ticket in."""

    params = {"label": "text drawn in the corner"}

    def natural_height(self, width):
        return 40.0

    def draw(self, canvas, rect):
        canvas.rect(rect.x, rect.y, rect.w, rect.h, fill="none",
                    stroke=self.stroke, stroke_width=self.stroke_width,
                    stroke_dasharray=self.opt("dash", "1 1"))
        self.draw_label(canvas, rect)
        self.draw_dots(canvas, rect)
```

Four parts:

- `@register("stamp")` makes `type: stamp` available in YAML. Every `.py` in
  `modules/` is imported before a build, so nothing else is needed.
- `params` documents the options for `journalkit modules`. It is
  documentation only.
- `natural_height` is the module's intrinsic height in millimetres when the
  template gives none. Return `None` to mean "no opinion", which makes the
  module behave as `fill`.
- `draw` receives a `Canvas` and a `Rect` that is already snapped to the grid.
  Everything you draw is in page millimetres.

## Write the timeline

Create `modules/timeline.py`:

```python
"""A day plan: hour labels down a vertical rule, writing space to the right."""

from journalkit.modules import Module, register


@register("timeline")
class Timeline(Module):
    """Hour marks down the left edge with a writing area beside them."""

    params = {
        "start": "first hour (default 8)",
        "end": "last hour (default 20)",
        "gutter": "width of the hour-label gutter in mm (default 10)",
        "dots": "true to fill the writing area with the dot lattice",
    }

    def _hours(self):
        return range(int(self.opt("start", 8)), int(self.opt("end", 20)) + 1)

    def natural_height(self, width):
        # One grid step per hour keeps every mark on the lattice.
        return len(self._hours()) * self.ctx.grid * 2

    def draw(self, canvas, rect):
        gutter = self.length("gutter") or 10.0
        hours = list(self._hours())
        step = rect.h / len(hours)
        axis_x = rect.x + gutter

        canvas.line(axis_x, rect.y, axis_x, rect.bottom,
                    stroke=self.stroke, stroke_width=self.stroke_width)
        for index, hour in enumerate(hours):
            y = rect.y + index * step
            canvas.line(axis_x - 1.0, y, axis_x + 1.0, y,
                        stroke=self.stroke, stroke_width=self.stroke_width)
            # Baseline placed from the cap height, so the label centres on the tick.
            self.text(canvas, axis_x - 2.0, y + self.cap_height("label") / 2,
                      "%02d" % hour, style="label", text_anchor="end")

        if self.opt("dots"):
            from journalkit.geometry import Rect
            self.draw_dots(canvas, Rect(axis_x, rect.y, rect.right - axis_x, rect.h))
```

Points worth noticing:

- `self.opt(key, default)` reads a YAML option and expands any
  `$theme.…` reference. `self.length(key)` does the same and converts a
  length with units to millimetres.
- `self.stroke` and `self.stroke_width` come from the theme unless the
  module's YAML overrides them.
- `self.text(...)` draws in the theme's `label` style. Baselines are placed
  from `self.cap_height("label")`, which is read from the font file, so the
  label is optically centred on its tick.
- `self.draw_dots(...)` samples the *page's* dot lattice inside whatever rect
  you hand it. The dots line up with every other dotted module on the page
  because the lattice is anchored to the page, not to your module.
- `self.ctx.grid` is the document's module grid, if you want your internal
  geometry to sit on it too. Nothing forces that: the invariant is about the
  module's *placement*, not what it draws inside.

## Use it

Check it is registered:

```sh
journalkit modules | grep -A4 '^timeline'
```

```
timeline — Hour marks down the left edge with a writing area beside them.  [timeline.py]
      start          first hour (default 8)
      end            last hour (default 20)
      …
```

Try it without touching a template:

```sh
echo '- {type: heading, text: TODAY}
- {type: timeline, start: 7, end: 19, dots: true}' | journalkit preview
```

```
wrote /…/out/preview/preview-01-preview.png
```

Then put it on a page:

```yaml
      - type: timeline
        start: 7
        end: 21
        height: fill
        dots: true
```

With `height: fill` the module stretches and the hour spacing adapts; without
it, `natural_height` decides.

## What to read next

- The [custom modules guide](../guide/custom-modules.md) covers the rest of
  the `Module` API: markers, label bands, icons, per-module theme overrides,
  and how containers lay out children.
- The [Python API reference](../reference/python-api.md) lists every helper.
