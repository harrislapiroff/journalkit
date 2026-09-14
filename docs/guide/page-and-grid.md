# Choosing a page and grid

The page, the margins and the grids need to agree with each other. Settle
them first; modules added afterwards line up on their own.

## Page size

A name or millimetres:

```yaml
page:
  size: a6                # 105 × 148
  # size: [105, 170]      # width, height
```

Names: `a4`, `a5`, `a6`, `a7`, `b6`, `letter`, `half-letter`, `pocket`
(89 × 140), `hobonichi-weeks` (95 × 188). See [units](../reference/units.md).

For a bound book, use the trimmed page size, not the sheet you print on.

## Margins

```yaml
page:
  margins:
    top: 2.5
    bottom: 7.5
    inner: 15          # binding side
    outer: 5
```

`inner` and `outer` are named by their relation to the spine. A template's
`side: right` or `side: left` decides which becomes left and right. Set
`left` and `right` instead to turn mirroring off. `margins: {all: 10}` sets
all four; named keys override it.

## The module grid

Every module's position and size snaps to it. 2.5 mm and 2 mm are both
reasonable; 2 mm gives finer control over row heights.

```yaml
grid:
  module: 2.5
```

A height you write that is off the grid is snapped, with a warning. A
module's own intrinsic height is snapped silently.

## The dot lattice

Dots are a separate, coarser grid, anchored to the page rather than to any
module, so dots in one box line up with dots in the next.

```yaml
grid:
  dots:
    spacing: 5
    origin: [0, 2.5]     # the lattice passes through x ≡ 0, y ≡ 2.5 (mm)
    radius: 0.125
```

Make `spacing` a multiple of `module` and put `origin` half a step off, so a
module edge never lands on a dot row. The defaults do this.

## Check they divide

Both grids are anchored to the page, so for the content rectangle to sit on
the module grid on both sides of a spread:

- `inner` must be a multiple of the grid (it is the left margin on a recto);
- `outer` must be too (it is the left margin on a verso);
- the page width must be as well, since the content width is
  `page − inner − outer`.

| page width | grid | |
|---|---|---|
| 105 mm | 2.5 | yes: 42 steps |
| 105 mm | 2 | no: 52.5 steps, one margin must be odd |
| 148 mm (a5) | 2 | yes: 74 steps |
| 148 mm (a5) | 2.5 | no: 59.2 steps |

If you accept a page that doesn't divide, one side's content rectangle sits
off the lattice. `journalkit check` reports that as a per-page note and
checks module placements relative to the rectangle, so a module that
actually drifts still fails. See [the two grids](../explanation/two-grids.md).

## Look

```sh
journalkit build --png --debug
```

Blue lines are the module grid; the pink dashed box is the content
rectangle. If its edges sit on blue lines on both a recto and a verso, the
page and grid agree.
