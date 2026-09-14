# Fonts and baselines

Text in journalkit is positioned from the font's **cap height**, and the
cap height is read from the font file on the machine doing the build. This
is why the font matters more than it usually does in a layout tool, and why
a missing font is the one failure that looks like success.

## How a baseline is placed

SVG positions text by its baseline. To centre a capital-letter label
vertically in a 5 mm row, you need to know how tall a capital is: the
baseline goes at `row_centre + cap_height / 2`. Cap height is a fraction of
the font size — around 0.7 em for most sans-serifs, but 0.66 for some and
0.73 for others — and the fraction is published in the font's `OS/2` table.

`journalkit/fontmetrics.py` is a small reader for that table and for the
advance widths in `hmtx`/`cmap`. It needs no font library; it finds the
installed file for the family and weight the theme names, and reads two
numbers out of it. Every built-in that places text uses
`Module.cap_height(style)`, so every baseline on the page is derived from the
real font.

If the file cannot be found, the fallback is a cap ratio of 0.7 and a label
width estimate of 0.75 em per character. That is a safety net, not a
substitute: real capitals range from 0.5 em (`I`) to over 0.9 em (`M`, `W`),
so the estimate under-reserves for wide words and over-reserves for long
ones. Set `theme.font.cap_height` explicitly to override either way.

## Why a missing font is dangerous at PDF time

Inkscape converts the SVG to PDF and embeds fonts. If the family named in the
SVG is not installed, Inkscape **substitutes another font, prints no
warning, and exits 0**. The PDF opens, the text is legible, the page looks
plausible.

But journalkit placed every baseline using the intended font's cap height,
and the substitute has a different one. Every label is a fraction of a
millimetre off-centre in its row; every heading is slightly high or low
against its icon. It is the kind of error you notice only after a book is
bound.

Two defences:

- `journalkit doctor` checks that every font family your templates name is
  installed, before you build.
- `journalkit check` reads every `/BaseFont` name embedded in the finished
  PDF and asserts each is a subset of the family the document's theme asked
  for. This is cheap, needs no PDF library, and is the only reliable
  detection. Run it after any PDF build you intend to print.

## Measuring labels

The same font reader gives advance widths, which is what makes
`theme.dots.reserve_label: text` work: dots are cleared from exactly the
width the label occupies, measured from the font, rather than from a guess.
The [dots and labels](dots-and-labels.md) page explains what that clearance
is for.

## Choosing a font

Anything installed system-wide works; set `theme.font.family`. journalkit
looks in the usual system and user font directories and, if available, asks
`fc-list`. Fonts with several weights should have the weights you use
installed (`label.weight` 500 and `heading.weight` 700 by default), since
each weight is a separate file with its own metrics.
