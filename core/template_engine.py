"""
Simple Template Engine

Renders templates with {{VARIABLE}} substitution.
No external dependencies.
"""
import re
from pathlib import Path
from typing import Dict


def render_template(template_text: str, variables: Dict[str, str]) -> str:
    """Replace all {{VARIABLE}} placeholders with values from the dict.

    Unknown variables are left as-is.
    """
    def replacer(match):
        key = match.group(1).strip()
        return variables.get(key, match.group(0))

    return re.sub(r"\{\{(\s*\w+\s*)\}\}", replacer, template_text)


def render_template_file(template_path: Path, variables: Dict[str, str]) -> str:
    """Read a template file and render it."""
    text = template_path.read_text(encoding="utf-8")
    return render_template(text, variables)


def render_and_write(template_path: Path, output_path: Path, variables: Dict[str, str]):
    """Read a template, render it, and write the result."""
    rendered = render_template_file(template_path, variables)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
