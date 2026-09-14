# Theme

The complete default theme, from `journalkit/theme.py`. A document's `theme:`
is deep-merged over this; a template's `theme:` over that; a module's
`theme:` over that. Any string value of the form `$theme.<path>` is resolved
by looking up `<path>`, and chains resolve; a cycle is an error.

```yaml
ink: "#231F20"                 # the one colour every role below points at
stroke: $theme.ink
stroke_width: 0.25pt
fill: none

font:
  family: Montserrat           # Regular, Medium and Bold are bundled
  outline: true                # draw glyph outlines; false emits SVG <text>
  cap_height: null             # fraction of the em; null = read the font's OS/2 table
  avg_advance: 0.75            # em per character, used only when the font file can't be read

label:                         # small text inside modules
  size: 8pt
  weight: 500
  tracking: 0
  colour: $theme.ink
  dx: 1.8                      # text anchor, in from the module's left edge
  dy: 3.55                     # baseline, down from the module's top edge

heading:
  size: 12pt
  weight: 700
  tracking: 0
  colour: $theme.ink
  icon_box: 6.0                # fixed-width slot the icon sits in
  icon_height: 4.6             # drawn icon height
  icon_gap: 1.0                # between the icon box and the text

dots:
  radius: 0.125
  colour: $theme.ink
  opacity: 1.0
  reserve_label: band          # band | text | none
  label_pad: 0.75              # clearance around a label, for reserve_label

marker:                        # the checkbox in checklist and habit_grid
  shape: circle-slash          # circle-slash | circle | square | none | icon:<name>
  size: 5.0
  fill: "#ffffff"              # a knockout: deliberately not $theme.ink

checklist:
  marker_gap: 2.5              # between the marker and the writing box

rating:
  icon_size: 3.0
  icon_gap: 2.0
  pad_right: 1.5               # from the last icon to the row's right edge

lines:
  spacing: 5.0
  colour: $theme.ink
  opacity: 0.45
```

## Notes on particular keys

**`ink`** is the single value behind every colour. Set it to recolour a
document; set an individual role to pin just that role. You may add your own
keys (`accent: "#c00"`) and point roles at them.

**`font.family`** — Montserrat is bundled; any other family must be
installed on the machine that builds. journalkit reads the font file for
metrics and glyph outlines. `journalkit doctor` reports what it found.

**`font.outline`** — `true` draws every glyph as an SVG path, so the output
depends on no installed font. `false` emits `<text>` and leaves the font to
Inkscape. Fonts without TrueType outlines (CFF) fall back to `<text>`
regardless.

**`font.cap_height`** — `null` means read the true value from the font. If
the font publishes none, the fallback is 0.7. Set a number to override for
every style at once.

**`label.dx` / `label.dy`** place the label's baseline relative to the
module's top-left corner. The defaults centre an 8 pt cap optically in a
5 mm row. For 6 mm rows, `dy: 4` recentres it.

**`dots.reserve_label`** — where dots would collide with a label: `band`
drops every dot in the label's line across the module, `text` drops only
those under the label's measured width, `none` drops none. Dots are never
shifted.

**`marker.fill`** and the page background are white knockouts that mask
what is under them; they are not themed on purpose.

## Lengths

Any length accepts units: `8pt`, `0.25pt`, `1in`, `2cm`, `12px`, or a bare
number in millimetres. See [units](units.md).

## Where each key is read

| key | used by |
|---|---|
| `stroke`, `stroke_width` | every frame and rule |
| `label.*` | `box`, `fields`, `lines`, `checklist` labels, `habit_grid` labels and headers, `rating` label, `text` |
| `heading.*` | `heading`, `text` with `style: heading` |
| `dots.*` | any module with `dots: true`; `dots.colour`/`radius`/`opacity` also default `grid.dots` |
| `marker.*` | `checklist`, `habit_grid` |
| `checklist.marker_gap` | `checklist` |
| `rating.*` | `rating` |
| `lines.*` | `lines` |
