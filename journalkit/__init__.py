"""journalkit — YAML page templates for a printable journal.

    from journalkit import spec, render
    doc = spec.load("templates/daily.yaml")
    pages = render.Renderer(doc).render_all()
"""

__version__ = "0.2.0"

from . import modules  # noqa: F401  (populates the module registry)

__all__ = ["modules", "__version__"]
