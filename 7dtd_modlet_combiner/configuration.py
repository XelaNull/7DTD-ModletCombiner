"""
Configuration module for 7 Days to Die Modlet Combiner

This module contains global variables and decorator functions used throughout the script.
It also handles loading configuration values from a .env file.

Classes that use this module:
    - All classes in the project

Methods called from this module:
    - load_config: Called at the start of the main script

Visual map:
[configuration.py] <- [All other modules]
"""

import os
import functools
from functools import wraps
from configparser import ConfigParser, ExtendedInterpolation
from typing import Any, Callable


# Global variables
CONFIG_FILE = '.env'
SKIP_DIRECTORIES = ['.git', '__pycache__']
    
###### Language Settings ######
# Localization.txt standard file header
EXPECTED_HEADER = ['Key', 'File', 'Type', 'UsedInMainMenu', 'NoTranslate', 'english', 'Context / Alternate Text', 'german', 'latam', 'french', 'italian', 'japanese', 'koreana', 'polish', 'brazilian', 'russian', 'turkish', 'schinese', 'tchinese', 'spanish']

# Languages to translate to
TARGET_LANGUAGES = EXPECTED_HEADER[7:]  # This will include all languages starting from 'german'

# Columns that should be quoted in the Localization.translated.txt
QUOTED_COLUMNS = ['english', 'Context / Alternate Text'] + TARGET_LANGUAGES

# SQL aliases for the SQLite CLI
CLI_ALIASES = {
    '.tables': "SELECT name FROM sqlite_master WHERE type='table';",
    '.schema': "SELECT sql FROM sqlite_master WHERE type='table';",
    '.dbinfo': "SELECT * FROM sqlite_master;",
    '.columns': "SELECT name FROM pragma_table_info(?);",  # This one needs a table name as an argument
    '.size': "SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size();",
    '.modlets': "SELECT name, description FROM modlets;",
    '.modlets_describe': "PRAGMA table_info(modlets);",
    '.xml_data': "SELECT * FROM xml_data;",
    '.xml_data_describe': "PRAGMA table_info(xml_data);",
    '.localization_data': "SELECT * FROM localization_data;",
    '.localization_data_describe': "PRAGMA table_info(localization_data);",
    '.help': "Commands: .tables, .schema, .dbinfo, .columns, .size, .modlets, .modlets_describe, .xml_data, .xml_data_describe, .localization_data, .localization_data_describe, .help"
}

def versioned(version):
    """
    Decorator to track the version of the class.
    """
    def decorator(cls):
        cls._version = version
        return cls
    return decorator

def todo(message: str):
    """
    Decorator to mark functions that need further implementation.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            print(f"TODO: {message}")
            return func(*args, **kwargs)
        return wrapper
    return decorator

def load_config() -> None:
    """
    Load configuration from .env file.
    """
    config = ConfigParser(interpolation=None)  # Disable interpolation
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            # Read the file and add a default section
            config.read_string("[DEFAULT]\n" + f.read())
    else:
        config['DEFAULT'] = {
            'LOG_LEVEL': 'INFO',
            'DB_FILE': 'modlets.db',
            'ENCODING': 'base64',
            'LOG_RETENTION_DAYS': '30',
            'ADDITIONAL_SKIP_DIRECTORIES': '',
            'LOG_FORMAT': '%(levelname)s - %(message)s',  # Set a default log format
        }
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)
    
    # Set environment variables
    for key, value in config['DEFAULT'].items():
        os.environ[key] = value

def get_config(key: str, default: Any = None) -> Any:
    """
    Get a configuration value from the environment.

    Args:
        key (str): The configuration key to retrieve.
        default (Any, optional): The default value if the key is not found.

    Returns:
        Any: The configuration value.
    """
    return os.environ.get(key, default)

# Initialize configuration when this module is imported
load_config()
