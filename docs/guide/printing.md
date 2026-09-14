# Printing and checking

## The PDF

```sh
journalkit build --pdf
```

Each page is rendered to SVG, converted to PDF by Inkscape, and the pages
joined by Ghostscript into `out/<document>.pdf`. A single-page document
skips Ghostscript.

The PDF page size is the document's `page.size`: trimmed pages. Imposing
them onto a larger sheet is a job for the print dialog or an imposition
tool.

## Check

```sh
journalkit check
```

```
== module grid ==
daily / front                   2.5mm   6 placements, 0 off-grid
daily / back                    2.5mm   3 placements, 0 off-grid

9 placements checked; all on the 2.5mm grid

== embedded fonts ==
daily.pdf                    text outlined, no fonts embedded

fonts ok
```

**Grid**: every module placement, including children of `row` and `stack`,
is on the document's module grid. What a module draws inside its rectangle
isn't counted. A page whose content rectangle is itself off the lattice gets
a note and its placements are checked relative to it.

**Fonts**: text is drawn as outlines, so a correct PDF embeds no fonts. If a
font does appear, an SVG `<text>` got through and Inkscape set it in
whatever it had; with `font.outline: false` the check instead asserts that
only the theme's family is embedded.

`check` exits non-zero on a failure, so in a script:

```sh
journalkit build --pdf --strict && journalkit check
```

## Before printing

- `journalkit doctor` on the machine doing the build: Inkscape, Ghostscript,
  and whether each font the templates name was found.
- Proof one page at 100% from `journalkit build --png --dpi 300` to check
  stroke weights on your printer. The default hairline is 0.25 pt.
- `--no-background` omits the white page fill, for imposing onto coloured
  stock elsewhere.
- `{template: daily, repeat: 31}` under `pages:` puts a month of dailies in
  one PDF.

## Output

```
out/
  daily-01-front.svg       <document>-<nn>-<page>.svg
  daily-01-front.png       with --png
  daily.pdf                with --pdf
  preview/                 from journalkit preview
```

Everything in `out/` is regenerated; delete it freely. `-o DIR` writes
elsewhere.
