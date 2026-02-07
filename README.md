# Auto Portable Python Deployer

A self-bootstrapping tool that generates **fully portable, zero-install Python deployment packages** for Windows. No system Python required. No admin rights. No PATH modifications. Just double-click and go.

The deployer itself is portable — it downloads its own embedded Python runtime on first run, sets up pip and tkinter automatically, then launches a GUI or CLI where you configure and generate deployment packages for your own projects.

---

## Features

- **Self-Bootstrapping** — Run `install.bat` on any Windows machine. It downloads Python, pip, and tkinter from scratch. Nothing needs to be pre-installed.
- **Python 3.10 – 3.14** — Choose any supported Python version. The tool tracks the latest patch releases that include Windows embeddable distributions.
- **GUI + CLI** — Full Tkinter GUI for interactive use, or a complete CLI for scripting and CI pipelines.
- **Portable Git** — Optionally bundles MinGit so generated packages can clone repositories without system Git.
- **Portable FFmpeg** — Optionally bundles FFmpeg for audio/video processing projects.
- **Tkinter Support** — Automatically downloads and installs tkinter from the official `tcltk.msi` — something the embeddable distribution doesn't include.
- **Template-Based Generation** — Clean `{{VAR}}` template system produces well-structured, readable batch files and config modules.
- **Zero Dependencies at Bootstrap** — The installer uses only PowerShell (built into Windows) and `get-pip.py`. No curl, no wget, no chocolatey.

---

## How It Works

The Python embeddable distribution is a minimal, self-contained Python runtime designed for embedding into applications. It's missing several things that a full install provides: pip, tkinter, site-packages support, and the `import site` mechanism. This tool handles all of that automatically:

1. Downloads the embeddable ZIP from `python.org`
2. Extracts and configures the `._pth` file to enable `site-packages` and `import site`
3. Bootstraps pip via `get-pip.py`
4. Downloads `tcltk.msi` from `python.org` and extracts the DLLs, Python packages, and Tcl/Tk libraries needed for tkinter
5. Installs project requirements into the embedded environment

Generated packages follow this exact same proven pattern.

---

## Quick Start

### First Run (Setup)

```
git clone https://github.com/rookiemann/auto-portable-python-deployer.git
cd auto-portable-python-deployer
install.bat
```

This will:
- Download Python 3.12.10 embedded (~11 MB)
- Configure pip and tkinter
- Install deployer dependencies
- Launch the GUI

After first run, use `launcher.bat` to reopen instantly.

### GUI Mode

```
launcher.bat
```

The GUI provides:
- **Project Configuration** — Name, output directory, Python version (3.10–3.14), entry point, launcher name
- **Portable Components** — Checkboxes for tkinter, Git, and FFmpeg
- **Requirements Editor** — Paste requirements or load from file
- **Advanced Options** — Extra `._pth` paths and pip arguments
- **Generation Log** — Real-time progress output

### CLI Mode

```
launcher.bat cli --name MyApp --python 3.12
launcher.bat cli --name WebServer --python 3.13 -r requirements.txt --git
launcher.bat cli --name MLProject --python 3.10 -ri "torch,numpy,flask" --no-tkinter
launcher.bat cli --name QuickTool --python 3.14 -q
launcher.bat cli --list-versions
launcher.bat cli --help
```

#### CLI Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--name` | `-n` | Project name (required) |
| `--python` | `-p` | Python version: `3.10`, `3.11`, `3.12`, `3.13`, `3.14` (default: `3.12`) |
| `--output` | `-o` | Output directory (default: `./output`) |
| `--entry-point` | `-e` | Python entry point filename (default: `app.py`) |
| `--launcher-name` | | Launcher batch file name (default: `launcher.bat`) |
| `--requirements` | `-r` | Path to a `requirements.txt` file |
| `--requirements-inline` | `-ri` | Comma-separated package list |
| `--git` | | Include portable Git (MinGit 2.47.1) |
| `--ffmpeg` | | Include portable FFmpeg |
| `--no-tkinter` | | Skip tkinter setup in the generated package |
| `--extra-pth` | | Extra `._pth` paths, comma-separated |
| `--extra-pip-args` | | Additional pip install arguments |
| `--list-versions` | | Show available Python versions and exit |
| `--quiet` | `-q` | Suppress all output (for scripting) |

---

## Generated Package Structure

When you generate a package, the output folder contains everything needed for a portable deployment:

```
MyProject/
├── install.bat          # Downloads Python, pip, tkinter, Git, FFmpeg — then installs requirements
├── launcher.bat         # Runs the app (auto-triggers install.bat if needed)
├── config.py            # Path resolution: embedded Python > system Python
├── requirements.txt     # Project dependencies
└── app.py               # Entry point stub (tkinter or console, depending on options)
```

The end user just runs `install.bat` or `launcher.bat`. Everything downloads and configures automatically.

---

## Python Version Matrix

The embeddable distribution is only available for active Python releases. Security-only releases (end-of-life for new features) drop Windows embeddable builds. These are the latest verified versions:

| Version | Patch | Status | Notes |
|---------|-------|--------|-------|
| 3.10 | 3.10.11 | Stable | Last with embeddable ZIP — wide library compatibility |
| 3.11 | 3.11.9 | Stable | Last with embeddable ZIP — ~25% faster than 3.10 |
| 3.12 | 3.12.10 | Stable | **Recommended** — latest features with broad support |
| 3.13 | 3.13.12 | Stable | Newest features, active development |
| 3.14 | 3.14.3 | Stable | Latest release |

---

## Project Structure

```
auto-portable-python-deployer/
│
├── install.bat                 # Self-bootstrapper: downloads Python 3.12.10, pip, tkinter
├── launcher.bat                # Quick launcher: GUI, CLI, or setup
├── deployer_app.py             # Main application entry point (routes GUI ↔ CLI)
├── config.py                   # Path resolution and app settings
├── requirements.txt            # Deployer's own dependencies (just requests)
├── .gitignore
├── README.md
│
├── core/
│   ├── __init__.py
│   ├── python_manager.py       # Python 3.10–3.14 download engine + tkinter setup
│   ├── package_generator.py    # Assembles deployment packages from templates
│   ├── template_engine.py      # {{VAR}} template rendering (no external deps)
│   └── cli.py                  # Full argparse CLI interface
│
├── templates/
│   ├── install.bat.template    # Parameterized installer for generated packages
│   ├── launcher.bat.template   # Parameterized launcher for generated packages
│   └── config.py.template      # Parameterized config for generated packages
│
└── python_embedded/            # (auto-downloaded, not in repo)
    ├── python.exe
    ├── pip, tkinter, tcl/tk
    └── Lib/site-packages/
```

---

## How the Embedded Python Bootstrap Works

For those curious about the internals, here's what `install.bat` does under the hood:

```
1. Download python-3.12.10-embed-amd64.zip from python.org
2. Extract to python_embedded/
3. Find python312._pth and rewrite it:
     python312.zip
     .
     Lib
     Lib\site-packages
     DLLs

     import site              ← This line re-enables the site module
4. Create Lib/site-packages/
5. Download get-pip.py from bootstrap.pypa.io
6. Run: python.exe get-pip.py
7. Download tcltk.msi from python.org
8. Extract via: msiexec /a tcltk.msi /qn TARGETDIR=...
9. Copy _tkinter.pyd, tcl86t.dll, tk86t.dll → python_embedded/
10. Copy Lib/tkinter/ and tcl/ directories
11. pip install -r requirements.txt
12. Launch the application
```

This pattern is proven in production across multiple projects and handles all the quirks of the embeddable distribution.

---

## Requirements

- **Windows 10/11** (64-bit)
- **Internet connection** (for first-run download only)
- **No admin rights needed**
- **No pre-installed Python needed**

---

## Contributors

- **[@rookiemann](https://github.com/rookiemann)** — Creator and maintainer
- **Claude (Anthropic)** — AI pair programmer, architecture design and implementation

---

## License

MIT
