"""Sphinx configuration for the ExoArmur documentation site."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

project = "ExoArmur"
author = "ExoArmur Team"
copyright = "2026, ExoArmur Team"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}
master_doc = "index"

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "tasklist",
]
autodoc_typehints = "description"
autoclass_content = "both"
