# Units and page sizes

## Lengths

Every internal length is a float in millimetres, and one SVG user unit is
one millimetre. In YAML a length is either a bare number (millimetres) or a
string with a unit suffix:

| suffix | millimetres |
|---|---|
| `mm` | 1 |
| `cm` | 10 |
| `pt` | 25.4 / 72 ≈ 0.3528 |
| `in` | 25.4 |
| `px` | 25.4 / 96 ≈ 0.2646 |

```yaml
height: 20          # 20 mm
stroke_width: 0.25pt
size: 8pt
margins: {all: 1cm}
```

Whitespace between number and unit is allowed. Unknown units are an error
that names the valid ones. In Python, `journalkit.units.mm(value)` performs
the conversion.

## Snapping

`journalkit.units.snap(value, grid, mode)` rounds a length to a multiple of
`grid`; `mode` is `nearest` (default), `floor` or `ceil`. The layout engine
snaps every module's written height to nearest and warns; `fill` shares are
rounded down.

## Named page sizes

`page.size` accepts these names (case-insensitive), all width × height in
millimetres, portrait:

| name | size |
|---|---|
| `a4` | 210 × 297 |
| `a5` | 148 × 210 |
| `a6` | 105 × 148 |
| `a7` | 74 × 105 |
| `b6` | 125 × 176 |
| `letter` | 215.9 × 279.4 |
| `half-letter` | 139.7 × 215.9 |
| `pocket` | 89 × 140 |
| `hobonichi-weeks` | 95 × 188 |

For anything else, write `[width, height]` or `{width: …, height: …}`, with
units if you like: `size: [4in, 6in]`.

The default when `page.size` is omitted is `a5`.
