"""Loading a notebook definition from YAML."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .project import Project, import_module_file
from .theme import Theme
from .units import mm

#: Icons shipped with journalkit, searched after the project's own.
BUILTIN_ICONS = Path(__file__).resolve().parent / "icons"

#: Named page sizes, width x height in mm.
PAGE_SIZES = {
    "a4": (210.0, 297.0),
    "a5": (148.0, 210.0),
    "a6": (105.0, 148.0),
    "a7": (74.0, 105.0),
    "b6": (125.0, 176.0),
    "letter": (215.9, 279.4),
    "half-letter": (139.7, 215.9),
    "pocket": (89.0, 140.0),
    "hobonichi-weeks": (95.0, 188.0),
}

DEFAULT_MARGINS = {"top": 10.0, "bottom": 10.0, "inner": 15.0, "outer": 10.0}


def _page_size(value) -> tuple[float, float]:
    if value is None:
        return PAGE_SIZES["a5"]
    if isinstance(value, str):
        key = value.strip().lower()
        if key not in PAGE_SIZES:
            raise ValueError("unknown page size %r (known: %s)" % (value, ", ".join(sorted(PAGE_SIZES))))
        return PAGE_SIZES[key]
    if isinstance(value, dict):
        return mm(value["width"]), mm(value["height"])
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return mm(value[0]), mm(value[1])
    raise ValueError("cannot read page size from %r" % (value,))


@dataclass
class Margins:
    top: float
    bottom: float
    inner: float
    outer: float
    left: float | None = None   # set to disable mirroring
    right: float | None = None

    @classmethod
    def parse(cls, data: dict | None) -> "Margins":
        data = dict(data or {})
        if "all" in data:
            everywhere = mm(data.pop("all"))
            for key in ("top", "bottom", "inner", "outer"):
                data.setdefault(key, everywhere)
        values = {k: mm(data[k]) if k in data else v for k, v in DEFAULT_MARGINS.items()}
        left = mm(data["left"]) if "left" in data else None
        right = mm(data["right"]) if "right" in data else None
        return cls(left=left, right=right, **values)

    def for_side(self, side: str) -> tuple[float, float, float, float]:
        """Return (top, right, bottom, left) for a 'left' or 'right' page."""
        if self.left is not None or self.right is not None:
            left = self.left if self.left is not None else self.outer
            right = self.right if self.right is not None else self.outer
        elif side == "left":  # verso: binding on the right
            left, right = self.outer, self.inner
        else:                 # recto: binding on the left
            left, right = self.inner, self.outer
        return self.top, right, self.bottom, left


@dataclass
class DotGrid:
    spacing: float = 5.0
    origin: tuple[float, float] = (0.0, 0.0)
    radius: float = 0.125
    colour: str = "#231F20"
    opacity: float = 1.0
    inset: float = 0.0

    @classmethod
    def parse(cls, data: dict | None, theme: Theme) -> "DotGrid":
        data = dict(data or {})
        origin = data.get("origin", (0.0, 0.0))
        if isinstance(origin, (int, float)):
            origin = (float(origin), float(origin))
        return cls(
            spacing=mm(data.get("spacing", 5)),
            origin=(mm(origin[0]), mm(origin[1])),
            radius=mm(data.get("radius", theme.get("dots.radius"))),
            colour=data.get("colour", data.get("color", theme.get("dots.colour"))),
            opacity=float(data.get("opacity", theme.get("dots.opacity"))),
            inset=mm(data.get("inset", 0)),
        )


@dataclass
class PageSpec:
    name: str
    side: str = "right"
    content: list = field(default_factory=list)
    decorations: list = field(default_factory=list)
    theme: dict | None = None
    margins: Margins | None = None
    gap: float | None = None


@dataclass
class Document:
    name: str
    width: float
    height: float
    margins: Margins
    grid: float
    dots: DotGrid
    theme: Theme
    default_gap: float
    decorations: list
    pages: list[PageSpec]
    icon_dirs: list[Path]
    source: Path
    project: Project | None = None

    @property
    def size(self):
        return self.width, self.height


def _load_extra_modules(paths, base: Path) -> None:
    """Import module files a document lists under ``modules:``.

    Relative paths are resolved against the document. The project's own
    ``modules/`` directory is loaded without being listed; this is for the
    one-off case of a file that lives somewhere else.
    """
    for raw in paths or []:
        path = (base / raw).resolve() if not Path(raw).is_absolute() else Path(raw)
        if not path.is_file():
            raise FileNotFoundError("modules: %s not found" % path)
        import_module_file(path)


def load(path: str | Path, project: Project | None = None) -> Document:
    """Read a YAML document into a :class:`Document`.

    ``project`` is the directory whose ``modules/`` and ``icons/`` the
    document may use; it is located from the file's position when omitted.
    """
    path = Path(path).resolve()
    if project is None:
        project = Project.locate(path)
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        # A syntax error in a hand-written template is a user error, not a
        # journalkit bug — report it like one instead of a traceback. This is the
        # common case under `journalkit watch`, which rebuilds mid-edit.
        raise ValueError("%s: %s" % (path.name, exc)) from None
    base = path.parent

    project.load_modules()
    _load_extra_modules(data.get("modules"), base)

    page_data = data.get("page", {})
    width, height = _page_size(page_data.get("size"))
    margins = Margins.parse(page_data.get("margins"))

    grid_data = data.get("grid", {})
    if isinstance(grid_data, (int, float, str)):
        grid_data = {"module": grid_data}
    grid = mm(grid_data.get("module", 2.5))

    theme = Theme(data.get("theme"))
    dots = DotGrid.parse(grid_data.get("dots", data.get("dots")), theme)

    defaults = data.get("defaults", {})
    default_gap = mm(defaults.get("gap", grid))

    # Search order: directories the document names (relative to itself),
    # then the project's icons/, then the set shipped with journalkit.
    icon_dirs = [base / d for d in data.get("icons", []) or []]
    icon_dirs += [project.icons_dir, BUILTIN_ICONS]

    templates = data.get("templates", {}) or {}
    pages: list[PageSpec] = []
    entries = data.get("pages")
    if entries is None:
        entries = [{"template": name} for name in templates]

    for entry in entries:
        if isinstance(entry, str):
            entry = {"template": entry}
        template_name = entry.get("template")
        template = {}
        if template_name:
            if template_name not in templates:
                raise ValueError("page refers to unknown template %r" % template_name)
            template = templates[template_name] or {}
        merged = dict(template)
        merged.update({k: v for k, v in entry.items() if k not in ("repeat", "template")})

        count = int(entry.get("repeat", 1))
        for index in range(count):
            name = merged.get("name") or template_name or "page"
            if count > 1:
                name = "%s-%02d" % (name, index + 1)
            pages.append(
                PageSpec(
                    name=name,
                    side=merged.get("side", "right"),
                    content=merged.get("content", []) or [],
                    decorations=merged.get("decorations", []) or [],
                    theme=merged.get("theme"),
                    margins=Margins.parse(merged["margins"]) if "margins" in merged else None,
                    gap=mm(merged["gap"]) if "gap" in merged else None,
                )
            )

    return Document(
        name=data.get("document", {}).get("name", path.stem) if isinstance(data.get("document"), dict)
        else data.get("document", path.stem),
        width=width,
        height=height,
        margins=margins,
        grid=grid,
        dots=dots,
        theme=theme,
        default_gap=default_gap,
        decorations=data.get("decorations", []) or [],
        pages=pages,
        icon_dirs=icon_dirs,
        source=path,
        project=project,
    )
