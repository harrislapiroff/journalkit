# Theming

A theme is a nested mapping deep-merged over the defaults. Set it once for
the document, override it on a page, or override it on a single module.

```yaml
theme:                        # document-wide
  ink: "#000"
  font: {family: Montserrat}

templates:
  front:
    theme: {label: {size: 7pt}}          # this page only
    content:
      - type: box
        label: NOTES
        theme: {dots: {reserve_label: text}}   # this module only
```

The full list of keys and defaults is in the [theme reference](../reference/theme.md).

## One colour

Every colour role — strokes, label and heading text, dots, ruled lines —
defaults to `$theme.ink`. Recolour the whole document by setting `ink`:

```yaml
theme:
  ink: "#1a1a2e"
```

Pin any single role without disturbing the others. Softening the dot grid
relative to the text is the usual case:

```yaml
theme:
  ink: "#000"
  dots: {colour: "#999"}
```

Values can point at other values with `$theme.<path>`, and chains resolve. A
module option can point at the theme too: `stroke: $theme.dots.colour`.

```yaml
theme:
  accent: "#c8102e"
  heading: {colour: $theme.accent}
```

The default `ink` is `#231F20`, a rich black that prints a little softer than
`#000`. The page background and the white fill behind a checklist marker are
knockouts and deliberately not themed.

## Fonts

```yaml
theme:
  font:
    family: Montserrat
```

The font must be installed system-wide for two reasons: Inkscape embeds it in
the PDF, and journalkit reads its metrics from the font file to place
baselines and measure labels. If the file cannot be found, baselines fall
back to a cap-height ratio of 0.7 and label widths to a per-character
estimate. Read [fonts and baselines](../explanation/fonts.md) for what goes
wrong when the font is missing at PDF time, and run `journalkit doctor` to
confirm it is installed.

`cap_height` is read from the font's `OS/2` table by default. Set it to a
fraction of the em to override — for a font that publishes no cap height, or
to nudge every baseline at once.

## Text styles

Two styles: `label` (small text inside modules) and `heading`. Each has
`size`, `weight`, `colour` and `tracking`. Lengths take units:

```yaml
theme:
  label:   {size: 8pt,  weight: 500}
  heading: {size: 12pt, weight: 700, tracking: 0.1}
```

A label's baseline is `label.dy` below the module's top edge and its anchor
`label.dx` in from the left. The defaults centre an 8 pt cap in a 5 mm row;
if your rows are 6 mm, raise `dy` so the label recentres:

```yaml
theme:
  label: {dy: 4}
```

## Strokes and dots

```yaml
theme:
  stroke_width: 0.25pt      # every hairline
  dots:
    radius: 0.125
    opacity: 1.0
    reserve_label: band     # band | text | none — see below
    label_pad: 0.75
```

`reserve_label` decides what happens where dots would collide with a
module's label: `band` clears the label's whole line, `text` clears only
the label's measured width so dots continue to its right, `none` lets dots
run underneath. Dots are dropped, never shifted, so the survivors stay on
the lattice — see [dots and labels](../explanation/dots-and-labels.md).

## Markers

The checkbox drawn by `checklist` and `habit_grid`:

```yaml
theme:
  marker:
    shape: circle-slash     # circle-slash | circle | square | none | icon:<name>
    size: 5
```

`icon:<name>` uses an icon from your `icons/` or the built-in set as the
marker.
