# Decorations

Decorations sit outside the content flow: a rule in the binding margin, a
year in the footer, a running head. Declare them for the document or for one
template. They draw under the content unless `above: true`.

```yaml
decorations:                  # every page
  - type: rule
    edge: inner
    offset: 4

templates:
  front:
    decorations:              # this template only, in addition
      - type: text
        text: "2026"
        at: {x: {from: outer, offset: 2}, y: {from: bottom, offset: 6}, width: 20, height: 5}
```

Any module type can be a decoration; `rule` and `text` are the useful ones.

## The `edge` shorthand

The most common decoration is a full-length rule beside an edge. `edge` plus
`offset` places one without spelling out a rectangle:

```yaml
  - {type: rule, edge: inner, offset: 4}    # vertical, 4 mm into the binding margin
  - {type: rule, edge: top,   offset: 1}    # horizontal, 1 mm below the page top
```

`inner`, `outer`, `left`, `right` and `center` produce a vertical rule the
full page height; `top` and `bottom` produce a horizontal one the full page
width. For `inner` and `outer`, the offset is measured *away from the text
block towards the page edge*, so the same declaration lands in the binding
margin on both a recto and a verso.

## Explicit placement with `at`

For anything else, give a rectangle. `x` and `y` are a number in page
millimetres or an anchor; `width` and `height` are a number, `full` (the page
dimension) or `content` (the content dimension).

```yaml
  - type: text
    text: WEEK
    above: true
    at:
      x: {from: content_right, offset: 0}
      y: {from: top, offset: 1}
      width: 20
      height: 4
```

| x anchors | measured from |
|---|---|
| `left`, `right`, `center` | the page edges and centre |
| `content_left`, `content_right`, `content_center` | the content rectangle |
| `inner`, `outer` | the binding-side and outer-side edges of the content rectangle, offset **towards the page edge** |

| y anchors | measured from |
|---|---|
| `top`, `bottom`, `middle` | the page |
| `content_top`, `content_bottom`, `content_middle` | the content rectangle |

`right`, `bottom` and the `*_right` / `*_bottom` anchors measure inwards, so a
positive offset always moves away from the named edge. Omitted coordinates
default to the content rectangle's origin; omitted extents run to its far
edge.

## Mirroring

`inner` and `outer` are the only anchors that know which side the page is.
Use them for anything that belongs to the spine or the thumb edge, and it
mirrors with the margins. Use `left` and `right` for something that must stay
put — a registration mark, say.
