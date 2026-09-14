# Install

## journalkit

[pipx](https://pipx.pypa.io/) installs a Python command line tool in its own
environment and puts it on your `PATH`:

```sh
pipx install https://github.com/harrislapiroff/journalkit/archive/refs/heads/main.tar.gz
```

That is GitHub's archive of the `main` branch; pip installs it directly, no
git needed. For a specific release use a tag:
`.../archive/refs/tags/v0.2.0.tar.gz`. Upgrade with the same command plus
`--force`.

```sh
journalkit --version
```

Plain `pip install <the same URL>` works too, in any Python 3.10+
environment.

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
  ok   Montserrat (bundled with journalkit) — text will be outlined, nothing to install
project:
  FAIL /Users/you has no templates/ — run `journalkit init` to start one

MISSING: project
```

The last line is expected; making a project is the
[next step](first-journal.md).
