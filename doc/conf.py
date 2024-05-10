# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

topdir = os.path.split(os.path.split(__file__)[0])[0]
sys.path.insert(0, os.path.join(topdir, "src/server"))
sys.path.insert(0, os.path.join(topdir, "src/server/util"))
sys.path.insert(0, os.path.join(topdir, "src/interface"))

from server import RELEASE_VERSION

project = 'RotorHazard'
copyright = '2024, Michael Niggel and other contributors'
author = 'Michael Niggel and other contributors'
version = RELEASE_VERSION.split("-")[0]
release = RELEASE_VERSION

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_book_theme'
html_static_path = ['_static']
html_logo = "../src/server/static/image/RotorHazard Logo.svg"
html_title = "RotorHazard Documentation"

html_theme_options = {
    "repository_url": "https://github.com/RotorHazard/RotorHazard",
    "use_repository_button": True,
}

extensions = [
              'sphinx_copybutton',
              ]