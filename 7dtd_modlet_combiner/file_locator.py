"""
File Locator for 7 Days to Die Modlet Combiner

This class searches for XML and Localization.txt files in the source path and creates a list of files to be processed.

Classes that call this class:
    - ModletFinder

Methods called from this class:
    - locate_files: Called from ModletFinder
    - process_files: Called after locate_files to parse and process the found files
    - get_file_counts: Called from ModletFinder

Visual map:
[file_locator.py] -> [File System]
                  <- [modlet_finder.py]
                  -> [parser_xml.py]
                  -> [parser_localization.py]
"""

import os
from typing import List, Dict
from .mc_logger import info, error, warning, debug
from .configuration import get_config, versioned
from .parser_xml import XMLParser
from .parser_localization import LocalizationParser

@versioned("1.3.1")
class FileLocator:
    def __init__(self, source_paths: List[str]):
        self.source_paths = source_paths
        self.xml_files: List[str] = []
        self.localization_files: List[str] = []
        self.total_char_count = 0
        self.xml_parser = XMLParser()
        self.localization_parser = LocalizationParser()

    def locate_files(self, file_type, path=None, exclude=None):
        """
        Locate files of a specific type in the given directory.

        Args:
            file_type (str): The file type to search for ('.xml' or 'Localization.txt')
            path (str, optional): The specific path to search. If None, uses self.source_paths
            exclude (List[str], optional): List of directories to exclude

        Returns:
            List[str]: A list of file paths matching the file type
        """
        found_files = []
        search_paths = [path] if path else self.source_paths
        for directory in search_paths:
            for root, _, files in os.walk(directory):
                if exclude and any(ex in root for ex in exclude):
                    continue
                for file in files:
                    if file_type == '.xml' and file.endswith('.xml'):
                        full_path = os.path.join(root, file)
                        found_files.append(full_path)
                        self.xml_files.append(full_path)
                    elif file_type == 'Localization.txt' and file.lower() == 'localization.txt':
                        full_path = os.path.join(root, file)
                        found_files.append(full_path)
                        self.localization_files.append(full_path)

        return found_files

    def process_files(self, modlet_name: str, unique_id: str, path: str) -> None:
        """
        Process the located files using the appropriate parsers.

        Args:
            modlet_name (str): Name of the modlet
            unique_id (str): Unique identifier for the modlet
            path (str): The specific path to process files from
        """
        xml_files = [f for f in self.xml_files if f.startswith(path)]
        localization_files = [f for f in self.localization_files if f.startswith(path)]

        for xml_file in xml_files:
            self._process_xml_file(xml_file, modlet_name, unique_id)

        for localization_file in localization_files:
            self._process_localization_file(localization_file, modlet_name, unique_id)

    def _process_xml_file(self, file_path: str, modlet_name: str, unique_id: str) -> None:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.total_char_count += len(content)
            self.xml_parser.parse(file_path, modlet_name, unique_id, content)
        except Exception as e:
            error(f"[FileLocator] Error processing XML file {file_path}: {str(e)}")

    def _process_localization_file(self, file_path: str, modlet_name: str, unique_id: str) -> None:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.total_char_count += len(content)
            debug(f"[FileLocator] Total character count: {self.total_char_count}")
            self.localization_parser.parse(file_path, modlet_name, unique_id, content)
            debug(f"[FileLocator] Finished processing Localization file {file_path}")
        except Exception as e:
            error(f"[FileLocator] Error processing Localization file {file_path}: {str(e)}")

    def get_file_counts(self) -> tuple[int, int]:
        """
        Get the count of XML and Localization files.

        Returns:
            Tuple[int, int]: Count of XML files and Localization files
        """
        return len(self.xml_files), len(self.localization_files)

    def get_total_char_count(self) -> int:
        """
        Get the total character count of all processed files.

        Returns:
            int: Total character count
        """
        return self.total_char_count

    def get_summary(self) -> str:
        """
        Returns a summary of the file locating and processing results.

        Returns:
            str: A summary string
        """
        return f"[FileLocator] Found {len(self.xml_files)} XML files and {len(self.localization_files)} Localization files. Total character count: {self.total_char_count}"
