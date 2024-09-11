"""
Modlet Finder for 7 Days to Die Modlet Combiner

This class searches for ModInfo.xml files and forms a master listing of modlets to be combined.

Classes that call this class:
    - modletCombiner.py (main script)

Methods called from this class:
    - find_modlets: Called from the main script
    - get_summary: Called from the main script

Visual map:
[modlet_finder.py] -> [File System]
                   <- [modletCombiner.py]
                   -> [db_processor.py]
                   -> [file_locator.py]
"""

import os
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, Any
from .mc_logger import info, error, warning, debug
from .db_processor import DBProcessor
from .file_locator import FileLocator
from .configuration import get_config, versioned
import hashlib

@versioned("1.3.3")
class ModletFinder:
    def __init__(self, source_path: str, additional_skip_dirs: Optional[List[str]] = None):
        self.source_path = os.path.abspath(source_path)
        self.skip_dirs = set(['.git', '__pycache__'] + (additional_skip_dirs or []))
        self.db_processor = DBProcessor()
        self.file_locator = FileLocator([self.source_path])
        self.skip_directories = get_config('SKIP_DIRECTORIES', '.git,__pycache__,CombinedModlet').split(',')
        if additional_skip_dirs:
            self.skip_directories.extend(additional_skip_dirs)

    def find_modlets(self) -> List[Dict[str, str]]:
        """
        Search for ModInfo.xml files and return a list of modlet information.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing modlet information
        """
        modlets = []
        for root, dirs, files in os.walk(self.source_path):
            # Remove directories to skip from the dirs list
            dirs[:] = [d for d in dirs if d not in self.skip_directories]

            if 'ModInfo.xml' in files:
                modinfo_path = os.path.join(root, 'ModInfo.xml')
                debug(f"[ModletFinder] ############################################################")
                debug(f"[ModletFinder] Found ModInfo.xml at: {modinfo_path}")
                modlet_info = self._parse_modinfo(modinfo_path)
                if modlet_info:
                    modlets.append(modlet_info)
                    try:
                        self.db_processor.store_modlet_info(modlet_info)
                        self._process_modlet_files(root, modlet_info)
                    except Exception as e:
                        error(f"Error storing modlet info for {modinfo_path}: {str(e)}")

        debug(f"[ModletFinder] Total modlets found & processed: {len(modlets)}")
        
        return modlets

    def _process_modlet_files(self, root, modlet_info):
        debug(f"[ModletFinder] Processing files for modlet: {modlet_info['name']}")
        
        # Locate XML files within this modlet's directory, explicitly excluding ModInfo.xml
        xml_files = self.file_locator.locate_files('.xml', path=root, exclude=["ModInfo.xml"])
        
        for xml_file in xml_files:
            self.file_locator.process_files(modlet_info["name"], modlet_info["unique_id"], xml_file)
        
        # Process Localization.txt files within this modlet's directory
        localization_files = self.file_locator.locate_files('Localization.txt', path=root)
        for loc_file in localization_files:
            self.file_locator.process_files(modlet_info["name"], modlet_info["unique_id"], loc_file)

    def _parse_modinfo(self, modinfo_path: str) -> Dict[str, str]:
        """
        Parse a ModInfo.xml file and extract modlet information.

        Args:
            modinfo_path (str): Path to the ModInfo.xml file

        Returns:
            Dict[str, str]: A dictionary containing modlet information
        """
        try:
            tree = ET.parse(modinfo_path)
            root = tree.getroot()
            
            modlet_info = {
                'name': root.find('Name').get('value') if root.find('Name') is not None else '',
                'description': root.find('Description').get('value') if root.find('Description') is not None else '',
                'author': root.find('Author').get('value') if root.find('Author') is not None else '',
                'version': root.find('Version').get('value') if root.find('Version') is not None else '',
                'website': root.find('Website').get('value') if root.find('Website') is not None else ''
            }
            
            # Generate unique_id
            unique_id = hashlib.md5(f"{modlet_info['name']}_{modlet_info['version']}".encode()).hexdigest()
            modlet_info['unique_id'] = unique_id

            # Ensure no None values are in the dictionary
            modlet_info = {k: v if v is not None else '' for k, v in modlet_info.items()}
            
            debug(f"[ModletFinder] Parsed ModInfo.xml at {modinfo_path}: {modlet_info}")
            
            return modlet_info
        except ET.ParseError as e:
            error(f"[ModletFinder] Error parsing ModInfo.xml at {modinfo_path}: {str(e)}")
        except Exception as e:
            error(f"[ModletFinder] Unexpected error parsing ModInfo.xml at {modinfo_path}: {str(e)}")
        return {}

    def get_summary(self) -> str:
        """
        Return a summary of the modlet search results.

        Returns:
            str: A summary string
        """
        modlets = self.find_modlets()
        xml_files, localization_files = self.file_locator.get_file_counts()
        return f"[ModletFinder] Found {len(modlets)} modlets, {xml_files} XML files, and {localization_files} Localization files in {self.source_path}"
