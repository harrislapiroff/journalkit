"""The project directory: where a journal's templates, modules and icons live.

journalkit is run *on a directory*. A project is nothing more than a folder
with this shape — every part of it optional except ``templates/``::

    my-journal/
      templates/   *.yaml documents, one per printable spread
      modules/     *.py files whose @register decorators add module types
      icons/       *.svg files, looked up by stem before the built-in set
      out/         where `journalkit build` writes (created on demand)

:func:`Project.locate` turns whatever the user typed — nothing, a directory,
or a path to one YAML file — into a project, so every command resolves the
same way.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

TEMPLATE_SUFFIXES = (".yaml", ".yml")

#: Files already imported, by resolved path. A module file registers its
#: types with ``@register``, which refuses duplicates — so importing the same
#: file for a second document in the same process must be a no-op.
_LOADED: dict[Path, object] = {}


def import_module_file(path: str | Path) -> object:
    """Import a Python file so its ``@register`` decorators run. Idempotent."""
    path = Path(path).resolve()
    if path in _LOADED:
        return _LOADED[path]
    if not path.is_file():
        raise FileNotFoundError("module file not found: %s" % path)
    name = "journalkit_project_module_%d_%s" % (len(_LOADED), path.stem)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    # Register before executing so a module that imports itself (or a sibling
    # that imports it back) does not recurse.
    _LOADED[path] = module
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        del _LOADED[path]
        sys.modules.pop(name, None)
        raise
    return module


@dataclass(frozen=True)
class Project:
    root: Path

    @classmethod
    def locate(cls, source: str | Path | None = None) -> "Project":
        """Find the project a command line argument refers to.

        * nothing → the working directory
        * a directory → that directory
        * a YAML file → its ``templates/`` parent's parent, or failing that
          the directory the file is in, so a document outside any project
          still gets a place to write ``out/``.
        """
        if source is None:
            return cls(Path.cwd().resolve())
        path = Path(source).expanduser().resolve()
        if path.is_dir():
            return cls(path)
        if path.parent.name == "templates":
            return cls(path.parent.parent)
        return cls(path.parent)

    # -- layout -----------------------------------------------------------
    @property
    def templates_dir(self) -> Path:
        return self.root / "templates"

    @property
    def modules_dir(self) -> Path:
        return self.root / "modules"

    @property
    def icons_dir(self) -> Path:
        return self.root / "icons"

    @property
    def out_dir(self) -> Path:
        return self.root / "out"

    def is_project(self) -> bool:
        """Does this look like a journal, or just a directory we landed in?"""
        return self.templates_dir.is_dir()

    def templates(self) -> list[Path]:
        if not self.templates_dir.is_dir():
            return []
        return sorted(p for p in self.templates_dir.iterdir()
                      if p.suffix in TEMPLATE_SUFFIXES and p.is_file()
                      and not p.name.startswith("."))

    def module_files(self) -> list[Path]:
        if not self.modules_dir.is_dir():
            return []
        return sorted(p for p in self.modules_dir.glob("*.py")
                      if not p.name.startswith(("_", ".")))

    def load_modules(self) -> list[Path]:
        """Import every ``modules/*.py`` so their types are registered."""
        files = self.module_files()
        for path in files:
            import_module_file(path)
        return files

    def font_families(self) -> set[str]:
        """Every ``theme.font.family`` the project's templates ask for.

        Read with a plain YAML load rather than :func:`journalkit.spec.load`
        so ``doctor`` can report on a project whose templates do not parse
        yet. Falls back to the theme default when a template names none.
        """
        from .theme import DEFAULT_THEME

        families: set[str] = set()
        for template in self.templates():
            try:
                data = yaml.safe_load(template.read_text()) or {}
            except (yaml.YAMLError, OSError):
                continue
            family = ((data.get("theme") or {}).get("font") or {}).get("family")
            families.add(family or DEFAULT_THEME["font"]["family"])
        if not families:
            families.add(DEFAULT_THEME["font"]["family"])
        return families


def sources_to_documents(sources: list[str] | None) -> list[tuple[Project, Path]]:
    """Expand command line SOURCE arguments to ``(project, template)`` pairs.

    Each source is a directory (every template in it) or a single YAML file.
    No sources means the working directory.
    """
    pairs: list[tuple[Project, Path]] = []
    for source in sources or ["."]:
        path = Path(source).expanduser()
        if path.is_dir():
            project = Project.locate(path)
            templates = project.templates()
            if not templates:
                raise FileNotFoundError(
                    "%s has no templates/*.yaml — run `journalkit init` to start one"
                    % project.root)
            pairs.extend((project, t) for t in templates)
        elif path.is_file():
            pairs.append((Project.locate(path), path.resolve()))
        else:
            raise FileNotFoundError("no such file or directory: %s" % source)
    return pairs
