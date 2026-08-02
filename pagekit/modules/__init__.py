"""Module registry.

Import your own module files here (or set ``modules:`` in the YAML document to
a list of paths) and their ``@register`` decorators will make them available.
"""

from .base import REGISTRY, Module, build, register  # noqa: F401
from . import containers  # noqa: F401  (registers stack, row)
from . import core  # noqa: F401  (registers box, fields, heading, ...)

__all__ = ["REGISTRY", "Module", "build", "register"]
