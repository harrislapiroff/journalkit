# Install

## journalkit

journalkit is a command line tool. The recommended way to install a Python
command line tool is [pipx](https://pipx.pypa.io/), which gives it an
isolated environment and puts the `journalkit` command on your `PATH`.

```sh
pipx install https://github.com/harrislapiroff/journalkit/archive/refs/heads/main.tar.gz
```

That URL is GitHub's archive of the `main` branch. pip downloads and installs
it directly; no git is involved. To install a specific release instead, use a
tag: `.../archive/refs/tags/v0.2.0.tar.gz`.

Upgrade later with the same command plus `--force`.

Check it worked:

```sh
journalkit --version
```

!!! note "Without pipx"
    Any Python 3.10+ environment works: `pip install <the same URL>`. pipx is
    recommended only because it keeps the tool separate from your other
    Python packages.

## Inkscape and Ghostscript

SVG output needs nothing else. For **PDF** and **PNG** output journalkit
shells out to Inkscape, which embeds fonts properly, and for multi-page
documents to Ghostscript, which concatenates the per-page PDFs.

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
    [Ghostscript](https://ghostscript.com/releases/gsdnld.html), and make
    sure `inkscape` and `gs` are on your `PATH`.

## A font

Text is positioned from the font's cap height, and Inkscape substitutes a
missing font *without warning*. Install the font your templates use before
you build a PDF. The default theme and the starter project use
[Montserrat](https://fonts.google.com/specimen/Montserrat); download it and
install it system-wide.

## Check everything

```sh
journalkit doctor
```

```
tools (only needed for --pdf and --png):
  ok   inkscape  /opt/homebrew/bin/inkscape
  ok   gs        /opt/homebrew/bin/gs
fonts:
  ok   Montserrat installed
project:
  FAIL /Users/you has no templates/ — run `journalkit init` to start one

MISSING: project
```

The last line is expected: you have not made a project yet. That is the
[next step](first-journal.md).
