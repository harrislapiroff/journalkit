# Laying out a page

A template's `content` is a vertical stack. Each module gets the full
content width and a height decided as follows.

## Height

| `height` | meaning |
|---|---|
| a number (`20`, `"2cm"`) | fixed, snapped to the module grid with a warning if it was off |
| `fill` | absorb whatever is left after the fixed ones |
| omitted | the module's intrinsic height if it has one, otherwise `fill` |

Modules with an intrinsic height: `heading` (7.5 mm), `fields` (5 mm),
`rating` (5 mm), `checklist` and `habit_grid` (from their rows), and `text`,
`rule` and `spacer` (one grid step). `box`, `dotfield` and `lines` have none
and fill by default.

## Gaps

`defaults.gap` at the top of the document is the space between consecutive
modules. Any module can override the space *before itself* with `gap`:

```yaml
defaults:
  gap: 2.5

templates:
  front:
    content:
      - {type: heading, text: MORNING}
      - {type: rating, label: MOOD, icon: mood, count: 5, gap: 0}   # snug under the heading
      - {type: box, label: NOTES, height: fill}
      - {type: heading, text: EVENING, gap: 5}                       # a breath before the next section
```

The first module in a stack has no gap before it regardless.

## Several modules filling

When more than one module is `fill`, leftover space is shared by `flex`
weight (default 1). Shares are rounded *down* to the grid and the remainder
goes to the last filling module, so the stack always ends exactly on the
container's bottom edge.

```yaml
      - {type: box, label: MORNING, height: fill}
      - {type: box, label: AFTERNOON, height: fill}
      - {type: box, label: EVENING, height: fill, flex: 2}   # twice the others
```

## Columns

Nest a `row`. Its children size on `width` the same way a stack's size on
`height`: a number, `fill`, or omitted.

```yaml
      - type: row
        height: 30
        gap_between: 2.5
        content:
          - {type: box, label: LEFT, width: fill}
          - {type: box, label: RIGHT, width: 25}
```

A child shorter than the row is placed with `valign: top | middle | bottom`.
Put a `stack` inside a column to stack modules within it; nest as deep as you
like.

`gap_between` on a container is the default gap between *its* children;
`padding` insets the container before laying them out.

## Overflow

If fixed heights plus gaps exceed the available height you get a warning and
the excess runs off the bottom:

```
warning: daily: front: content overflows its container by 12.50mm (160.0 available, 172.5 needed)
```

Give something `fill` or trim a height. `--strict` makes this fatal, which is
useful in a script.

## Repeating pages

```yaml
pages:
  - {template: daily, repeat: 31}
```

renders `daily-01` … `daily-31`. A page entry may also override anything
the template set — `side`, `theme`, `margins`, `gap`, or even `content`:

```yaml
pages:
  - template: daily
  - {template: daily, side: left, name: daily-verso}
```

## Debugging a layout

`journalkit build --png --debug` overlays the module grid and the content
box. When a module is not where you expect, the overlay usually shows why:
a gap you forgot, a height that snapped, or a `fill` with nothing left to
fill.
