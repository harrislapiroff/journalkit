"""Example of a project-local module type.

A YAML document picks this up with::

    modules:
      - ../custom/habits.py

after which ``type: habit_grid`` is available.  This file is the whole story
for adding a module: subclass, register, declare an intrinsic height, draw.
"""

from pagekit.geometry import Rect
from pagekit.modules import Module, register
from pagekit.units import mm


@register("habit_grid")
class HabitGrid(Module):
    """A habit tracker: one labelled row per habit, one checkbox per day.

    The checkbox is the same marker the daily's ``checklist`` ticks — drawn by
    ``Module.draw_marker`` — so a habit is crossed off exactly like a task.
    """

    params = {
        "habits": "list of row labels; a blank one gets a rule to write on",
        "columns": "number of day columns (default 7)",
        "headers": "optional list of column headings, e.g. [M, T, W, T, F, S, S]",
        "label_width": "width of the habit label gutter (default 25)",
        "row_height": "height of each habit row (default 5)",
        "row_gap": "gap between rows (default: the module grid)",
        "label_gap": "clearance between the label gutter and the first column "
                     "(default: the module grid)",
        "cell": "column width; defaults to filling the remaining width",
        "marker": "circle-slash | circle | square | none | icon:<name>",
        "marker_size": "marker diameter; defaults to the row height",
    }

    def _metrics(self, width):
        habits = self.opt("habits") or []
        columns = int(self.opt("columns", 7))
        label_width = self.length("label_width") or 25.0
        row_height = self.length("row_height") or 5.0
        row_gap = self.length("row_gap")
        if row_gap is None:
            # Same breathing room the checklist leaves between its rows, so
            # markers never touch the ones above and below them.
            row_gap = self.ctx.grid
        label_gap = self.length("label_gap")
        if label_gap is None:
            label_gap = self.ctx.grid
        cell = self.length("cell") or (width - label_width) / max(columns, 1)
        headers = self.opt("headers") or []
        return (habits, columns, label_width, row_height, row_gap, label_gap,
                cell, headers)

    def natural_height(self, width):
        habits, _, _, row_height, row_gap, _, _, headers = self._metrics(width)
        rows = len(habits) + (1 if headers else 0)
        return rows * row_height + max(rows - 1, 0) * row_gap

    def draw(self, canvas, rect):
        habits, columns, label_width, row_height, row_gap, label_gap, cell, headers = \
            self._metrics(rect.w)
        grid_x = rect.x + label_width
        marker = self.opt("marker", self.theme.get("marker.shape"))
        # Square by default, so the marker is as big as the row will take.
        marker_size = self.length("marker_size") or row_height
        y = rect.y

        if headers:
            for index, heading in enumerate(headers[:columns]):
                cell_rect = Rect(grid_x + index * cell, y, cell, row_height)
                self.text(canvas, cell_rect.cx, y + row_height - 1.4, heading,
                          style="label", text_anchor="middle")
            y += row_height + row_gap

        for habit in habits:
            label = Rect(rect.x, y, label_width, row_height)
            if habit:
                # Flush left — the gutter is the margin — and centred on the
                # row, so the habit reads level with the markers it belongs to.
                self.text(canvas, label.x,
                          label.cy + self.cap_height("label") / 2, habit, style="label")
            else:
                # A blank row is one to name yourself: give it a line to do it
                # on, stopping short of the grid so the two don't run together.
                canvas.line(label.x, label.bottom, label.right - label_gap, label.bottom,
                            stroke=self.stroke, stroke_width=self.stroke_width)
            for index in range(columns):
                box = Rect(grid_x + index * cell + (cell - marker_size) / 2, y,
                           marker_size, row_height)
                self.draw_marker(canvas, box, marker)
            y += row_height + row_gap
