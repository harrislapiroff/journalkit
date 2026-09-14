# A journalkit project

This directory is a journal. Build it with:

```sh
journalkit build --png      # SVG + PNG previews into out/
journalkit build --pdf      # the print-ready document (needs Inkscape)
journalkit watch --png      # rebuild on every save
journalkit check            # placements on the grid, fonts embedded
```

```
templates/   one YAML file per printable document (a spread, a section)
modules/     optional: Python files that add module types with @register
icons/       optional: SVG icons, looked up by filename before the built-ins
out/         what `journalkit build` writes; safe to delete
```

`journalkit modules` lists every module type available here, including the
ones from `modules/`. The full reference for templates, themes and modules is
in the journalkit README.
