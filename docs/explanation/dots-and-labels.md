# Dots and labels

A dotted box with a label in its corner has a problem: some dots fall in the
label's ink. On screen the text covers them; on a printed page a dot behind
a letter reads as a smudge. journalkit resolves this by not drawing those
dots, and the way it decides *which* dots is a small design decision worth
explaining.

## Drop, never shift

The obvious fix is to start the dot grid below the label. That moves the
whole grid inside the module, and now this box's dots are out of phase with
the box beside it. The lattice is anchored to the page precisely so that
never happens (see [the two grids](two-grids.md)).

So dots are **dropped**, never shifted. The module computes the rectangle
the label occupies — its *band* — and omits every lattice point that falls
inside it. Every surviving dot is exactly where it would have been. The
grid looks like it continues under the label and simply is not printed
there.

## Three modes

`theme.dots.reserve_label` chooses how wide the band is:

| mode | band | effect |
|---|---|---|
| `band` (default) | the label's line, the full width of the module | the grid starts cleanly below the title |
| `text` | the label's measured width plus `label_pad` | dots continue to the right of the label |
| `none` | nothing | dots run under the label |

`band` is the calmer look and the safe default. `text` suits a page where
labels are short and the writing area is wanted right up to the top edge; it
depends on measuring the label from the font file, which is why
[fonts](fonts.md) matter here too. If the font cannot be read, the width is
estimated and the band may be a little too narrow for wide letters or too
wide for narrow ones.

## The band is only as tall as it must be

The band runs from `label_pad` above the cap height to `label_pad` below the
baseline, or a little further to allow for descenders. A label that already
clears the first dot row costs no dots at all — the test suite asserts this
— so a theme with a slightly larger `label.dy` may lose nothing.

## Multi-cell modules

`fields` has one label per cell and reserves a band per cell. `checklist`
with `labels:` reserves per row. A module you write gets the same behaviour
by passing `reserve=[...]` or `label=` to `Module.draw_dots`.
