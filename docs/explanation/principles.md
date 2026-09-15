# Design principles

Each of these is enforced by the code or asserted by a test.

**Millimetres everywhere.** Every internal length is a float in millimetres
and one SVG user unit is one millimetre. YAML may carry units; they are
converted once, on the way in. Nothing else ever thinks about points or
pixels.

**Modules snap; what they draw is theirs.** The layout engine places every
module on the module grid. Inside its rectangle a module draws what it
likes. `journalkit check` tests the first and ignores the second.

**Both grids are page-anchored.** The module grid and the dot lattice are
defined from the page origin, so alignment across modules and across pages
is automatic rather than arranged. A module never chooses a phase.

**Mirroring happens once.** `inner` and `outer` margins become left and
right when the content rectangle is computed. No module branches on the
side.

**Text is drawn from the font file.** Glyph outlines, cap heights and
advance widths are read directly, so the output does not depend on the
machine that renders it.

**Dots are dropped, never shifted.** Where a dot would collide with a label
it is omitted; the survivors stay on the lattice.

**One colour, many roles.** Every colour defaults to `$theme.ink`. Any role
can be pinned. Knockouts stay white.

**Warnings are loud and non-fatal.** A snapped height or an overflow is
printed to stderr and the build succeeds, because the output is still
useful for looking at. `--strict` is there for scripts. Only sizes the
author wrote are worth warning about; intrinsic sizes snap silently.

**A template is written once.** It works on a recto and a verso, in any
project, with any theme.

