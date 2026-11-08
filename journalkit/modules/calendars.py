"""Calendars: blank grids you date by hand.

``month_grid`` is a month you number yourself: day names above a frame,
weeks divided by full-width rules only. There are no vertical dividers
between days, so one note can run across several of them. Each day has a
small slot in its top-right corner for the date.

It is drawn for a landscape page (``orientation: landscape``), where seven
columns get the long side, but it works on a portrait page too.
"""

from ..geometry import Rect
from .base import Module, register

DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


@register("month_grid")
class MonthGrid(Module):
    """A blank month calendar: day names over a frame of week rows."""

    params = {
        "weeks": "number of week rows (default 5)",
        "headers": "day names, left to right (default MON..SUN)",
        "header_height": "height of the day-name row above the frame (default 2 module grids)",
        "number": "date slot in each day: corner (default) | box | tick | none",
        "number_size": "[width, height] of the date slot (default [6, 4])",
        "dots": "dot grid inside the week rows, kept off the rules and date slots",
    }

    def draw(self, canvas, rect):
        stroke = dict(stroke=self.stroke, stroke_width=self.stroke_width)
        line = dict(stroke_linecap="square", **stroke)

        weeks = max(int(self.opt("weeks", 5)), 1)
        headers = self.opt("headers") or DAYS
        columns = len(headers)
        header_h = self.length("header_height")
        if header_h is None:
            header_h = 2 * self.ctx.grid
        style = self.opt("number", "corner")
        num_w, num_h = (float(n) for n in self.opt("number_size", [6, 4]))
        col_w = rect.w / columns

        # Day names sit just above the frame, at each column's left edge.
        label_dx = self.theme.mm("label.dx")
        for index, name in enumerate(headers):
            self.text(canvas, rect.x + index * col_w + label_dx, rect.y + header_h - 1.0,
                      name, style="label")

        frame = Rect(rect.x, rect.y + header_h, rect.w, rect.h - header_h)
        row_h = frame.h / weeks
        canvas.rect(frame.x, frame.y, frame.w, frame.h, fill="none", **stroke)

        slots = []
        for week in range(weeks):
            y = frame.y + week * row_h
            if week:
                canvas.line(frame.x, y, frame.right, y, **line)
            for col in range(columns):
                right = frame.x + (col + 1) * col_w
                slot = Rect(right - num_w, y, num_w, num_h)
                slots.append(slot)
                if style == "none":
                    continue
                if col < columns - 1:   # the frame already draws the last one
                    canvas.line(right, y, right, slot.bottom, **line)
                if style in ("corner", "box"):
                    canvas.line(slot.x, slot.bottom, right, slot.bottom, **line)
                if style == "box":
                    canvas.line(slot.x, y, slot.x, slot.bottom, **line)

        if self.spec.get("dots"):
            # One band per week, held clear of the rules, with the date slots
            # knocked out; a dot touching a rule reads as a smudge.
            clear = 0.8
            exclude = [s.inset(-clear) for s in slots] if style != "none" else []
            for week in range(weeks):
                band = Rect(frame.x, frame.y + week * row_h + clear,
                            frame.w, row_h - 2 * clear)
                self.ctx.draw_dots(canvas, band, options=self.spec.get("dots"),
                                   exclude=exclude)
