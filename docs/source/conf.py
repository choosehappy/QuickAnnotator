from pathlib import Path
import toml

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'QuickAnnotator'
copyright = '2025, Jackson Jacobs, Fan Fan, Laura Barisoni, Andrew Janowczyk'
author = 'Jackson Jacobs, Fan Fan, Laura Barisoni, Andrew Janowczyk'
pyproject_path = "../../pyproject.toml"
pyproject_data = toml.load(pyproject_path)

release = pyproject_data["project"]["version"]

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx_design',
    'myst_parser',
]

# Allow .md files as source
source_suffix = {
    ".md": "markdown",
}

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'
html_static_path = ['_static']

# Add custom JavaScript to set dark mode as default
html_js_files = [
    'set_default_dark_mode.js',
]

# Add custom CSS for further customization
html_css_files = [
    'custom.css',
]