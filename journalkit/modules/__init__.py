"""Module registry.

The built-in library registers itself when this package is imported. A
project adds its own types by dropping ``.py`` files in its ``modules/``
directory (loaded by :class:`journalkit.project.Project`), or by listing files
under ``modules:`` in a document; either way their ``@register`` decorators run
and the type becomes available in YAML.
"""

from .base import REGISTRY, Module, build, register  # noqa: F401
from . import containers  # noqa: F401  (registers stack, row)
from . import core  # noqa: F401  (registers box, fields, heading, ...)
from . import trackers  # noqa: F401  (registers habit_grid)

__all__ = ["REGISTRY", "Module", "build", "register"]
