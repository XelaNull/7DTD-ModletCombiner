"""
Utilities for 7 Days to Die Modlet Combiner

This module contains utility functions used throughout the project.

Functions:
    - format_number: Format a number with commas and a space
    - check_dependencies: Check if required dependencies are installed
    - shorten_text: Shorten a text string to a specified maximum length
    - install_dependency: Attempt to install a missing dependency
    - update_dependency: Attempt to update a dependency to the latest version
    - update_all_dependencies: Update all installed dependencies
"""

import subprocess
import sys
import json
from typing import List
from .mc_logger import info, error, warning


def format_number(number: int) -> str:
    """
    Format a number with commas and a space.

    Args:
        number (int): The number to format.

    Returns:
        str: The formatted number.
    """
    return f'{number:,}'

def check_dependencies() -> bool:
    """Check if the required dependencies are available."""
    try:
        import lxml
        import sqlite3
        return True
    except ImportError as e:
        error(f"Required dependency not found: {e}")
        return False

def shorten_text(value: str, max_length: int = 50) -> str:
    """
    Shorten the given text to a maximum length, preventing line wraps.

    Args:
        value (str): The input text to be shortened.
        max_length (int, optional): The maximum length of the output string. Defaults to 50.

    Returns:
        str: The shortened text.
    """
    # Remove any leading/trailing whitespace
    value = value.strip()
    
    # Find the first occurrence of a linefeed character
    linefeed_index = value.find('\n')
    
    # If a linefeed is found, truncate the string at that point
    if linefeed_index != -1:
        value = value[:linefeed_index]
    
    # If the remaining text is longer than max_length, truncate it
    if len(value) > max_length:
        value = value[:max_length - 3] + '...'
    
    return value

def install_dependency(package: str) -> bool:
    """
    Attempt to install a missing dependency.

    Args:
        package (str): The name of the package to install.

    Returns:
        bool: True if installation was successful, False otherwise.
    """
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        info(f"Successfully installed {package}")
        return True
    except subprocess.CalledProcessError:
        error(f"Failed to install {package}")
        return False

def update_dependency(package: str) -> bool:
    """
    Attempt to update a dependency to the latest version.

    Args:
        package (str): The name of the package to update.

    Returns:
        bool: True if update was successful, False otherwise.
    """
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", package])
        info(f"Successfully updated {package}")
        return True
    except subprocess.CalledProcessError:
        error(f"Failed to update {package}")
        return False

def update_all_dependencies() -> List[str]:
    """
    Update all installed dependencies to their latest versions.

    Returns:
        List[str]: A list of packages that failed to update.
    """
    try:
        output = subprocess.check_output([sys.executable, "-m", "pip", "list", "--outdated", "--format=json"])
        outdated_packages = json.loads(output)
        failed_updates = []
        for package in outdated_packages:
            if not update_dependency(package['name']):
                failed_updates.append(package['name'])
        return failed_updates
    except subprocess.CalledProcessError:
        error("Failed to check for outdated packages")
    return []

def is_valid_path(path: str) -> bool:
    """
    Check if a given path is valid and accessible.

    Args:
        path (str): The path to check.

    Returns:
        bool: True if the path is valid and accessible, False otherwise.
    """
    import os
    return os.path.exists(path) and os.access(path, os.R_OK)

def create_directory(path: str) -> bool:
    """
    Create a directory if it doesn't exist.

    Args:
        path (str): The path of the directory to create.

    Returns:
        bool: True if the directory was created or already exists, False otherwise.
    """
    import os
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except OSError:
        error(f"Failed to create directory: {path}")
        return False

def get_file_hash(file_path: str) -> str:
    """
    Calculate the SHA256 hash of a file.

    Args:
        file_path (str): The path to the file.

    Returns:
        str: The SHA256 hash of the file.
    """
    import hashlib
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()
