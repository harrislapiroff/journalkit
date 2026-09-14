# Iterating with watch and preview

Two commands are built for the edit–look loop.

## `watch`

Rebuilds on every save until you interrupt it:

```sh
journalkit watch --png          # SVG + PNG, the useful combination while editing
journalkit watch --pdf          # the real document, slower (Inkscape per page)
```

```
watching /…/my-journal for changes → svg + png
ctrl-c to stop

[18:17:35] initial build
  daily.yaml         ok      2 file(s)   0.4s
  weekly.yaml        ok      2 file(s)   0.3s

[18:17:41] daily.yaml
  daily.yaml         ok      2 file(s)   0.4s
      warning: daily: front: box: height 25.000mm is off the 2.500mm grid, snapped to 25.000mm
```

It watches the project's `templates/`, `modules/` and `icons/`. Editing a
template rebuilds that template; editing a module or an icon rebuilds every
template, because either can change every page. Warnings appear indented
under the file that caused them, and a broken template prints its error
without stopping the watcher — fix the YAML and it rebuilds.

Pair it with an image viewer that reloads when a file changes, and keep it
in a second terminal.

Pass a single document to watch just that one, or `-o DIR` to write
somewhere other than `out/`.

## `preview`

Renders a list of modules from standard input, without a template file. You
feed it just the `content:` entries and it wraps them in a throwaway
105 × 170 mm document on a 2.5 mm grid:

```sh
cat <<'YAML' | journalkit preview
- {type: heading, text: PREVIEW, icon: sunrise}
- {type: fields, columns: [ALPHA, BETA, GAMMA]}
- {type: rating, label: SCALE, icon: mood, count: 5}
- {type: checklist, rows: 3}
- {type: lines, height: 20, border: true, label: RULED}
- {type: box, label: DOTS, height: fill, dots: true}
YAML
```

```
wrote /…/my-journal/out/preview/preview-01-preview.svg
wrote /…/my-journal/out/preview/preview-01-preview.png
```

The project's `modules/` and `icons/` are available, so this is the
fastest loop for developing a module: edit the `.py`, re-run the pipe, look.
`--project DIR` points it at a different project; `--modules FILE` loads an
extra module file from anywhere; `--debug` adds the grid overlay.

## The debug overlay

`--debug` on `build`, `watch` or `preview` draws the module grid in blue and
the content rectangle as a pink dashed box. It answers most "why is this
here?" questions at a glance: a module edge that is not on a blue line has
been snapped, and a gap that looks wrong usually is one.
