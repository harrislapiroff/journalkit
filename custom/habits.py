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
    """A habit tracker: one labelled row per habit, one cell per day."""

    params = {
        "habits": "list of row labels",
        "columns": "number of day columns (default 7)",
        "headers": "optional list of column headings, e.g. [M, T, W, T, F, S, S]",
        "label_width": "width of the habit label gutter (default 25)",
        "row_height": "height of each habit row (default 5)",
        "cell": "cell width; defaults to filling the remaining width",
    }

    def _metrics(self, width):
        habits = self.opt("habits") or []
        columns = int(self.opt("columns", 7))
        label_width = self.length("label_width") or 25.0
        row_height = self.length("row_height") or 5.0
        cell = self.length("cell") or (width - label_width) / max(columns, 1)
        headers = self.opt("headers") or []
        return habits, columns, label_width, row_height, cell, headers

    def natural_height(self, width):
        habits, _, _, row_height, _, headers = self._metrics(width)
        return (len(habits) + (1 if headers else 0)) * row_height

    def draw(self, canvas, rect):
        habits, columns, label_width, row_height, cell, headers = self._metrics(rect.w)
        grid_x = rect.x + label_width
        y = rect.y

        if headers:
            for index, heading in enumerate(headers[:columns]):
                cell_rect = Rect(grid_x + index * cell, y, cell, row_height)
                self.text(canvas, cell_rect.cx, y + row_height - 1.4, heading,
                          style="label", text_anchor="middle")
            y += row_height

        for habit in habits:
            row = Rect(rect.x, y, label_width + columns * cell, row_height)
            self.draw_label(canvas, Rect(rect.x, y, label_width, row_height), habit)
            for index in range(columns):
                canvas.rect(grid_x + index * cell, y, cell, row_height,
                            fill="none", stroke=self.stroke, stroke_width=self.stroke_width)
            canvas.line(row.x, row.bottom, grid_x, row.bottom,
                        stroke=self.stroke, stroke_width=self.stroke_width)
            y += row_height
