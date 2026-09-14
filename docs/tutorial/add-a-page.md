# Add a page

You will write a weekly overview from scratch: a header, a habit tracker,
and two columns of day boxes. Along the way you meet containers, `fill`
weights, and the debug overlay.

## Start a new document

Create `templates/weekly.yaml`:

```yaml
document: weekly

page:
  size: [105, 170]
  margins: {top: 2.5, bottom: 7.5, inner: 15, outer: 5}

grid:
  module: 2.5
  dots: {spacing: 5, origin: [0, 2.5]}

decorations:
  - {type: rule, edge: inner, offset: 5}

templates:
  plan:
    side: right
    content:
      - type: fields
        columns: [{label: WEEK OF}]
pages: [plan]
```

Build it with a live preview running so you can see each change:

```sh
journalkit watch --png
```

Leave that terminal open; it rebuilds on every save. Open `out/weekly-01-plan.png`
in a viewer that reloads on change.

## A heading and a habit grid

Add to `content`:

```yaml
      - type: heading
        text: HABITS
      - type: habit_grid
        headers: [M, T, W, T, F, S, S]
        habits: [Move, Read, "", ""]
        label_width: 35
        row_height: 5
```

Two named habits, then two blank rows. A blank habit gets a rule to write on
instead of a label. The grid works out its own height from the row count, so
you did not give it one.

## Two columns of days

A page's `content` is a stack. To put things side by side you nest a `row`,
and inside each column a `stack`:

```yaml
      - type: row
        height: fill
        gap: 5
        gap_between: 2.5
        content:
          - type: stack
            gap_between: 2.5
            content:
              - {type: box, label: MON, height: fill}
              - {type: box, label: WED, height: fill}
              - {type: box, label: FRI, height: fill}
          - type: stack
            gap_between: 2.5
            content:
              - {type: box, label: TUE, height: fill}
              - {type: box, label: THU, height: fill}
              - {type: box, label: "SAT / SUN", height: fill}
```

Save and look. The row takes all the remaining height (`height: fill`) and
sits 5 mm below the habit grid (`gap` is the space *before* a module).
Inside it two stacks split the width equally, and inside each stack three
boxes split the height equally. Every edge is on the 2.5 mm grid, and the
bottom of the last box is exactly the bottom margin.

Give the weekend more room by weighting its `fill`:

```yaml
              - {type: box, label: "SAT / SUN", height: fill, flex: 2}
```

`flex` is the relative share of leftover space among siblings that fill. The
weekend box is now twice the height of TUE and THU. Leftover space is divided
by weight and rounded *down* to the grid, with the remainder going to the last
filling child, so the column still ends on the margin.

## See the grid

Stop `watch` (Ctrl-C) and build once with the overlay:

```sh
journalkit build templates/weekly.yaml --png --debug
```

Blue lines are the module grid; the pink dashed rectangle is the content
area. Every module edge sits on a blue line. That is the property `journalkit
check` asserts without drawing anything.

## The verso

Add a second template and page:

```yaml
templates:
  plan:
    # …
  notes:
    side: left
    content:
      - type: heading
        text: NOTES
      - type: lines
        height: fill
        spacing: 7.5
pages: [plan, notes]
```

Build. On `weekly-02-notes.png` the binding margin and the rule have moved
to the right edge. Ruled lines are 7.5 mm apart — three grid steps — so they
line up with anything else on the page.

You now have a two-document project. `journalkit build` with no arguments
renders both. Next: [write a module](write-a-module.md).
