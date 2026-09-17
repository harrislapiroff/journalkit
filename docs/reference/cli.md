# Command line

```
journalkit [--version] <command> [options]
```

Every command works on a **project directory** (see
[project directory](project.md)). Commands that take `SOURCE` accept any
number of them, each a project directory or a single YAML document; with
none, the working directory is the project. Output goes to `<project>/out/`
unless `-o` says otherwise.

Exit codes: `0` success, `1` an error (unreadable document, missing tool,
failed check), `2` a warning under `--strict`.

## `build`

Render documents to SVG, and optionally PDF and PNG.

```
journalkit build [SOURCE ...] [--project DIR] [-o DIR] [--pdf] [--png] [--dpi N]
                 [--debug] [--no-background] [--strict]
```

| option | |
|---|---|
| `SOURCE` | project directories and/or YAML files; default `.` |
| `--project DIR` | use `DIR`'s `modules/`, `icons/` and `out/` regardless of where `SOURCE` is |
| `-o, --out DIR` | output directory; default `<project>/out` |
| `--pdf` | also write `<document>.pdf` (needs Inkscape; Ghostscript for more than one page) |
| `--png` | also write one PNG per page (needs Inkscape) |
| `--dpi N` | PNG resolution; default 300 |
| `--debug` | overlay the module grid and content rectangle |
| `--no-background` | omit the white page fill |
| `--strict` | exit 2 if any document warned |

Files are named `<document>-<nn>-<page>.svg` where `nn` is the 1-based page
index. One line per file written goes to stdout; warnings go to stderr,
prefixed with the document and page. A document that fails to build is
reported and the others continue; the exit code is then 1.

## `watch`

Rebuild whenever an input changes, until interrupted.

```
journalkit watch [SOURCE ...] [--project DIR] [-o DIR] [--pdf] [--png] [--dpi N]
                 [--debug] [--interval SECONDS]
```

Same rendering options as `build`, plus `--interval` (poll period, default
0.4 s). PDF is opt-in here as everywhere. Watches each project's
`templates/`, `modules/` and `icons/`, and the installed journalkit package.
A changed template rebuilds only that template; any other change rebuilds
all of them. Files that appear while watching are picked up.

## `preview`

Render a `content:` list from standard input into a throwaway document.

```
journalkit preview [--project DIR] [--modules FILE ...] [--dpi N] [--debug]
```

| option | |
|---|---|
| `--project DIR` | project whose `modules/`, `icons/` and `out/` to use; default `.` |
| `--modules FILE` | an extra module file to load; repeatable |
| `--dpi N` | PNG resolution; default 150 |
| `--debug` | grid overlay |

The wrapper is a 105 × 170 mm recto with margins `{top: 2.5, bottom: 7.5,
inner: 25, outer: 5}`, a 2.5 mm module grid, 5 mm dots at origin `[0, 2.5]`,
and the default theme. Output is `<project>/out/preview/preview-01-preview.{svg,png}`.

## `check`

Two checks on the built output.

```
journalkit check [SOURCE ...] [--project DIR] [-o DIR]
```

1. **Grid.** Every module placement in every page, recursively through
   containers, lies on the document's module grid. A page whose content
   rectangle is itself off the lattice is noted and its placements are
   checked relative to it.
2. **Fonts.** For each document whose PDF exists in the output directory:
   with outlined text (the default) the PDF embeds no fonts; with
   `font.outline: false`, every embedded `/BaseFont` (subset prefix
   stripped) begins with `theme.font.family` (spaces removed). A PDF that
   has not been built is reported and skipped.

Exit 1 on any off-grid placement or substituted font.

## `modules`

List every registered module type with its docstring and parameters.

```
journalkit modules [DIR]
```

`DIR` is the project whose `modules/` to load first; default `.`. Types from
the project are marked with their file name. A closing line lists the
options every module accepts.

## `doctor`

Check the environment.

```
journalkit doctor [DIR]
```

Reports Inkscape and Ghostscript on `PATH`; for each font family the
project's templates name, whether a font file was found (bundled with
JournalKit, or in the system font directories) and whether it has TrueType
outlines; and whether `DIR` is a project. Exit 1 if anything is missing.

## `init`

Create a project from the built-in scaffold.

```
journalkit init [DIRECTORY]
```

Writes `README.md`, `templates/daily.yaml` and `modules/stamp.py` into
`DIRECTORY` (default `.`), creating it if needed. Existing files are never
overwritten; they are listed as kept.

## `--version`

Prints `journalkit <version>`.
