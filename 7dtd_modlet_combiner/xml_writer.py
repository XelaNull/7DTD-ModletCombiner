"""
XML Writer for 7 Days to Die Modlet Combiner

This class handles writing XML content to files, ensuring proper formatting and validation.

Classes that call this class:
    - ModletWriter

Methods called from this class:
    - write: Called from ModletWriter
    - validate_all_files: Called from ModletWriter after all files are written
    - check_total_filesize: Called from ModletWriter after all files are written

Visual map:
ModletWriter
    |
    v
XMLWriter
    |
    |-- write
    |-- validate_all_files
    |-- check_total_filesize
    |-- _validate_xml
    |-- _update_file_size
    |-- ensure_file_exists
    |-- get_file_hash
    |-- get_summary
    |-- pretty_print
"""

import os
import xml.etree.ElementTree as ET
import xml.dom.minidom
from .mc_logger import info, error, warning
from .utilities import get_file_hash
from .configuration import get_config, versioned
from .mc_logger import debug
from typing import List, Dict
import logging
from lxml import etree

@versioned("1.3.1")
class XMLWriter:
    def __init__(self):
        self.total_size = 0
        self.original_total_size = 0
        self.written_files: Dict[str, int] = {}  # Store file paths and their sizes
        self.file_char_counts: Dict[str, int] = {}  # Store character counts for each file
        self.logger = logging.getLogger('7DTD-ModletCombiner')

    def write(self, file_path: str, content: str) -> None:
        """
        Write XML content to a file.

        Args:
            file_path (str): Path to the XML file
            content (str): XML content to write
        """
        try:
            self.logger.debug(f"Content to write: {content[:500]}...")  # Log first 500 characters

            # Pretty print the XML content
            pretty_xml = self.pretty_print(content)

            # Write the pretty-printed XML to the file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(pretty_xml)

            self._validate_xml(file_path)
            self._update_file_size(file_path, len(pretty_xml))
            self._update_char_count(file_path, pretty_xml)

        except ET.ParseError as e:
            error(f"Error parsing XML content for file {file_path}: {str(e)}")
        except IOError as e:
            error(f"Error writing to file {file_path}: {str(e)}")
        except Exception as e:
            error(f"Unexpected error writing XML file {file_path}: {str(e)}")

    def _validate_xml(self, file_path: str) -> None:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add root element for validation
            #content = f"{content}"
            
            ET.fromstring(content)  # This will raise an exception if the XML is invalid
            debug(f"Validated XML file: {file_path}")
        except ET.ParseError as e:
            error(f"Invalid XML in file {file_path}: {str(e)}")
        except Exception as e:
            error(f"Error validating XML file {file_path}: {str(e)}")

    def _update_file_size(self, file_path: str, content_size: int) -> None:
        """
        Update the total file size and store individual file sizes.

        Args:
            file_path (str): Path to the XML file
            content_size (int): Size of the content written
        """
        file_size = os.path.getsize(file_path)
        self.total_size += file_size
        self.original_total_size += content_size
        self.written_files[file_path] = file_size

    def _update_char_count(self, file_path: str, content: str) -> None:
        """
        Update the character count for the given file.

        Args:
            file_path (str): Path to the XML file
            content (str): Content written to the file
        """
        char_count = len(content)
        if file_path in self.file_char_counts:
            self.file_char_counts[file_path] += char_count
        else:
            self.file_char_counts[file_path] = char_count

    def ensure_file_exists(self, file_path: str) -> None:
        """
        Ensure that the file exists and is empty before writing.

        Args:
            file_path (str): Path to the XML file
        """
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if not os.path.exists(file_path):
            open(file_path, 'a').close()
        elif os.path.getsize(file_path) > 0:
            warning(f"File {file_path} is not empty. It will be appended to.")

    def get_file_hash(self, file_path: str) -> str:
        """
        Get the SHA256 hash of the XML file.

        Args:
            file_path (str): Path to the XML file

        Returns:
            str: SHA256 hash of the file
        """
        return get_file_hash(file_path)

    def get_summary(self) -> str:
        """
        Get a summary of the XML writing process.

        Returns:
            str: Summary of the XML writing process
        """
        summary = f"Total XML content written: {self.total_size} bytes. " \
                  f"Original content size: {self.original_total_size} bytes. " \
                  f"Difference: {abs(self.total_size - self.original_total_size)} bytes " \
                  f"({abs(self.total_size - self.original_total_size) / self.original_total_size * 100:.2f}%)\n"
        
        summary += "Character counts per file:\n"
        for file_path, char_count in self.file_char_counts.items():
            summary += f"{file_path}: {char_count} characters\n"

        return summary

    def pretty_print(self, content: str) -> str:
        """
        Pretty print the XML content.

        Args:
            content (str): XML content to pretty print

        Returns:
            str: Pretty printed XML content
        """
        try:
            # Remove XML declaration and root 'xml' tag
            content = content.replace('<?xml version="1.0" ?>', '').strip()
            if content.startswith('<xml>') and content.endswith('</xml>'):
                content = content[5:-6].strip()

            dom = xml.dom.minidom.parseString(f"<root>{content}</root>")
            pretty_xml = dom.toprettyxml(indent="  ")
            
            # Remove added root tags and clean up empty lines
            pretty_xml = pretty_xml.replace('<?xml version="1.0" ?>\n', '')
            pretty_xml = pretty_xml.replace('<root>\n', '').replace('</root>', '')
            pretty_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])
            
            return pretty_xml
        except Exception as e:
            error(f"Error pretty printing XML content: {str(e)}")
            return content

    def validate_all_files(self) -> None:
        """
        Perform a sanity check on all written files to ensure they are valid XML files.
        """
        for file_path in self.written_files:
            try:
                self._validate_xml(file_path)
                debug(f"Validated XML file: {file_path}")
            except ET.ParseError as e:
                error(f"Invalid XML in file {file_path}: {str(e)}")

    def check_total_filesize(self) -> bool:
        """
        Check if the total filesize of all written files is within 5% of the original summed file sizes.

        Returns:
            bool: True if within 5%, False otherwise
        """
        total_written_size = sum(self.written_files.values())
        difference = abs(total_written_size - self.original_total_size)
        percentage_difference = (difference / self.original_total_size) * 100

        if percentage_difference <= 5:
            debug(f"Total filesize is within 5% of original size. Difference: {percentage_difference:.2f}%")
            return True
        else:
            warning(f"Total filesize differs by more than 5% from the original size. Difference: {percentage_difference:.2f}%")
            return False
