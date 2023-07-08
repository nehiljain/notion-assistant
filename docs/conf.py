"""Sphinx configuration."""
project = "Notion Assistant"
author = "Nehil Jain"
copyright = "2023, Nehil Jain"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_click",
    "myst_parser",
]
autodoc_typehints = "description"
html_theme = "furo"
