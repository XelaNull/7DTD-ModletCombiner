"""
Modlet Writer for 7 Days to Die Modlet Combiner

This class handles the creation of the combined modlet, including the ModInfo.xml file,
Localization.txt file, and all XML files.

Classes that call this class:
    - modletCombiner.py (main script)

Methods called from this class:
    - write_modlet: Called from the main script

Visual map:
[modlet_writer.py] <- [modletCombiner.py]
                   -> [db_processor.py]
                   -> [xml_writer.py]
"""

import os
import re
import logging
import textwrap
from tabulate import tabulate
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from typing import Dict, Any, List
from .db_processor import DBProcessor
from .xml_writer import XMLWriter
from .mc_logger import info, error, warning, debug
from .configuration import versioned, get_config, QUOTED_COLUMNS, EXPECTED_HEADER

@versioned("1.3.3")
class ModletWriter:
    def __init__(self, output_path: str, db_processor: DBProcessor, args: Dict[str, Any]):
        self.args = args  # Add this line to set args as an attribute
        self.output_path = self._get_output_path(output_path)  # Pass output_path to _get_output_path
        self.db_processor = db_processor
        self.xml_writer = XMLWriter()
        self.logger = logging.getLogger('7DTD-ModletCombiner')
        self.file_xml_block_counts = {}  # New attribute to store XML block counts
        self.modlet_info = None  # Initialize modlet_info as None

    def _get_output_path(self, provided_output_path: str) -> str:
        """
        Get the output path from args or configuration, with a fallback default.
        """
        output_path = provided_output_path or self.args.get('source_path') or get_config('OUTPUT_PATH')
        output_path = os.path.join(output_path, "Combined_Modlet")
        if not output_path:
            output_path = 'combined_modlet'
            error(f"Output path not specified. Using default: {output_path}")
        return output_path

    def reset_output_directory(self) -> None:
        """
        Clear the contents of the output directory, including ModInfo.xml, 
        Localization.txt, and all files in the Config directory.
        """
        try:
            # Get the output path and add on the string "Combined_Modlet
            # This is the name of the modlet that will be created
            output_path = self._get_output_path()+"/Combined_Modlet/"

            # Define paths
            mod_info_path = os.path.join(output_path, 'ModInfo.xml')
            localization_path = os.path.join(output_path, 'Localization.txt')
            config_path = os.path.join(output_path, 'Config')

            # Remove ModInfo.xml if it exists
            if os.path.exists(mod_info_path):
                os.remove(mod_info_path)
                debug(f"[ModletWriter] Cleared {mod_info_path}")

            # Remove Localization.txt if it exists
            if os.path.exists(localization_path):
                os.remove(localization_path)
                debug(f"[ModletWriter] Cleared {localization_path}")

            # Clear all files in the Config directory
            if os.path.exists(config_path):
                for file in os.listdir(config_path):
                    file_path = os.path.join(config_path, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        debug(f"[ModletWriter] Cleared {file_path}")
                # Optionally, remove the Config directory if empty
                if not os.listdir(config_path):
                    os.rmdir(config_path)
                    debug(f"[ModletWriter] Removed empty directory: {config_path}")

        except Exception as e:
            error(f"[ModletWriter] Error resetting output directory: {str(e)}")

    def write_modlet(self, modlet_info: Dict[str, Any]) -> None:
        """
        Write the combined modlet.

        Args:
            modlet_info (Dict[str, Any]): Information about the combined modlet
        """
        self.modlet_info = modlet_info  # Store modlet_info as an attribute
        try:
            self._create_output_directory()
            self._write_modinfo_xml(modlet_info)
            self._write_localization_file()
            self._write_xml_files()
            self.post_process_xml_files()
            self.display_statistics()
        except Exception as e:
            error(f"Error writing combined modlet: {str(e)}")
            raise

    def _create_output_directory(self) -> None:
        """
        Create the output directory and Config folder if they don't exist.
        """
        try:
            os.makedirs(self.output_path, exist_ok=True)
            os.makedirs(os.path.join(self.output_path, 'Config'), exist_ok=True)
        except OSError as e:
            error(f"Error creating output directories: {str(e)}")
            raise

    def _write_modinfo_xml(self, modlet_info: Dict[str, Any]) -> None:
        """
        Create a new ModInfo.xml file with the modlet information.

        Args:
            modlet_info (Dict[str, Any]): Information about the combined modlet
        """
        try:
            mod_info_path = os.path.join(self.output_path, 'ModInfo.xml')
            root = ET.Element("xml")

            # Add Name without spaces
            name_elem = ET.SubElement(root, "Name")
            name_elem.set("value", modlet_info['Name'].replace(" ", "_"))

            # Add DisplayName with spaces
            display_name_elem = ET.SubElement(root, "DisplayName")
            display_name_elem.set("value", modlet_info['Name'])

            # Add Website
            website_elem = ET.SubElement(root, "Website")
            website_elem.set("value", modlet_info.get('Website', ''))

            for key, value in modlet_info.items():
                if key not in ['Name', 'Website']:  # Skip Name and Website as we've already added them
                    element = ET.SubElement(root, key)
                    element.set("value", str(value))

            # Convert to string and pretty print
            xml_str = ET.tostring(root, encoding='unicode')
            dom = minidom.parseString(xml_str)
            pretty_xml = dom.toprettyxml(indent="\t")

            # Remove extra newlines that minidom adds
            pretty_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])

            # Add XML declaration manually to ensure it's on a single line
            pretty_xml = '<?xml version="1.0" encoding="UTF-8" ?>\n' + pretty_xml[pretty_xml.index('<xml'):]

            with open(mod_info_path, 'w', encoding='utf-8') as f:
                f.write(pretty_xml)

            debug(f"[ModletWriter] Wrote ModInfo.xml: {mod_info_path}")
        except ET.ParseError as e:
            error(f"Error creating ModInfo.xml: {str(e)}")
            raise
        except IOError as e:
            error(f"Error writing ModInfo.xml: {str(e)}")
            raise

    def _write_localization_file(self):
        localization_data = self.db_processor.get_localization_data('', '')
        if localization_data:
            localization_file_path = os.path.join(self.output_path, 'Config/Localization.txt')
            try:
                with open(localization_file_path, 'w', encoding='utf-8') as f:
                    # Write the static header
                    f.write(','.join(EXPECTED_HEADER) + '\n')
                    
                    # Write each localization entry
                    for entry in localization_data:
                        line_parts = []
                        for column in EXPECTED_HEADER:
                            value = entry.get(column.lower(), '')  # Use lowercase for dictionary keys
                            if value and column in QUOTED_COLUMNS:
                                value = f'"{value}"'  # Wrap in quotes if non-empty and in QUOTED_COLUMNS
                            line_parts.append(value)
                        
                        line = ','.join(line_parts) + '\n'
                        f.write(line)
                
                debug(f"[ModletWriter] Wrote localization file: {localization_file_path}")
            except UnicodeEncodeError as e:
                error(f"[ModletWriter] Unable to write localization data: {str(e)}")
        else:
            debug("[ModletWriter] No localization data to write")

    def _write_xml_files(self) -> None:
        """
        Write all combined XML files.
        """
        try:
            xml_data = self.db_processor.get_xml_data('', '', '')
            debug(f"Retrieved XML data for {len(xml_data)} files")
            
            for short_path, content in xml_data.items():
                file_path = os.path.join(self.output_path, 'Config', short_path)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                combined_content = []
                xml_block_count = 0
                for outer_tag, tag_contents in content.items():
                    for tag_content in tag_contents:
                        # Get the modlet name for this specific content
                        modlet_name = self.db_processor.get_xml_metadata(short_path, outer_tag, tag_content)['modlet_name']
                        
                        combined_content.append(f"<!-- Start XML_Block: {modlet_name} -->")
                        combined_content.append(tag_content)
                        combined_content.append(f"<!-- End XML_Block: {modlet_name} -->")
                        
                        xml_block_count += 1
                
                full_content = f"<config>\n{' '.join(combined_content)}\n</config>"
                
                debug(f"Writing {len(full_content)} characters to {file_path}")
                debug(f"Content preview: {full_content[:100]}...")
                
                self.xml_writer.write(file_path, full_content)
                self.file_xml_block_counts[short_path] = xml_block_count

            self.xml_writer.validate_all_files()
            self.xml_writer.check_total_filesize()
        except Exception as e:
            error(f"Error writing XML files: {str(e)}")
            raise

    def display_statistics(self):
        """
        Display statistics about the combined modlet files.
        """
        stats = []
        db_xml_data = self.db_processor.get_xml_data('', '', '')

        for short_path, content in db_xml_data.items():
            file_path = os.path.join(self.output_path, 'Config', short_path)
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                db_size = sum(len(''.join(c)) for c in content.values())
                db_xml_block_count = sum(len(c) for c in content.values())
                file_xml_block_count = self.file_xml_block_counts.get(short_path, "Unknown")

                size_difference = file_size - db_size
                size_difference_percent = (size_difference / db_size) * 100 if db_size > 0 else 0

                stats.append([
                    short_path,
                    db_xml_block_count,
                    file_xml_block_count,
                    f"{file_size:,}",
                    f"{db_size:,}",
                    f"{size_difference:+,}",
                    f"{size_difference_percent:.2f}%"
                ])
        self.combined_modlet_stats()
        print("\nCombined Modlet Statistics:")
        print(tabulate(stats, headers=[
            "File", "DB XML Blocks", "File XML Blocks", "File Size (bytes)", 
            "DB Size (bytes)", "Size Difference", "Difference %"
        ], tablefmt="grid"))

    def post_process_xml_files(self):
        """
        Remove only the first level of indentation from all XML files in the output directory.
        """
        config_dir = os.path.join(self.output_path, 'Config')
        for filename in os.listdir(config_dir):
            if filename.endswith('.xml'):
                file_path = os.path.join(config_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as file:
                    lines = file.readlines()
                
                # Process lines to remove only the first level of indentation
                processed_lines = []
                in_config = False
                for line in lines:
                    if '<config>' in line:
                        in_config = True
                        processed_lines.append(line)
                    elif '</config>' in line:
                        in_config = False
                        processed_lines.append(line)
                    elif in_config:
                        # Remove only the first two spaces of indentation if present
                        processed_lines.append(line[2:] if line.startswith('  ') else line)
                    else:
                        processed_lines.append(line)
                
                # Write the processed content back to the file
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.writelines(processed_lines)
                
                debug(f"Post-processed {filename}")

    def combined_modlet_stats(self):
        """
        Display statistics about the combined modlet and its components.
        """
        # Table 1: Combined Modlet Information
        if self.modlet_info:
            combined_info = [
                ["Name", self.modlet_info.get('Name', 'N/A')],
                ["DisplayName", self.modlet_info.get('DisplayName', 'N/A')],
                ["Version", self.modlet_info.get('Version', 'N/A')],
                ["Author", self.modlet_info.get('Author', 'N/A')],
                ["Description", self.modlet_info.get('Description', 'N/A')]
            ]
            print("\nCombined Modlet Information:")
            print(tabulate(combined_info, headers=["Attribute", "Value"], tablefmt="grid"))
        else:
            print("\nCombined Modlet Information not available.")

        # Table 2: Component Modlets
        try:
            component_modlets = self.db_processor.get_all_modlet_info()
            if component_modlets:
                component_info = []
                for modlet in component_modlets:
                    component_info.append([
                        modlet.get('Name', 'N/A'),
                        modlet.get('Version', 'N/A'),
                        modlet.get('Author', 'N/A')
                    ])
                print("\nComponent Modlets:")
                print(tabulate(component_info, headers=["Name", "Version", "Author"], tablefmt="grid"))
            else:
                print("\nNo component modlets found.")
        except Exception as e:
            error(f"Error retrieving component modlet information: {str(e)}")
            print("\nUnable to retrieve component modlet information.")

        # Table 3: Destination File Sizes
        file_sizes = []
        for root, dirs, files in os.walk(self.output_path):
            for file in files:
                file_path = os.path.join(root, file)
                size = os.path.getsize(file_path)
                file_sizes.append([file, f"{size:,} bytes"])
        print("\nDestination File Sizes:")
        print(tabulate(file_sizes, headers=["File", "Size"], tablefmt="grid"))

    def write(self) -> None:
        """
        Write all combined modlet files.
        """
        self._write_modinfo()
        self._write_localization()
        self._write_xml_files()
        self.post_process_xml_files()
        self.combined_modlet_stats()  # Add this line
        info("Finished writing combined modlet files")