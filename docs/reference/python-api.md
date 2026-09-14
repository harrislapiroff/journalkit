# Python API

Everything the command does is available from Python, and custom modules
use the same objects.

```python
from journalkit import spec
from journalkit.render import Renderer

document = spec.load("my-journal/templates/daily.yaml")
for name, svg in Renderer(document).render_all():
    print(name, len(svg))
```

The API is stable within a minor version. Names beginning with `_` are
private.

## `journalkit.spec`

`load(path, project=None) -> Document`
:   Read a YAML document. `project` is a `Project`; when omitted it is
    located from the file's position. Raises `ValueError` for a malformed
    document, `FileNotFoundError` for a missing module file.

`Document`
:   Fields: `name`, `width`, `height`, `margins: Margins`, `grid: float`,
    `dots: DotGrid`, `theme: Theme`, `default_gap`, `decorations: list`,
    `pages: list[PageSpec]`, `icon_dirs: list[Path]`, `source: Path`,
    `project: Project`. Property `size -> (width, height)`.

`PageSpec`
:   Fields: `name`, `side`, `content`, `decorations`, `theme`, `margins`,
    `gap`.

`Margins`
:   `parse(mapping) -> Margins`; `for_side(side) -> (top, right, bottom, left)`.

`DotGrid`
:   Fields `spacing`, `origin`, `radius`, `colour`, `opacity`, `inset`.

`PAGE_SIZES`, `DEFAULT_MARGINS`, `BUILTIN_ICONS`
:   The named sizes, default margins, and the packaged icon directory.

## `journalkit.render`

`Renderer(document, debug=False, background="#ffffff")`
:   `render_all() -> list[(page_name, svg_text)]`;
    `render_page(page_spec) -> (Canvas, RenderContext)`;
    `content_rect(page_spec) -> (page: Rect, content: Rect)`;
    `warnings: list[str]` accumulated across pages; `icons: IconSet`.

`RenderContext`
:   What a module sees beyond its spec: `theme`, `icons`, `grid`,
    `default_gap`, `dots`, `page`, `content`, `side`, `debug`, `warnings`.
    Methods `warn(message)`, `dot_points(rect, spacing=None, origin=None,
    inset=0.0, exclude=())`, `draw_dots(canvas, rect, options=None,
    exclude=())`.

`resolve_placement(at, page, content, side) -> Rect`
:   Turn a decoration's `at:` mapping into a rectangle.

## `journalkit.modules`

`register(name)`
:   Class decorator adding a `Module` subclass to the registry. Raises if
    `name` is a built-in; replaces a previous project registration.

`build(spec, ctx) -> Module`
:   Instantiate a module from its YAML mapping (or a bare type string).

`REGISTRY: dict[str, type]`
:   Name → class.

`Module`
:   The base class. Attributes `spec`, `ctx`, `theme`, `id`, `name`. See the
    [custom modules guide](../guide/custom-modules.md) for the helper
    methods: `opt`, `length`, `stroke`, `stroke_width`, `natural_height`,
    `natural_width`, `requested_height`, `requested_width`, `fill_weight`,
    `text`, `font_metrics`, `cap_ratio`, `cap_height`, `text_width`,
    `draw_label`, `draw_marker`, `label_band`, `draw_dots`, and the abstract
    `draw(canvas, rect)`.

## `journalkit.layout`

`layout_stack(children, rect, gap_default, grid, ctx) -> list[Placement]`
:   Solve a vertical stack.

`layout_row(children, rect, gap_default, grid, ctx) -> list[Placement]`
:   Solve a horizontal row.

`Placement`
:   `module`, `rect`.

## `journalkit.geometry`

`Rect(x, y, w, h)`
:   Properties `right`, `bottom`, `cx`, `cy`. Methods `inset(top, right=None,
    bottom=None, left=None)`, `moved(dx, dy)`, `resized(w=None, h=None)`,
    `contains_point(x, y, strict=True)`. Immutable; every method returns a
    new `Rect`.

## `journalkit.svg`

`Canvas(width, height, background="#ffffff")`
:   `rect`, `line`, `circle`, `path`, `text`, `open_group`/`close_group`,
    `comment`, `raw`, `defs`, `to_svg(title=None)`. Coordinates in
    millimetres; keyword attributes with underscores become hyphenated SVG
    attributes; `None` attributes are omitted.

## `journalkit.theme`

`Theme(data=None)`
:   `get(path, default)` with `$theme.` resolution; `mm(path)`;
    `resolve(value)`; `derive(override) -> Theme`; `data` (the merged dict).

`DEFAULT_THEME`, `deep_merge(base, override)`.

## `journalkit.units`

`mm(value, default=None) -> float`, `snap(value, grid, mode="nearest")`,
`on_grid(value, grid)`, `is_fill(value)`, `fmt(value)`, and the constants
`MM_PER_PT`, `MM_PER_IN`, `MM_PER_PX`, `FILL`.

## `journalkit.icons`

`IconSet(roots)`
:   `get(name) -> Icon`, `names() -> list[str]`.

`Icon`
:   `place(canvas, box, colour, height=None, align="center",
    valign="middle") -> Rect`.

## `journalkit.fontmetrics`

`load(family, weight=400) -> FontMetrics | None`
:   Parse the font file for a family and weight, or `None` if not found.
    Bundled fonts are searched first. Cached.

`find_font(family, weight=400) -> Path | None`, `BUNDLED_FONTS: Path`

`FontMetrics`
:   `units_per_em`, `cap_ratio`, `has_outlines`,
    `text_width(text, size, tracking=0.0)`,
    `outline(text, size, tracking=0.0, anchor="start") -> str` (SVG path data
    in output units, baseline at the origin), `glyph_path(glyph_id) -> str`
    (font units).

## `journalkit.project`

`Project(root)`
:   Frozen dataclass. `locate(source=None)` classmethod; properties
    `templates_dir`, `modules_dir`, `icons_dir`, `out_dir`; methods
    `is_project()`, `templates()`, `module_files()`, `load_modules()`,
    `font_families()`.

`import_module_file(path)`
:   Import a Python file so its `@register` decorators run. Idempotent per
    resolved path.

`sources_to_documents(sources) -> list[(Project, Path)]`
:   Expand CLI `SOURCE` arguments.

## `journalkit.checks`

`check_grid(sources, out=print) -> int`
:   Number of off-grid placements across the documents.

`check_fonts(pairs, out=print) -> int`
:   `pairs` is `[(pdf_path, family, outlined)]`; returns the number of PDFs
    that fail.

`embedded_fonts(pdf) -> list[str]`

## `journalkit.cli`

`main(argv=None) -> int`
:   The command line entry point; pass a list to drive it from Python.

`build_document(source, out_dir, project=None, *, pdf=False, png=False,
dpi=300, debug=False, background=True, log=print) -> list[str]`
:   Render one document; returns its warnings.

`svg_to_pdf(svg_paths, out_pdf)`, `svg_to_png(svg_path, out_png, dpi)`
:   The Inkscape and Ghostscript wrappers.
