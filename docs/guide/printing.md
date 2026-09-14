# Printing and checking

## Build the PDF

```sh
journalkit build --pdf
```

For each document, journalkit renders every page to SVG, has Inkscape
convert each to PDF with the fonts embedded, and has Ghostscript concatenate
them into `out/<document>.pdf`. A single-page document skips Ghostscript.

The PDF's page size is exactly the document's `page.size`. If your printer
wants a larger sheet with the page imposed on it, do that in your print
dialog or imposition tool; journalkit produces trimmed pages.

## Check it

```sh
journalkit check
```

```
== module grid ==
daily / front                   2.5mm   6 placements, 0 off-grid
daily / back                    2.5mm   3 placements, 0 off-grid

9 placements checked; all on the 2.5mm grid

== embedded fonts ==
daily.pdf                    Montserrat-Bold, Montserrat-Medium

fonts ok
```

Two checks, and both catch things you cannot see:

**Grid.** Every module placement, including children of `row` and `stack`,
is on the document's module grid. This drives the layout engine rather than
reading the SVG, so what a module draws *inside* its rect is not counted.
A page whose content rectangle is itself off the lattice (see
[the two grids](../explanation/two-grids.md)) gets a note, and its placements
are checked relative to it.

**Fonts.** Every `/BaseFont` embedded in each PDF is a subset of the family
the document's theme asked for. Inkscape substitutes a missing font
*silently* and exits 0, and because baselines are placed from the intended
font's cap height, a substituted page looks plausible with every label
shifted. This is the only cheap detection.

`check` exits non-zero on any failure, so it belongs in a script that builds
your journal:

```sh
journalkit build --pdf --strict && journalkit check
```

## Before sending to print

- Run `journalkit doctor` on the machine doing the build. It checks Inkscape,
  Ghostscript and every font family your templates name.
- Proof one page at print size. `journalkit build --png --dpi 300` gives a
  PNG you can print at 100% to check stroke weights; 0.25 pt hairlines are
  the default and reproduce well on a laser printer, but check yours.
- Transparent background: `--no-background` omits the white page fill, for
  imposing onto coloured stock in another tool.
- Repeated pages: `{template: daily, repeat: 31}` in `pages:` puts a month of
  dailies in one PDF.

## Output layout

```
out/
  daily-01-front.svg       one SVG per page: <document>-<nn>-<page>.svg
  daily-02-back.svg
  daily-01-front.png       with --png
  daily.pdf                with --pdf
  preview/                 from `journalkit preview`
```

`out/` is safe to delete; everything in it is regenerated. `-o DIR` writes
elsewhere.
