"""A project-local module type.

Every ``.py`` file in a project's ``modules/`` directory is imported before a
build, so the ``@register`` decorator below is all it takes to make
``type: stamp`` available in the templates next door. A module is one class:
subclass ``Module``, register a name, declare an intrinsic height (or return
``None`` to mean "elastic"), and draw into the rect the layout engine hands
you — already snapped to the module grid.

Run ``journalkit modules`` to see this listed alongside the built-ins.
"""

from journalkit.modules import Module, register


@register("stamp")
class Stamp(Module):
    """A dashed frame to stick a photo or a ticket in."""

    params = {
        "label": "text drawn in the corner",
        "dash": "dash pattern, in mm (default '1 1')",
        "dots": "true to fill the frame with the page's dot lattice",
    }

    def natural_height(self, width):
        # A sensible default when the template gives no height. Returning
        # a value that is not on the grid is fine: it is snapped silently.
        return 40.0

    def draw(self, canvas, rect):
        canvas.rect(rect.x, rect.y, rect.w, rect.h, fill="none",
                    stroke=self.stroke, stroke_width=self.stroke_width,
                    stroke_dasharray=self.opt("dash", "1 1"))
        self.draw_label(canvas, rect)     # honours theme.label and dots.reserve_label
        self.draw_dots(canvas, rect)      # draws nothing unless `dots: true`
