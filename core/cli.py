"""
Command-line interface for the Auto Portable Python Deployer.

Usage:
    deployer_app.py cli --name MyProject --python 3.12 [options]
    deployer_app.py cli --help

Examples:
    deployer_app.py cli --name MyApp --python 3.13
    deployer_app.py cli --name WebServer --python 3.12 --requirements req.txt --entry-point server.py --git --ffmpeg
    deployer_app.py cli --name MLProject --python 3.10 --requirements req.txt --no-tkinter --output E:\\builds
    deployer_app.py cli --list-versions
"""
import argparse
import sys
from pathlib import Path

from core.python_manager import PYTHON_VERSIONS, PYTHON_VERSION_LABELS
from core.package_generator import PackageConfig, PackageGenerator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deployer cli",
        description="Auto Portable Python Deployer - Generate self-contained deployment packages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  deployer_app.py cli --name MyApp --python 3.12\n"
            "  deployer_app.py cli --name WebServer --python 3.13 --requirements req.txt --git\n"
            "  deployer_app.py cli --list-versions\n"
        ),
    )

    parser.add_argument("--name", "-n",
                        help="Project name (required unless --list-versions)")
    parser.add_argument("--python", "-p", default="3.12",
                        choices=list(PYTHON_VERSIONS.keys()),
                        help="Python minor version (default: 3.12)")
    parser.add_argument("--output", "-o",
                        help="Output directory (default: ./output)")
    parser.add_argument("--entry-point", "-e", default="app.py",
                        help="Python entry point filename (default: app.py)")
    parser.add_argument("--launcher-name", default="launcher.bat",
                        help="Launcher batch file name (default: launcher.bat)")
    parser.add_argument("--requirements", "-r",
                        help="Path to requirements.txt file")
    parser.add_argument("--requirements-inline", "-ri",
                        help="Inline requirements, comma-separated (e.g., 'requests,flask,numpy')")
    parser.add_argument("--git", action="store_true",
                        help="Include portable Git")
    parser.add_argument("--ffmpeg", action="store_true",
                        help="Include portable FFmpeg")
    parser.add_argument("--no-tkinter", action="store_true",
                        help="Exclude tkinter setup")
    parser.add_argument("--extra-pth", default="",
                        help="Extra ._pth paths, comma-separated")
    parser.add_argument("--extra-pip-args", default="",
                        help="Extra pip install arguments")
    parser.add_argument("--list-versions", action="store_true",
                        help="List available Python versions and exit")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress progress output")

    return parser


def run_cli(args: list) -> int:
    """Run the CLI with given arguments. Returns exit code."""
    parser = build_parser()
    opts = parser.parse_args(args)

    # Handle --list-versions
    if opts.list_versions:
        print("\nAvailable Python versions (with embeddable ZIP):\n")
        print(f"  {'Minor':<8} {'Patch':<12} {'Description'}")
        print(f"  {'-----':<8} {'-----':<12} {'-----------'}")
        for minor, patch in PYTHON_VERSIONS.items():
            label = PYTHON_VERSION_LABELS[minor]
            print(f"  {minor:<8} {patch:<12} {label}")
        print()
        return 0

    # Require --name for generation
    if not opts.name:
        parser.error("--name is required (use --list-versions to see options)")
        return 1

    # Resolve output dir
    base_dir = Path(__file__).parent.parent.resolve()
    output_dir = Path(opts.output) if opts.output else base_dir / "output"

    # Build requirements string
    requirements = ""
    if opts.requirements:
        req_path = Path(opts.requirements)
        if not req_path.exists():
            print(f"ERROR: Requirements file not found: {req_path}")
            return 1
        requirements = req_path.read_text(encoding="utf-8")
    elif opts.requirements_inline:
        requirements = "\n".join(p.strip() for p in opts.requirements_inline.split(","))

    # Parse extra pth paths
    extra_pth = [p.strip() for p in opts.extra_pth.split(",") if p.strip()] if opts.extra_pth else []

    # Build config
    config = PackageConfig(
        project_name=opts.name,
        python_minor=opts.python,
        output_dir=output_dir,
        entry_point=opts.entry_point,
        launcher_name=opts.launcher_name,
        requirements=requirements,
        include_git=opts.git,
        include_ffmpeg=opts.ffmpeg,
        include_tkinter=not opts.no_tkinter,
        extra_pth_paths=extra_pth,
        extra_pip_args=opts.extra_pip_args,
    )

    # Print config summary
    if not opts.quiet:
        print()
        print("=" * 55)
        print("  Auto Portable Python Deployer - CLI")
        print("=" * 55)
        print(f"  Project:     {config.project_name}")
        print(f"  Python:      {config.python_version} ({config.python_minor})")
        print(f"  Entry point: {config.entry_point}")
        print(f"  Output:      {output_dir / config.project_name.replace(' ', '_')}")
        print(f"  Tkinter:     {'Yes' if config.include_tkinter else 'No'}")
        print(f"  Git:         {'Yes' if config.include_git else 'No'}")
        print(f"  FFmpeg:      {'Yes' if config.include_ffmpeg else 'No'}")
        if requirements:
            req_count = len([l for l in requirements.split("\n") if l.strip() and not l.strip().startswith("#")])
            print(f"  Requirements: {req_count} package(s)")
        print("-" * 55)

    # Generate
    def progress_cb(current, total, message):
        if not opts.quiet:
            print(f"  [{current:3d}%] {message}")

    generator = PackageGenerator(config)
    success = generator.generate(progress_callback=progress_cb)

    if success:
        if not opts.quiet:
            print()
            print(f"  Package generated at: {generator.output_path}")
            print(f"  Run install.bat in that folder to deploy.")
            print()
        return 0
    else:
        print("\nERROR: Package generation failed.")
        return 1
