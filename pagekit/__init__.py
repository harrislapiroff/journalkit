"""pagekit — structured page templates for a printable notebook.

    from pagekit import spec, render
    doc = spec.load("templates/daily.yaml")
    pages = render.Renderer(doc).render_all()
"""

__version__ = "0.1.0"

from . import modules  # noqa: F401  (populates the module registry)

__all__ = ["modules"]
