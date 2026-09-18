# Install

## JournalKit

[pipx](https://pipx.pypa.io/) installs a Python command line tool in its own
environment and puts it on your `PATH`:

```sh
pipx install journalkit
```

Upgrade with `pipx upgrade journalkit`. To run whatever is on `main` instead
of the last release, install GitHub's archive of the branch — pip downloads
it directly, no git needed:

```sh
pipx install --force https://github.com/harrislapiroff/journalkit/archive/refs/heads/main.tar.gz
```

```sh
journalkit --version
```

Plain `pip install journalkit` works too, in any Python 3.10+ environment.

## Inkscape and Ghostscript

Only needed for PDF and PNG output. Inkscape does the conversion;
Ghostscript joins the pages of a multi-page document into one PDF.

=== "macOS"

    ```sh
    brew install --cask inkscape
    brew install ghostscript
    ```

=== "Linux"

    ```sh
    sudo apt install inkscape ghostscript      # Debian / Ubuntu
    sudo dnf install inkscape ghostscript      # Fedora
    ```

=== "Windows"

    Install [Inkscape](https://inkscape.org/release/) and
    [Ghostscript](https://ghostscript.com/releases/gsdnld.html) and put
    `inkscape` and `gs` on your `PATH`.

## Check

```sh
journalkit doctor
```

```
tools (only needed for --pdf and --png):
  ok   inkscape  /opt/homebrew/bin/inkscape
  ok   gs        /opt/homebrew/bin/gs
fonts:
  ok   Montserrat (bundled with JournalKit)
project:
  FAIL /Users/you has no templates/ — run `journalkit init` to start one

MISSING: project
```

The last line is expected; making a project is the
[next step](first-journal.md).
