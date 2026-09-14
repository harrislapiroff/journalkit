# The two grids

There are deliberately two grids, and they do different jobs.

| | module grid | dot lattice |
|---|---|---|
| default | 2.5 mm | 5 mm |
| anchored to | the page origin | the page origin plus `origin` |
| governs | where every module rectangle sits and how big it is | the printed dots inside modules |
| enforced by | the layout engine; `journalkit check` | nothing — it is sampled, not enforced |

## The module grid is a layout constraint

Every module's rectangle — position and size — is a multiple of the module
grid. Heights written in a template are snapped and warned about; a module's
intrinsic height is snapped silently, because no template could act on that
warning. Leftover space handed to `fill` modules is divided and rounded
*down* to the grid, with the remainder going to the last one, so a stack
ends exactly where its container does.

The consequence is that any two modules on a page, or on two pages, line up
with each other without anyone arranging it. A checklist's row edges sit on
the same lines as the box above it. That is the whole point.

The grid constrains the *placement*. What a module draws inside its own
rectangle is its business: `habit_grid` divides its width into seven columns
that are not on any grid, and that is correct. `journalkit check` therefore
drives the layout engine and inspects placements, rather than parsing the
SVG and complaining about every rectangle it finds.

## The dot lattice is a page-wide texture

Dots are the writing texture of the page. If each module positioned its own
dots relative to its own corner, a box that starts 2.5 mm lower than its
neighbour would have dots 2.5 mm out of phase with it, and on a printed
spread the eye catches that immediately.

So the lattice is anchored to the page: the set of points
`(origin.x + i·spacing, origin.y + j·spacing)` for all integers `i, j`. A
module with `dots: true` draws the points that fall strictly inside its
rectangle, and nothing else. Two boxes anywhere on the page sample the same
lattice. Two pages with the same `grid.dots` sample the same lattice. The
module never chooses a phase.

Choose `spacing` as a multiple of the module grid and `origin` half a step
off it, and a module edge never coincides with a dot row. The defaults —
2.5 mm grid, 5 mm dots at `[0, 2.5]` — do exactly that.

## Commensurability

Both grids are anchored to the page, and the content rectangle is defined
by margins from the page edges. For the content rectangle to sit on the
module grid:

- its left edge on a recto is `inner`, so `inner` must be a multiple of the
  grid;
- its left edge on a verso is `outer`, so `outer` must be too;
- its width is `page − inner − outer`, so the page width must be a multiple
  as well;
- the same for `top`, `bottom` and the page height.

The last condition is the one that bites, because page sizes are given.
105 mm is 42 × 2.5 and divides a 2.5 mm grid exactly; it is 52.5 × 2, so on a
2 mm grid one of the two horizontal margins must be odd and the verso's
content rectangle is 1 mm off the lattice. A5's 148 mm divides 2 but not 2.5.

You can accept this knowingly. Nothing breaks: the layout engine still snaps
every module *within* the content rectangle. But the dots on that side sit
1 mm nearer one border than the other, and the modules on the two sides of
a spread are 1 mm out of register with each other.

`journalkit check` treats the two situations differently on purpose. A
content rectangle off the lattice is the template author's choice, reported
as a note. A module placement off *its own content rectangle* is the layout
engine failing, reported as a failure. Checking placements relative to the
page's own offset is what keeps the second check meaningful on a page that
has given up the first. Do not "fix" the note by loosening the check.
