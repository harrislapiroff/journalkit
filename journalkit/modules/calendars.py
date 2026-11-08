"""Calendars: blank grids you date by hand.

``month_grid`` is a month you number yourself: day names above a frame,
weeks divided by full-width rules only. There are no vertical dividers
between days, so one note can run across several of them. Each day has a
small slot in its top-right corner for the date.

It is drawn for a landscape page (``orientation: landscape``), where seven
columns get the long side, but it works on a portrait page too.
"""

from ..geometry import Rect
from ..units import mm
from .base import Module, register

DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
NUMBER_STYLES = ("corner", "box", "tick", "none")


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
        if not isinstance(headers, (list, tuple)):
            raise ValueError("month_grid: headers must be a list of day names, got %r"
                             % (headers,))
        columns = len(headers)
        header_h = self.length("header_height")
        if header_h is None:
            header_h = 2 * self.ctx.grid
        header_h = min(max(header_h, 0.0), rect.h)
        style = self.opt("number", "corner")
        if style not in NUMBER_STYLES:
            raise ValueError("month_grid: unknown number style %r (known: %s)"
                             % (style, ", ".join(NUMBER_STYLES)))
        size = self.opt("number_size", [6, 4])
        num_w, num_h = (mm(self.theme.resolve(n)) for n in size)
        col_w = rect.w / columns

        # Day names sit just above the frame, at each column's left edge,
        # with their baseline a little clear of it. A zero-height header row
        # means no day names at all.
        if header_h > 0:
            label_dx = self.theme.mm("label.dx")
            baseline = rect.y + header_h - min(1.0, header_h / 4)
            for index, name in enumerate(headers):
                self.text(canvas, rect.x + index * col_w + label_dx, baseline,
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
            # One band per week, held clear of every rule and the frame, with
            # that week's date slots knocked out; a dot touching a line reads
            # as a smudge.
            clear = 0.8
            for week in range(weeks):
                band = Rect(frame.x, frame.y + week * row_h, frame.w, row_h).inset(clear)
                week_slots = slots[week * columns:(week + 1) * columns]
                exclude = [s.inset(-clear) for s in week_slots] if style != "none" else []
                self.ctx.draw_dots(canvas, band, options=self.spec.get("dots"),
                                   exclude=exclude)
