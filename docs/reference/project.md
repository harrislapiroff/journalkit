# Project directory

A project is a directory with this shape. Only `templates/` is required.

```
my-journal/
  templates/     *.yaml (or *.yml) documents
  modules/       *.py files whose @register decorators add module types
  icons/         *.svg icons, looked up by file stem before the built-ins
  out/           output; created on demand, safe to delete
```

## How a source resolves to a project

Every command takes `SOURCE` arguments and turns each into a project:

| you pass | project is |
|---|---|
| nothing | the working directory |
| a directory | that directory |
| a YAML file inside a `templates/` directory | the directory containing `templates/` |
| any other YAML file | the directory the file is in |

So `journalkit build ~/journals/mine/templates/daily.yaml` finds
`~/journals/mine/modules/` and writes to `~/journals/mine/out/`. A single
document outside any project still builds; it just has no `modules/` or
`icons/` of its own.

`--project DIR` on `build`, `watch`, `check` and `preview` overrides the
resolution and uses `DIR` for everything.

## Templates

`templates/*.yaml` and `*.yml`, sorted by name, skipping dot-files. A
directory `SOURCE` builds all of them; a file `SOURCE` builds just that one.

## Modules

`modules/*.py`, sorted by name, skipping files that start with `_` or `.`.
Each is imported once per process before any document is loaded, so the
types it registers are available to every template. The import is by file
path, not by package, so the files need no `__init__.py` and can be named
anything.

A document may additionally list files under `modules:`; relative paths
resolve against the document. The same file listed twice, or loaded from two
documents, is imported once.

Registration rules: a project module may not redefine a built-in type name;
two project files defining the same name is permitted and the later wins.

## Icons

Lookup order for `icon: <name>`:

1. directories listed under `icons:` in the document, relative to it;
2. the project's `icons/`;
3. the icons shipped with journalkit.

The first `<name>.svg` found wins.

## Output

`out/` under the project, or `-o DIR`. File naming:

```
<document>-<nn>-<page>.svg     nn = 1-based page index, zero-padded to 2
<document>-<nn>-<page>.png     with --png
<document>.pdf                 with --pdf
preview/preview-01-preview.*   from journalkit preview
```

## Scaffold

`journalkit init [DIR]` writes:

```
README.md                a one-screen orientation
templates/daily.yaml     a two-page recto/verso document
modules/stamp.py         a small module type the template uses
```

It never overwrites an existing file, so it is safe to re-run in a project
to recover a deleted starter file.
