# Fonts and baselines

## Text is drawn as outlines

JournalKit reads glyph outlines from the font file and writes each label as
an SVG `<path>`. The SVG and the PDF contain no fonts and no text, only
shapes, so the output is the same on every machine.

The alternative, emitting SVG `<text>` and letting Inkscape set it, depends
on Inkscape finding the same font JournalKit measured. If it does not, it
substitutes another without saying so, and every baseline is slightly off.
Outlining removes the possibility.

## Baselines come from the cap height

SVG positions text by its baseline. To centre a capital label in a row you
need the height of a capital, which is a fraction of the font size and
differs between fonts (Montserrat publishes 0.700). JournalKit reads it from
the font's `OS/2` table and places baselines with it, so labels sit where
the theme's `label.dy` says regardless of size.

Advance widths come from the same file, and measure labels for
`dots.reserve_label: text`.

## What the reader does and doesn't do

`journalkit/fontmetrics.py` is a small parser for the sfnt tables that
matter: `head`, `hhea`, `hmtx`, `cmap`, `OS/2`, `loca`, `glyf`. It has no
dependencies.

- **TrueType outlines only.** CFF-flavoured OpenType keeps outlines in a
  different table, which is not read. For those fonts, metrics still work
  and text falls back to `<text>`; keep the font installed for the PDF.
- **No kerning.** GPOS is not applied. On short capital labels the
  difference is small; on longer mixed-case text it is visible. Since a
  plain sum of advances errs wide, label clearance for dots is never too
  narrow.
- **No hinting or shaping.** Combining marks and complex scripts are not
  handled beyond what `cmap` maps directly.

## Using another font

Set `theme.font.family`. JournalKit looks in the user and system font
directories and, where available, asks `fc-match`; a TrueType font found
there is outlined like the bundled one. `journalkit doctor` reports what was
found for each family a project uses, and `journalkit check` confirms the
finished PDF embeds nothing it should not.

`theme.font.outline: false` emits `<text>` for every font, for anyone who
wants editable text in the SVG and is happy to manage fonts themselves.
