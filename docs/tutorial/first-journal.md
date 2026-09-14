# Your first journal

## Scaffold a project

journalkit runs on a *project directory*. Create one:

```sh
journalkit init my-journal
cd my-journal
```

```
wrote my-journal/README.md
wrote my-journal/modules/stamp.py
wrote my-journal/templates/daily.yaml

next: cd my-journal && journalkit build --png    # then open out/
```

Three files. `templates/daily.yaml` is a two-page document, `modules/stamp.py`
is a small custom module the template uses, and the README explains the
layout. Every directory in a project is optional except `templates/`.

## Build it

```sh
journalkit build --png
```

```
wrote /…/my-journal/out/daily-01-front.svg
wrote /…/my-journal/out/daily-02-back.svg
wrote /…/my-journal/out/daily-01-front.png
wrote /…/my-journal/out/daily-02-back.png
```

Open `out/daily-01-front.png`. You are looking at a recto page: a date and
location field row, a heading with an icon, a mood scale, a dotted notes box
that takes whatever height is left, three checklist rows, and a dashed frame
labelled *TODAY IN ONE PICTURE* — that last one is the `stamp` module from
`modules/stamp.py`.

Now `out/daily-02-back.png`. It is a verso: the wider binding margin has
moved to the right, and so has the hairline rule beside it. You did not write
that anywhere. The template says `side: left`, and journalkit mirrors the
margins.

## Read the template

Open `templates/daily.yaml`. Skim it top to bottom:

```yaml
document: daily            # (1)!

page:
  size: [105, 170]         # (2)!
  margins:
    top: 2.5
    bottom: 7.5
    inner: 15              # (3)!
    outer: 5

grid:
  module: 2.5              # (4)!
  dots:
    spacing: 5
    origin: [0, 2.5]

templates:
  front:
    side: right
    content:               # (5)!
      - type: fields
        columns: [{label: DATE, width: 25}, {label: "LOC."}]
      - type: heading
        text: MORNING
        icon: sunrise
      # …
pages:
  - template: front        # (6)!
  - template: back
```

1.  The document's name, used for output file names.
2.  Width and height in millimetres. Names like `a5` or `pocket` work too.
3.  `inner` is the binding side. On a recto it is the left margin; on a verso
    it is the right. That is all mirroring is.
4.  Every module snaps to this grid. The dot lattice is separate and coarser.
5.  A page is a vertical stack of modules, top to bottom.
6.  The pages to render, in order, each referring to a template.

Everything else in a document is optional. The
[document reference](../reference/document.md) lists every key.

## Change something

Make the notes box shorter and give the checklist more rows. In `front`,
change:

```yaml
      - type: box
        label: NOTES
        height: fill
        dots: true
      - type: checklist
        rows: 3
```

to:

```yaml
      - type: box
        label: NOTES
        height: fill
        dots: true
      - type: checklist
        rows: 6
```

Build again and look. The checklist grew; the notes box shrank by exactly the
same amount, because `height: fill` means *whatever is left*. The stack still
ends on the bottom margin.

Now try a height that is not on the grid:

```yaml
      - type: box
        label: NOTES
        height: 21
```

```
warning: daily: front: box: height 21.000mm is off the 2.500mm grid, snapped to 20.000mm
```

The build succeeded, the box is 20 mm, and you were told. Warnings go to
stderr with exit code 0; `--strict` turns them into failures. Put `fill`
back before moving on.

## Make a PDF

```sh
journalkit build --pdf
journalkit check
```

`out/daily.pdf` is the printable document, one page per template. `check`
proves two things you cannot see: every module landed on the grid, and the
PDF embeds the font the theme asked for rather than a silent substitute.

```
== module grid ==
daily / front                   2.5mm   6 placements, 0 off-grid
daily / back                    2.5mm   3 placements, 0 off-grid

9 placements checked; all on the 2.5mm grid

== embedded fonts ==
daily.pdf                    Montserrat-Bold, Montserrat-Medium

fonts ok
```

Next: [add a page of your own](add-a-page.md).
