# Choosing a page and grid

The page, the margins and the two grids have to agree with each other. Get
this right first and every module you add afterwards will line up for free.

## Page size

Either a name or explicit millimetres:

```yaml
page:
  size: a6                # 105 × 148
  # size: [105, 170]      # width, height
  # size: {width: 105, height: 170}
```

Named sizes: `a4`, `a5`, `a6`, `a7`, `b6`, `letter`, `half-letter`,
`pocket` (89 × 140), `hobonichi-weeks` (95 × 188). See
[units and page sizes](../reference/units.md) for the numbers.

For a hand-bound book, measure the *trimmed* page, not the sheet you print
on. If you print two-up and cut, the page size here is the size after
cutting.

## Margins

```yaml
page:
  margins:
    top: 2.5
    bottom: 7.5
    inner: 15          # binding side
    outer: 5
```

`inner` and `outer` are named by their relationship to the spine, not by left
and right. A template says `side: right` (recto) or `side: left` (verso), and
the margins mirror. Write the template once; it is correct on both sides.

Set `left` and `right` explicitly instead if you do not want mirroring — a
single-sided card, say.

`margins: {all: 10}` sets all four at once; named keys override it.

## The module grid

Every module's rectangle snaps to the module grid — its position and its
size. Pick a step that divides your common dimensions nicely. 2.5 mm and
2 mm are both good choices; 2.5 mm gives a coarser, calmer page, 2 mm gives
finer control over row heights.

```yaml
grid:
  module: 2.5
```

Heights you write that are not multiples of the grid are snapped, with a
warning. A module's own intrinsic height (a heading's 7.5 mm) is snapped
silently.

## The dot lattice

Dots are a separate, usually coarser grid. It is anchored to the page — not
to any module — so dots in one box line up with dots in the next box and on
the next page.

```yaml
grid:
  dots:
    spacing: 5
    origin: [0, 2.5]     # the lattice passes through x ≡ 0, y ≡ 2.5 (mm)
    radius: 0.125
```

Make `spacing` a multiple of `module`, so module edges can land *between*
dot rows rather than on them. With a 2.5 mm module grid and 5 mm dots, an
`origin` of `[0, 2.5]` puts dot rows halfway between grid lines: a box whose
top edge is on the grid never has a dot sitting on its border.

## Make them commensurate

Here is the constraint that trips people up. Both grids are anchored to the
**page**, and mirroring means:

- on a recto the content starts at `inner`, so `inner` must be a multiple of
  the module grid;
- on a verso it starts at `outer`, so `outer` must be too;
- the content width is `page − inner − outer`, so the **page width** must be
  a multiple as well.

Do the arithmetic before you commit. Some examples:

| page width | grid | works? |
|---|---|---|
| 105 mm | 2.5 | yes — 42 steps |
| 105 mm | 2 | no — 52.5 steps; one margin must be odd |
| 148 mm (a5) | 2 | yes — 74 steps |
| 148 mm (a5) | 2.5 | no — 59.2 steps |
| 95 mm | 2.5 | yes — 38 steps |

If you knowingly choose a page that does not divide, one side's content
rectangle sits off the lattice and `journalkit check` reports it as a
per-page **note**, not a failure. Placements are then checked *relative to*
that rectangle, so a module that genuinely drifts still fails. The
[two grids](../explanation/two-grids.md) explanation has the full reasoning.

## Check it

```sh
journalkit build --png --debug
```

The blue overlay is the module grid; the pink dashed box is the content
rectangle. If the pink box's edges sit on blue lines on **both** a recto and a
verso, your page and grid agree.
