# Icons

Icons are SVG files referenced by their file stem: `icon: sunrise` means
`sunrise.svg`. journalkit looks in, in order:

1. any directories a document lists under `icons:` (relative to the document);
2. the project's `icons/` directory;
3. the set shipped with journalkit.

Your own file wins over a built-in of the same name.

## The built-in set

| name | use |
|---|---|
| `sunrise`, `moon` | headings for morning and evening sections |
| `mood-1` … `mood-5` | a five-step scale, from worst to best |

`rating` builds a run of icons from a prefix and a count: `icon: mood,
count: 5` is `mood-1` through `mood-5`. Name your own scales the same way and
they work the same way.

## Requirements for your own SVG

Two, and both matter:

- **The `viewBox` must be a tight bounding box of the artwork.** journalkit
  scales and places icons by their `viewBox`; padding inside it becomes
  visible misalignment on the page.
- **Paths that should take the theme colour use `fill="currentColor"`.**
  Anything else keeps its own fill. White fills are preserved as knockouts.

The file is embedded as a `<g transform="translate(…) scale(…)">` wrapper
around the SVG body, so path data is never rewritten and the file stays
editable.

## Extracting from Illustrator or another editor

Export the object as plain SVG with the drawing area cropped to it, then run
the extraction helper from the repository, which computes the tight bounding
box from the path data and rewrites fills:

```sh
inkscape --pdf-poppler --export-type=svg --export-filename=raw.svg drawing.ai
inkscape --export-id=path42 --export-id-only --export-area-drawing \
         --export-plain-svg --export-filename=raw/sunrise.svg raw.svg
python3 tools/extract_icons.py raw/sunrise.svg -o my-journal/icons/
```

`tools/extract_icons.py` is in the source repository, not in the installed
package. The built-in set was produced this way, so it is a fair template
for what a finished icon file should look like.

## Sizing

- In a `heading`, the icon sits in a fixed-width box at the left
  (`theme.heading.icon_box`, 6 mm) and is drawn at
  `theme.heading.icon_height` (4.6 mm), so headings with and without icons
  share a text origin.
- In a `rating`, icons are drawn at `theme.rating.icon_size` (3 mm) with
  `theme.rating.icon_gap` between them, aligned to the right edge.
- As a marker (`marker: icon:<name>`), the icon fills the marker box.

A run of icons that must look optically equal should share a height, which
is why these sizes fix the height and let the width follow.
