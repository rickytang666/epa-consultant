"""Prompt template loading utilities."""

import os
from jinja2 import Environment, FileSystemLoader

# Set up Jinja environment with templates directory
_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
_env = Environment(loader=FileSystemLoader(_TEMPLATE_DIR))


def get_header_correction_template():
    """Load the header correction prompt template."""
    return _env.get_template("header_correction.jinja2")


def get_section_summary_template():
    """Load the section summary prompt template."""
    return _env.get_template("section_summary.jinja2")
