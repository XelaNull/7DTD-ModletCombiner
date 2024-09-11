"""
Localization Parser for 7 Days to Die Modlet Combiner

This class parses Localization.txt files and extracts their contents.

Classes that call this class:
    - FileLocator

Methods called from this class:
    - parse: Called from FileLocator

Visual map:
[parser_localization.py] <- [file_locator.py]
                         -> [db_processor.py]
"""

import base64
from typing import List
from .mc_logger import info, warning, error, debug
from .db_processor import DBProcessor
from .configuration import get_config, versioned
import csv
from io import StringIO

@versioned("1.3.4")
class LocalizationParser:
    def __init__(self):
        self.db_processor = DBProcessor()
        self.encoding = get_config('LOCALIZATION_ENCODING', 'utf-8')

    def parse(self, file_path, modlet_name, unique_id, content=None):
        """
        Parse a Localization.txt file and extract all lines after the first row.

        Args:
            file_path (str): Full path to the Localization.txt file
            modlet_name (str): Name of the modlet
            unique_id (str): Unique identifier for the modlet
            content (str, optional): Content of the Localization.txt file
        """
        
        if content is None:
            with open(file_path, 'r', encoding=self.encoding) as file:
                content = file.read()
        
        csv_reader = csv.reader(StringIO(content), delimiter=',', quotechar='"')
        
        short_path = self._get_short_path(file_path)
        
        # Skip the header row
        next(csv_reader, None)
        
        for line_number, row in enumerate(csv_reader, 2):  # Start from 2 to account for header
            if not row:
                debug(f"[LocalizationParser] Skipping empty line {line_number} in file {file_path}")
                continue
            
            if row[0].startswith('#'):
                debug(f"[LocalizationParser] Skipping comment line {line_number} in file {file_path}")
                continue
            
            if len(row) < 20:  # Ensure we have all expected columns
                warning(f"[LocalizationParser] Line {line_number} in file {file_path} has insufficient columns: {row}")
                continue
            
            key, file, type, used_in_main_menu, no_translate, english, *other_languages = row[:20]
            
            # Store the localization data
            self.db_processor.store_localization_data(
                modlet_name, unique_id, file_path, short_path,
                file, used_in_main_menu, no_translate, type, key,
                english, *other_languages  # Use English as the default value
            )

        # Add a summary at the end of parsing
        debug(f"[LocalizationParser] Finished parsing {file_path}. Processed {line_number - 1} lines.")

    def count_characters(self, content: str) -> int:
        """
        Count the number of characters in the content.

        Args:
            content (str): Content to count characters from

        Returns:
            int: Number of characters in the content
        """
        return len(content)

    def _get_short_path(self, full_path: str) -> str:
        """
        Get the short path (relative to the source path) from the full path.

        Args:
            full_path (str): Full path to the Localization.txt file

        Returns:
            str: Short path relative to the source path
        """
        return '/'.join(full_path.split('/')[-2:])

    def _validate_stored_data(self, full_path: str, short_path: str, original_char_count: int) -> None:
        """
        Validate the stored Localization data against the original file.

        Args:
            full_path (str): Full path to the Localization.txt file
            short_path (str): Short path to the Localization.txt file
            original_char_count (int): Character count of the original file
        """
        stored_data = self.db_processor.get_localization_data(full_path, short_path)
        stored_char_count = sum(len(line) for line in stored_data)

        difference_percentage = abs(stored_char_count - original_char_count) / original_char_count * 100

        if difference_percentage > 5:
            warning(f"[LocalizationParser] Stored Localization data for {full_path} differs by {difference_percentage:.2f}% from the original file")
        else:
            debug(f"[LocalizationParser] Validation successful for {full_path}. Difference: {difference_percentage:.2f}%")

    def get_summary(self, full_path: str) -> str:
        """
        Return a summary of the parsed Localization file.

        Args:
            full_path (str): Full path to the Localization.txt file

        Returns:
            str: A summary string
        """
        short_path = self._get_short_path(full_path)
        stored_data = self.db_processor.get_localization_data(full_path, short_path)
        line_count = len(stored_data.split('\n'))
        return f"[LocalizationParser] Parsed Localization file {full_path}: {line_count} lines stored"

    def merge_localization_data(self, localization_data: List[str]) -> str:
        """
        Merge multiple Localization.txt file contents.

        Args:
            localization_data (List[str]): List of Localization.txt file contents

        Returns:
            str: Merged Localization data
        """
        merged_data = {}
        for data in localization_data:
            for line in data.split('\n'):
                if ',' in line:
                    key, value = line.split(',', 1)
                    merged_data[key.strip()] = value.strip()

        return '\n'.join([f"{key},{value}" for key, value in merged_data.items()])

    def calculate_difference(self, original, stored):
        if original == stored:
            return 0
        
        # Calculate the difference
        changes = 0
        for i in range(min(len(original), len(stored))):
            if original[i] != stored[i]:
                changes += 1
        changes += abs(len(original) - len(stored))
        
        return (changes / max(len(original), len(stored))) * 100
