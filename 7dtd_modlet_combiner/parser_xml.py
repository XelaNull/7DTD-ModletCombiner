"""
XML Parser for 7 Days to Die Modlet Combiner

This class parses XML files and extracts outer XML tags and their contents.

Classes that call this class:
    - FileLocator

Methods called from this class:
    - parse: Called from FileLocator

Visual map:
[parser_xml.py] <- [file_locator.py]
                -> [db_processor.py]
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple
from .mc_logger import info, error, warning, debug
from .db_processor import DBProcessor
from .configuration import get_config, versioned
from .utilities import shorten_text
import logging
import re
from lxml import etree

@versioned("1.3.2")
class XMLParser:
    def __init__(self):
        self.logger = logging.getLogger('7DTD-ModletCombiner')
        self.db_processor = DBProcessor()

    def _read_file_with_fallback_encoding(self, file_path):
        encodings = ['utf-8', 'latin-1', 'ascii']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    return file.read()
            except UnicodeDecodeError:
                continue
        
        error(f"[XMLParser] Unable to read file {file_path} with any of the attempted encodings")
        return None
    

    def parse(self, file_path, modlet_name, unique_id, content=None):
        try:
            if content is None:
                debug(f"[XMLParser] Reading file: {file_path}")
                with open(file_path, 'r', encoding='utf-8-sig') as file:
                    content = file.read()
            
            # Remove any leading whitespace or hidden characters
            content = content.lstrip()
            
            # Ensure the XML declaration is at the start
            if not content.startswith('<?xml'):
                content = '<?xml version="1.0" encoding="UTF-8"?>\n' + content

            root = ET.fromstring(content)
            outer_tag = root.tag
            short_path = self._get_short_path(file_path)

            # Extract content inside the root tag, excluding the root tag itself
            xml_content = '\n'.join(ET.tostring(child, encoding='unicode', method='xml').strip() for child in root)
            
            debug(f"[XMLParser] Parsed XML for {file_path}")
            debug(f"[XMLParser] Outer tag: {outer_tag}")
            debug(f"[XMLParser] Content preview: {xml_content[:100]}...")  # Log first 100 characters of content

            self.db_processor.store_xml_data(modlet_name, unique_id, file_path, short_path, outer_tag, xml_content)
            
            debug(f"[XMLParser] Stored XML data for {file_path}")
        except ET.ParseError as e:
            error(f"[XMLParser] Error parsing XML file {file_path}: {str(e)}")
        except Exception as e:
            error(f"[XMLParser] Unexpected error processing XML file {file_path}: {str(e)}")


    def _get_short_path(self, full_path):
        try:
            return full_path.split('/')[-1]
        except Exception as e:
            warning(f"[XMLParser] Error getting short path for {full_path}: {str(e)}")
            return full_path

    def _decode_stored_data(self, stored_data):
        encodings = ['utf-8', 'latin-1', 'ascii']
        for encoding in encodings:
            try:
                return stored_data.decode(encoding)
            except UnicodeDecodeError:
                continue
        
        error(f"[XMLParser] Unable to decode stored data with any of the attempted encodings")
        return None
    
    def _validate_stored_data(self, file_path, short_path, outer_tag, original_content):
        try:
            stored_data = self.db_processor.get_xml_data(file_path, short_path, outer_tag)
            if stored_data is not None:
                try:
                    stored_content = stored_data
                except UnicodeDecodeError:
                    # If decoding fails, treat stored_data as bytes
                    stored_content = stored_data

                if stored_content is not None:
                    # Convert original_content to bytes for comparison if stored_content is bytes
                    if isinstance(stored_content, bytes):
                        original_content = original_content.encode('utf-8')

                    if stored_content != original_content:
                        difference_percentage = self._calculate_difference_percentage(str(original_content), str(stored_content))
                        if difference_percentage > 10:
                            warning(f"[XMLParser] Stored XML data for {file_path} differs by {difference_percentage:.2f}% from the original file")
                        else:
                            debug(f"[XMLParser] Minor difference ({difference_percentage:.2f}%) detected in stored XML data for {file_path}")
                    else:
                        debug(f"[XMLParser] Post-Storage Validation OK: {file_path}.")
                else:
                    warning(f"[XMLParser] Unable to decode or compare stored data for {file_path}. Skipping validation.")
            else:
                warning(f"[XMLParser] No stored data found for {file_path}")
        except Exception as e:
            error(f"[XMLParser] Error validating stored data for {file_path}: {str(e)}")

    def _calculate_difference_percentage(self, original, stored):
        try:
            if original == stored:
                return 0
            changes = sum(1 for a, b in zip(original, stored) if a != b)
            changes += abs(len(original) - len(stored))
            return (changes / max(len(original), len(stored))) * 100
        except Exception as e:
            error(f"[XMLParser] Error calculating difference percentage: {str(e)}")
            return 100  # Assume 100% difference in case of error

    def count_characters(self, content: str) -> int:
        try:
            return len(content)
        except Exception as e:
            error(f"[XMLParser] Error counting characters: {str(e)}")
            return 0

    def extract_outer_tags(self, root: ET.Element) -> List[Tuple[str, str]]:
        try:
            outer_tags = []
            for child in root:
                outer_tag = child.tag
                tag_content = ET.tostring(child, encoding='unicode')
                outer_tags.append((outer_tag, tag_content))
            return outer_tags
        except Exception as e:
            error(f"[XMLParser] Error extracting outer tags: {str(e)}")
            return []

    def _merge_xml_content(self, existing_content: str, new_content: str) -> str:
        try:
            existing_root = ET.fromstring(existing_content)
            new_root = ET.fromstring(new_content)

            for element in new_root:
                existing_element = existing_root.find(element.tag)
                if existing_element is not None:
                    existing_element.extend(element)
                else:
                    existing_root.append(element)

            return ET.tostring(existing_root, encoding='unicode')
        except Exception as e:
            error(f"[XMLParser] Error merging XML content: {str(e)}")
            return existing_content

    def handle_namespaces(self, content: str) -> str:
        try:
            root = ET.fromstring(content)
            for elem in root.iter():
                if '}' in elem.tag:
                    elem.tag = elem.tag.split('}', 1)[1]
            return ET.tostring(root, encoding='unicode')
        except ET.ParseError as e:
            error(f"[XMLParser] Error handling namespaces: {str(e)}")
            return content
        except Exception as e:
            error(f"[XMLParser] Unexpected error handling namespaces: {str(e)}")
            return content

    def _extract_inner_content(self, root):
        """Extract the contents of the outer tag."""
        return ''.join(ET.tostring(child, encoding='unicode') for child in root)
