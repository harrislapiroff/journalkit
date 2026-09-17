# Theming

A theme is a nested mapping merged over the defaults, at the document, page
or module level:

```yaml
theme:                        # document-wide
  ink: "#000"

templates:
  front:
    theme: {label: {size: 7pt}}          # this page
    content:
      - type: box
        label: NOTES
        theme: {dots: {reserve_label: text}}   # this module
```

The [theme reference](../reference/theme.md) lists every key and default.

## Colour

Every colour role defaults to `$theme.ink`, so one value recolours the
document:

```yaml
theme:
  ink: "#1a1a2e"
```

Pin a single role to change just that one; softening the dots is the usual
case:

```yaml
theme:
  ink: "#000"
  dots: {colour: "#999"}
```

Any value can point at another with `$theme.<path>`, including a module
option: `stroke: $theme.dots.colour`.

The default `ink`, `#231F20`, prints a little softer than `#000`. The page
background and the white behind a checklist marker are knockouts and stay
white.

## Fonts

Text is drawn as glyph outlines read from the font file. Montserrat
Regular, Medium and Bold ship with JournalKit (SIL Open Font License); the
default theme uses weights 500 and 700.

To use another font, name it and have it installed on the machine that
builds:

```yaml
theme:
  font:
    family: Source Sans 3
```

JournalKit finds the file in the usual font directories and outlines from
it the same way. `journalkit doctor` reports whether each family a project
uses was found. Two caveats:

- Only TrueType outlines (`glyf`) are read. For a CFF-flavoured OpenType
  font, JournalKit still reads the metrics but emits SVG `<text>`, and
  Inkscape then needs the font installed to make the PDF.
- Kerning is not applied. On short capital labels this is hard to see; on a
  long line of mixed-case text you may notice it.

`font.outline: false` emits `<text>` for every font, if you want editable
text in the SVG. `font.cap_height` overrides the cap height read from the
font, as a fraction of the em.

## Text styles

`label` (small text inside modules) and `heading`, each with `size`,
`weight`, `colour`, `tracking`:

```yaml
theme:
  label:   {size: 8pt,  weight: 500}
  heading: {size: 12pt, weight: 700}
```

A label's baseline is `label.dy` below the module's top edge. The default
centres an 8 pt capital in a 5 mm row; for 6 mm rows, `dy: 4`.

## Strokes, dots, markers

```yaml
theme:
  stroke_width: 0.25pt
  dots:
    radius: 0.125
    reserve_label: band     # band | text | none
  marker:
    shape: circle-slash     # circle-slash | circle | square | none | icon:<name>
    size: 5
```

`reserve_label` decides what happens where dots would fall under a label:
`band` clears the label's whole line, `text` clears only the label's width,
`none` leaves them. See [dots and labels](../explanation/dots-and-labels.md).
