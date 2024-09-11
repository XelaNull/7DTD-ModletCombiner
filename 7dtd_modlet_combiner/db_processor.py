"""
DB Processor for 7 Days to Die Modlet Combiner

This class handles database operations for storing and retrieving modlet information,
XML data, and localization data.

Classes that call this class:
    - modletCombiner.py (main script)
    - ModletFinder
    - XMLParser
    - LocalizationParser
    - ModletWriter

Methods called from this class:
    - store_modlet_info: Called from ModletFinder
    - store_xml_data: Called from XMLParser
    - store_localization_data: Called from LocalizationParser
    - get_modlet_info, get_xml_data, get_localization_data: Called from ModletWriter

Visual map:
[db_processor.py] <- [modletCombiner.py]
                  <- [modlet_finder.py]
                  <- [parser_xml.py]
                  <- [parser_localization.py]
                  <- [modlet_writer.py]
                  -> [SQLite Database]

Security considerations:
    - Use parameterized queries to prevent SQL injection
    - Implement proper error handling and logging
    - Use secure database connections (if applicable)
    - Validate and sanitize all input before storing in the database
"""

import sqlite3
import hashlib
import time
import os
import re
import base64
import random
import string
import binascii
import logging
from typing import Dict, Any, List, Union
from .mc_logger import info, error, warning, debug
from .configuration import get_config, versioned
from difflib import SequenceMatcher
from tabulate import tabulate



@versioned("1.3.3")
class DBProcessor:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DBProcessor, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def initialize(self, db_path='modlet_combiner.db', wipe=False):
        """Initialize the database connection."""
        if not self.initialized:
            self.db_path = db_path
            db_file = get_config('DATABASE_FILE', db_path)

            self.conn = sqlite3.connect(db_file)
            
            # Set file permissions to allow writing
            os.chmod(db_file, 0o664)
            
            if wipe:
                self.wipe_database()
            
            self.create_tables()
            self.encoding = get_config('DB_ENCODING', 'base64')
            self.initialized = True

    def create_tables(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS modlets
                     (unique_id TEXT PRIMARY KEY, name TEXT, description TEXT, author TEXT, version TEXT, website TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS xml_data
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, modlet_name TEXT, unique_id TEXT, full_path TEXT, short_path TEXT, outer_tag TEXT, content TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS localization_data
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, modlet_name TEXT, unique_id TEXT, full_path TEXT, short_path TEXT, file TEXT, used_in_main_menu TEXT, no_translate TEXT, type TEXT, key TEXT,  english TEXT, german TEXT, latam TEXT, french TEXT, italian TEXT, japanese TEXT, koreana TEXT, polish TEXT, brazilian TEXT, russian TEXT, turkish TEXT, schinese TEXT, tchinese TEXT, spanish TEXT, value TEXT)''')
        self.conn.commit()

    def _encode_data(self, data: str) -> str:
        if self.encoding == 'base64':
            return base64.b64encode(data.encode('utf-8')).decode('ascii')
        return data

    def _decode_data(self, data: str) -> str:
        if not data:
            return ''
        if self.encoding == 'base64':
            try:
                return base64.b64decode(data.encode('ascii')).decode('utf-8')
            except (binascii.Error, UnicodeDecodeError):
                # If decoding fails, check if the data is already in a readable format
                if all(ord(c) < 128 for c in data):
                    return data
                else:
                    warning(f"Failed to decode data: {data[:20]}... Returning partial data.")
                    return data[:50] + '...' if len(data) > 50 else data
        return data

    def generate_unique_id(self, modlet_info):
        """Generate a unique ID based on the modlet name and version."""
        id_string = f"{modlet_info['name']}_{modlet_info['version']}"
        return hashlib.md5(id_string.encode()).hexdigest()

    def store_modlet_info(self, modlet_info):
        c = self.conn.cursor()
        unique_id = self.generate_unique_id(modlet_info)
        try:
            c.execute('''INSERT OR REPLACE INTO modlets (unique_id, name, description, author, version, website)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (unique_id, modlet_info['name'], modlet_info['description'], modlet_info['author'],
                       modlet_info['version'], modlet_info['website']))
            self.conn.commit()
            debug(f"Stored modlet info for {modlet_info['name']}")
            return unique_id
        except sqlite3.Error as e:
            error(f"Error storing modlet info for {modlet_info['name']}: {str(e)}")
            return None

    def calculate_difference_percentage(self, str1, str2):
        """Calculate the difference percentage between two strings."""
        matcher = SequenceMatcher(None, str1, str2)
        similarity = matcher.ratio()
        return (1 - similarity) * 100

    def store_xml_data(self, modlet_name, unique_id, full_path, short_path, outer_tag, content):
        try:
            cursor = self.conn.cursor()
            debug(f"[DBProcessor] Storing XML data for {full_path}")
            debug(f"[DBProcessor] Content preview: {content[:100]}...")  # Log first 100 characters of content
            encoded_content = self._encode_data(content)
            cursor.execute('''
                INSERT OR REPLACE INTO xml_data (modlet_name, unique_id, full_path, short_path, outer_tag, content)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (modlet_name, unique_id, full_path, short_path, outer_tag, encoded_content))
            self.conn.commit()
            debug(f"[DBProcessor] Stored XML data for {full_path}")

            # Check if the data was updated
            cursor.execute('SELECT content FROM xml_data WHERE modlet_name = ? AND full_path = ?', (modlet_name, full_path))
            stored_data = cursor.fetchone()[0]

            if stored_data != encoded_content:
                diff_percentage = self.calculate_difference_percentage(stored_data, encoded_content)
                if diff_percentage > 10:
                    warning(f"Significant difference (>{diff_percentage:.2f}%) detected in stored XML data for {modlet_name} - {full_path}")
                else:
                    debug(f"Minor difference ({diff_percentage:.2f}%) detected in stored XML data for {modlet_name} - {full_path}")

        except sqlite3.Error as e:
            error(f"[DBProcessor] Error storing XML data: {e}")

    def store_localization_data(self, modlet_name, unique_id, full_path, short_path, file, used_in_main_menu, no_translate, type, key, english, german, latam, french, italian, japanese, koreana, polish, brazilian, russian, turkish, schinese, tchinese, spanish, value):
        try:
            cursor = self.conn.cursor()
            encoded_data = [self._encode_data(str(item)) for item in [modlet_name, unique_id, full_path, short_path, file, used_in_main_menu, no_translate, type, key, english, german, latam, french, italian, japanese, koreana, polish, brazilian, russian, turkish, schinese, tchinese, spanish, value]]
            cursor.execute('''
                INSERT OR REPLACE INTO localization_data 
                (modlet_name, unique_id, full_path, short_path, file, used_in_main_menu, no_translate, type, key, english, german, latam, french, italian, japanese, koreana, polish, brazilian, russian, turkish, schinese, tchinese, spanish, value)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', encoded_data)
            self.conn.commit()
        except sqlite3.Error as e:
            error(f"Error storing localization data: {e}")

    def get_modlet_info(self, modlet_id: str) -> Dict[str, str]:
        """Retrieve modlet information from the database"""
        try:
            c = self.conn.cursor()
            c.execute("SELECT * FROM modlets WHERE unique_id = ?", (modlet_id,))
            row = c.fetchone()
            if row:
                return {
                    'unique_id': row[0],
                    'name': self._decode_data(row[1]),
                    'description': self._decode_data(row[2]),
                    'author': self._decode_data(row[3]),
                    'version': self._decode_data(row[4]),
                    'website': self._decode_data(row[5])
                }
            return {}
        except sqlite3.Error as e:
            error(f"[DBProcessor] Error retrieving modlet info: {e}")
            raise

    def get_xml_data(self, full_path: str, short_path: str, outer_tag: str) -> Dict[str, Dict[str, str]]:
        """Retrieve XML data from the database"""
        try:
            c = self.conn.cursor()
            if full_path and short_path and outer_tag:
                c.execute("""SELECT short_path, outer_tag, content FROM xml_data 
                             WHERE full_path = ? AND short_path = ? AND outer_tag = ?""",
                          (full_path, short_path, outer_tag))
            else:
                c.execute("SELECT short_path, outer_tag, content FROM xml_data")
            
            xml_data = {}
            for row in c.fetchall():
                short_path, outer_tag, content = row
                if short_path not in xml_data:
                    xml_data[short_path] = {}
                if outer_tag not in xml_data[short_path]:
                    xml_data[short_path][outer_tag] = []
                xml_data[short_path][outer_tag].append(self._decode_data(content))
            
            debug(f"Retrieved {len(xml_data)} XML files from database")
            for short_path, content in xml_data.items():
                total_size = sum(len(''.join(c)) for c in content.values())
            
            return xml_data
        except sqlite3.Error as e:
            error(f"[DBProcessor] Error retrieving XML data: {e}")
            raise

    def get_localization_data(self, full_path: str, short_path: str) -> List[Dict[str, str]]:
        try:
            c = self.conn.cursor()
            if full_path and short_path:
                c.execute("""SELECT modlet_name, unique_id, full_path, short_path, file, used_in_main_menu, no_translate, type, key, english, german, latam, french, italian, japanese, koreana, polish, brazilian, russian, turkish, schinese, tchinese, spanish, value
                             FROM localization_data 
                             WHERE full_path = ? AND short_path = ?""",
                          (full_path, short_path))
            else:
                c.execute("""SELECT modlet_name, unique_id, full_path, short_path, file, used_in_main_menu, no_translate, type, key, english, german, latam, french, italian, japanese, koreana, polish, brazilian, russian, turkish, schinese, tchinese, spanish, value
                             FROM localization_data""")
            
            columns = [column[0] for column in c.description]
            results = c.fetchall()
            decoded_results = []
            for row in results:
                decoded_row = [self._decode_data(item) if item is not None else '' for item in row]
                decoded_results.append(dict(zip(columns, decoded_row)))
            return decoded_results
        except sqlite3.Error as e:
            error(f"[DBProcessor] Error retrieving localization data: {e}")
            raise

    def _calculate_hash(self, data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()

    def _validate_stored_data(self, table: str, id_value: str, original_data: Dict[str, Any]) -> None:
        """Validate that the stored data matches the original data"""
        c = self.conn.cursor()
        c.execute(f"SELECT * FROM {table} WHERE unique_id = ?", (id_value,))
        stored_data = c.fetchone()
        
        if stored_data:
            try:
                decoded_data = {k[0]: self._decode_data(v) for k, v in zip(c.description, stored_data) if k[0] not in ['timestamp', 'hash']}
                if decoded_data != original_data:
                    warning(f"Stored data in {table} does not match original data for id {id_value}")
                    debug(f"Original data: {original_data}")
                    debug(f"Stored data: {decoded_data}")
            except Exception as e:
                error(f"Error decoding stored data for {table}, id {id_value}: {str(e)}")
        else:
            warning(f"No data found in {table} for id {id_value}")

    def get_xml_metadata(self, short_path: str, outer_tag: str, content: str) -> Dict[str, str]:
        """Retrieve metadata for a specific XML entry"""
        try:
            c = self.conn.cursor()
            c.execute("""SELECT modlet_name, full_path FROM xml_data 
                        WHERE short_path = ? AND outer_tag = ? AND content = ?""",
                    (short_path, outer_tag, content))
            result = c.fetchone()
            if result:
                return {
                    'modlet_name': self._decode_data(result[0]),
                    'full_path': self._decode_data(result[1])
                }
            return {'modlet_name': 'Unknown', 'full_path': 'Unknown'}
        except sqlite3.Error as e:
            error(f"[DBProcessor] Error retrieving XML metadata: {e}")
            return {'modlet_name': 'Error', 'full_path': 'Error'}

    def __del__(self):
        """Close the database connection when the object is destroyed"""
        if hasattr(self, 'conn'):
            self.conn.close()

    def display_db_statistics(self):
        """
        Display various statistics about the database content.
        """
        try:
            c = self.conn.cursor()
            
            # Number of different modlets
            c.execute("SELECT COUNT(DISTINCT unique_id) FROM modlets")
            modlet_count = c.fetchone()[0]
            
            # Number of different short_file variations (excluding ModInfo.xml)
            c.execute("SELECT COUNT(DISTINCT short_path) FROM xml_data WHERE short_path != 'ModInfo.xml'")
            short_file_count = c.fetchone()[0]
            
            # XML blocks per file with total size
            c.execute("""
                SELECT short_path, COUNT(outer_tag) as block_count, SUM(LENGTH(content)) as total_size 
                FROM xml_data 
                GROUP BY short_path
            """)
            xml_blocks = c.fetchall()
            
            # Total XML content size
            c.execute("SELECT SUM(LENGTH(content)) FROM xml_data")
            total_xml_size = c.fetchone()[0]
            
            # Number of localization entries
            c.execute("SELECT COUNT(*) FROM localization_data")
            localization_count = c.fetchone()[0]
            
            # Number of unique outer tags
            c.execute("SELECT COUNT(DISTINCT outer_tag) FROM xml_data")
            unique_outer_tags = c.fetchone()[0]
            
            # Average content size per XML block
            c.execute("SELECT AVG(LENGTH(content)) FROM xml_data")
            avg_xml_size = c.fetchone()[0]
            
            # Prepare the statistics table
            stats = [
                ["Number of Modlets", modlet_count],
                ["Number of XML Files (excl. ModInfo.xml)", short_file_count],
                ["Total XML Content Size (bytes)", total_xml_size],
                ["Number of Localization Entries", localization_count],
                ["Number of Unique Outer Tags", unique_outer_tags],
                ["Average XML Block Size (bytes)", round(avg_xml_size, 2) if avg_xml_size else 0],
            ]
            
            print("\nDatabase Statistics:")
            print(tabulate(stats, headers=["Metric", "Value"], tablefmt="grid"))
            
            print("\nXML Blocks per File:")
            xml_block_stats = [[short_path, count, f"{size:,} bytes"] for short_path, count, size in xml_blocks]
            print(tabulate(xml_block_stats, headers=["Short Path", "XML Block Count", "XML Block Size"], tablefmt="grid"))
            
        except sqlite3.Error as e:
            error(f"Error retrieving database statistics: {e}")

    def wipe_database(self):
        """Wipe all data from the database."""
        try:
            c = self.conn.cursor()
            # Get all table names except sqlite_sequence
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence';")
            tables = c.fetchall()
            
            # Drop all tables except sqlite_sequence
            for table in tables:
                c.execute(f"DROP TABLE IF EXISTS {table[0]}")
            
            # Clear the sqlite_sequence table
            c.execute("DELETE FROM sqlite_sequence;")
            
            self.conn.commit()
            debug("Database wiped successfully")
        except sqlite3.Error as e:
            error(f"Error wiping database: {e}")

    def get_all_modlet_info(self) -> List[Dict[str, Any]]:
        """Retrieve information for all modlets"""
        try:
            c = self.conn.cursor()
            c.execute("SELECT name, version, author FROM modlets")
            results = c.fetchall()
            
            modlet_info = []
            for result in results:
                modlet_info.append({
                    'Name': self._decode_data(result[0]),
                    'Version': self._decode_data(result[1]),
                    'Author': self._decode_data(result[2])
                })
            
            return modlet_info
        except sqlite3.Error as e:
            error(f"[DBProcessor] Error retrieving all modlet info: {e}")
            return []