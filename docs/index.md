# journalkit

**Page templates for a printable, hand-bound journal.** You describe each page
as a list of modules in YAML — a dated header, a rating scale, a dotted notes
box, a checklist — and journalkit lays them out on a modular grid and renders
print-ready SVG and PDF.

```sh
pipx install https://github.com/harrislapiroff/journalkit/archive/refs/heads/main.tar.gz
journalkit init my-journal && cd my-journal
journalkit build --pdf
```

<div class="grid cards" markdown>

-   :material-school:{ .lg .middle } **Tutorial**

    ---

    Install, build a starter journal, add a page, write your first module.
    Start here if you have never used journalkit.

    [:octicons-arrow-right-24: Begin](tutorial/index.md)

-   :material-map-marker-path:{ .lg .middle } **Guides**

    ---

    Task-oriented recipes: pick a page size and grid, theme a document, add
    icons, put a rule in the binding margin, iterate with `watch`.

    [:octicons-arrow-right-24: Guides](guide/index.md)

-   :material-book-open-variant:{ .lg .middle } **Reference**

    ---

    Every command, every key in a document, every module parameter, every
    theme value, and the Python API.

    [:octicons-arrow-right-24: Reference](reference/index.md)

-   :material-lightbulb-on:{ .lg .middle } **Explanation**

    ---

    Why there are two grids, how mirroring works, why a missing font moves
    every baseline, and the principles behind the design.

    [:octicons-arrow-right-24: Explanation](explanation/index.md)

</div>

## What it does

A **document** is one YAML file: a page size, margins, a grid, a theme, and
one or more page **templates**, each a vertical stack of **modules**. Modules
are the building blocks — `box`, `heading`, `fields`, `checklist`, `lines`,
`rating`, `habit_grid` and a few more — and each snaps to the document's
module grid, so everything on the page lines up with everything else.

journalkit runs on a **project directory**: `templates/` for your documents,
optional `modules/` for your own module types in Python, optional `icons/`
for your own SVG artwork. `journalkit build` renders every document to SVG,
and with Inkscape installed, to a multi-page PDF ready for the printer.

```yaml title="templates/daily.yaml"
document: daily
page:
  size: [105, 170]
  margins: {top: 2.5, bottom: 7.5, inner: 15, outer: 5}
grid:
  module: 2.5
  dots: {spacing: 5, origin: [0, 2.5]}
templates:
  front:
    side: right
    content:
      - {type: fields, columns: [{label: DATE, width: 25}, {label: "LOC."}]}
      - {type: heading, text: MORNING, icon: sunrise}
      - {type: box, label: NOTES, height: fill, dots: true}
      - {type: checklist, rows: 3}
pages: [front]
```

## Requirements

- Python 3.10 or newer, and PyYAML (installed automatically).
- For PDF and PNG output: [Inkscape](https://inkscape.org) and, for
  multi-page documents, [Ghostscript](https://ghostscript.com). SVG output
  needs neither.
- The font your theme names, installed system-wide. The default is
  [Montserrat](https://fonts.google.com/specimen/Montserrat).

journalkit is released under the BSD 3-Clause License.
