"""
7 Days to Die Modlet Combiner

This package contains modules for combining multiple 7 Days to Die modlets into a single modlet.

Modules:
    modletCombiner: Main script for combining modlets
    configuration: Handles configuration and versioning
    utilities: Utility functions used across the project
    mc_logger: Custom logging functionality
    db_processor: Database operations for storing and retrieving modlet data
    modlet_finder: Locates modlets in the specified directory
    file_locator: Locates and categorizes files within modlets
    parser_xml: Parses XML files
    parser_localization: Parses Localization files
    modlet_writer: Writes the combined modlet
    xml_writer: Handles XML file writing operations
"""

__version__ = "1.0.0"

from . import modletCombiner
from . import configuration
from . import utilities
from . import mc_logger
from . import db_processor
from . import modlet_finder
from . import file_locator
from . import parser_xml
from . import parser_localization
from . import modlet_writer
from . import xml_writer

# Expose main function for easy access
main = modletCombiner.main
