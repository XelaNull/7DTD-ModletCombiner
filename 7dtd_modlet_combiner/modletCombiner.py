#!/usr/bin/env python3
"""
7 Days to Die Modlet Combiner

This script combines multiple 7 Days to Die modlets into a single modlet.
It searches for ModInfo.xml files, parses XML and Localization files,
and generates a new combined modlet with all the components.

Syntax: python modletCombiner.py [options] <source path>
Usage: python modletCombiner.py --combine --modlet-name="Combined Modlet" /path/to/modlets
Examples:
    python modletCombiner.py --combine --modlet-name="Super Modlet" --modlet-author="John Doe" /mods
    python modletCombiner.py --version

Poetry Usage:
    - Install dependencies: poetry install
    - Run the script: poetry run python -m 7dtd_modlet_combiner.modletCombiner [options] <source path>
    - Activate virtual environment: poetry shell
    - Add a new dependency: poetry add <package-name>
    - Update dependencies: poetry update

Version History:
    1.0.0 - Initial release
    1.1.0 - Added Poetry support and dependency management
    1.2.0 - Added log level configuration and periodic log cleanup
    1.2.1 - Refactored main function for better organization

Code Style Guidelines:
    - Follow PEP 8
    - Use type hints
    - Write comprehensive docstrings

Lessons Learned:
    - Importance of robust error handling
    - Benefits of modular design
    - Simplified dependency management with Poetry

TODO:
    - Implement unit tests
    - Add support for additional file types

Logical Flow:
1. Parse command-line arguments (ArgumentParser)
2. Initialize logging (MC Logger)
3. Check dependencies (Utilities)
4. Find modlets (Modlet Finder)
5. Locate and parse files (File Locator, XML Parser, Localization Parser)
6. Process and store data (DB Processor)
7. Generate combined modlet (Modlet Writer, XML Writer)
8. Perform final validations

Dependencies:
    See pyproject.toml for a full list of dependencies.
    Use 'poetry show' to view installed packages.
"""

import argparse
import sys
import time
import os
from typing import Dict, Any, Tuple
from .mc_logger import set_log_level, info, error, warning, delete_old_logs, debug
from .utilities import check_dependencies, format_number, update_all_dependencies
from .modlet_finder import ModletFinder
from .file_locator import FileLocator
from .db_processor import DBProcessor  # Add this import
from .modlet_writer import ModletWriter
from .configuration import load_config, get_config, versioned, todo, CLI_ALIASES
import traceback
import sqlite3
from tabulate import tabulate
import readline

@versioned("1.3.3")
@todo("Implement unit tests")
def main() -> None:
    """
    Main function to run the 7 Days to Die Modlet Combiner.
    """
    try:
        args = parse_arguments()
        setup_logging(args.get('log_level', 'INFO'), args.get('debug', False))

        debug("Starting main function execution")

        db_processor = DBProcessor()

        if args.get('update_dependencies'):
            update_dependencies()
            return

        if args.get('cli_db'):
            db_processor.initialize('modlet_combiner.db', wipe=False)
            run_sqlite_cli(db_processor)
            return

        # Only set up the full environment if not in CLI DB mode
        db_processor.initialize('modlet_combiner.db', wipe=True)
        args, modlet_writer = setup_environment(args, db_processor)
        run_modlet_combiner(args, db_processor, modlet_writer)

    except Exception as e:
        error(f"An error occurred in main: {str(e)}")
        error(f"Traceback: {traceback.format_exc()}")
    finally:
        info("7 Days to Die Modlet Combiner finished")

    info("7 Days to Die Modlet Combiner completed successfully")

def setup_environment(args: Dict[str, Any], db_processor: DBProcessor) -> Tuple[Dict[str, Any], ModletWriter]:
    """Set up the environment and parse arguments."""
    debug("Setting up environment")
    load_config()

    # Use source_path as the output_path
    output_path = args['source_path']
    info(f"Output path (using source_path): {output_path}")

    # Create an instance of ModletWriter and reset the output directory
    modlet_writer = ModletWriter(output_path, db_processor, args)

    modlet_writer.reset_output_directory()  # Clear the output directory

    debug(f"Parsed arguments: {args}")
    return args, modlet_writer  # Return these objects

def parse_arguments() -> Dict[str, Any]:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="7 Days to Die Modlet Combiner")
    parser.add_argument('--combine', action='store_true', help='Combine modlets')
    parser.add_argument('--modlet-name', type=str, help='Name of the combined modlet')
    parser.add_argument('--modlet-author', type=str, help='Author of the combined modlet')
    parser.add_argument('--modlet-desc', type=str, help='Description of the combined modlet')
    parser.add_argument('--modlet-ver', type=str, help='Version of the combined modlet')
    parser.add_argument('--modlet-url', type=str, help='URL of the combined modlet')
    parser.add_argument('--log-level', type=str, default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='Logging level')
    parser.add_argument('--update-dependencies', action='store_true', help='Update dependencies')
    parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without modifying files')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--cli-db', action='store_true', help='Enter SQLite CLI mode')
    parser.add_argument('source_path', type=str, nargs='?', help='Source path for modlets')
    
    args = parser.parse_args()
    
    # Check if source_path is required
    if not args.cli_db and not args.source_path:
        parser.error("the following arguments are required: source_path")
    
    return vars(args)

def setup_logging(log_level: str, debug_flag: bool) -> None:
    """Set up logging with the specified log level."""
    if debug_flag:
        log_level = 'DEBUG'
    set_log_level(log_level)
    info("7 Days to Die Modlet Combiner started")
    debug("Debug mode enabled")

def run_modlet_combiner(args: Dict[str, Any], db_processor: DBProcessor, modlet_writer: ModletWriter) -> None:
    """Run the main logic of the Modlet Combiner."""
    debug("Starting run_modlet_combiner")
    debug(f"Options: {args}")
    
    try:
        source_path = args['source_path']
        debug(f"Processing modlets from: {source_path}")

        additional_skip_dirs = args.get('skip_dirs', '').split(',') if args.get('skip_dirs') else None
        modlet_finder = ModletFinder(source_path, additional_skip_dirs)
        debug("Locating ModInfo.xml files")
        modlets = modlet_finder.find_modlets()
        debug(f"Found {len(modlets)} modlets")

        combined_modlet_info = {
            'Name': args.get('modlet_name', 'Combined Modlet'),
            'Author': args.get('modlet_author', 'Modlet Combiner'),
            'Description': args.get('modlet_desc', 'A combined modlet'),
            'Version': args.get('modlet_ver', '1.0.0'),
            'Website': args.get('modlet_url', '')
        }

        # Get the output path from args or use a default
        output_path = args.get('output_path') or 'combined_modlet'

        # Display database statistics
        # db_processor.display_db_statistics()        

        # ModletWriter is already initialized in the setup_environment function
        modlet_writer.write_modlet(combined_modlet_info)
        
        info("Modlet combination completed successfully.")
    except Exception as e:
        error(f"Error in modlet combination process: {str(e)}")
        raise
    
    perform_file_operations(args)
    cleanup_logs()

def process_modlets(args: Dict[str, Any]) -> None:
    """Find and process modlets."""
    debug("Starting process_modlets function")
    source_path = args['source_path']
    debug(f"Processing modlets from: {source_path}")

    additional_skip_dirs = args.get('skip_dirs', '').split(',') if args.get('skip_dirs') else None
    modlet_finder = ModletFinder(args['source_path'], additional_skip_dirs)
    debug("Locating ModInfo.xml files")
    modlets = modlet_finder.find_modlets()
    debug(f"Found {len(modlets)} modlets")
    
    debug("Processing files")
    file_locator.process_files()  # Remove the 'files' argument

    if args['combine']:
        debug("Combining modlets...")
        db_processor = DBProcessor()  # Create an instance of DBProcessor
        modlet_writer = ModletWriter(output_path, db_processor, args)
        modlet_info = {
            'name': args['modlet_name'],
            'author': args['modlet_author'],
            'description': args['modlet_desc'],
            'version': args['modlet_ver'],
            'website': args['modlet_url']
        }
        
        debug("Validating modlet info")
        for key, value in modlet_info.items():
            if value is None:
                error(f"Modlet {key} is None. Please provide a value for --modlet-{key}")
                raise ValueError(f"Modlet {key} cannot be None")
        
        try:
            debug("Writing combined modlet")
            modlet_writer.write_modlet(modlet_info)
            debug("Modlets combined successfully")
        except Exception as e:
            error(f"Error writing combined modlet: {str(e)}")
            error(f"Traceback: {traceback.format_exc()}")
            raise

def perform_file_operations(args: Dict[str, Any]) -> None:
    """Perform actual file operations if not in dry run mode."""
    debug("Starting perform_file_operations")
    if not args['dry_run']:
        # Perform actual file operations here
        pass

def cleanup_logs() -> None:
    """Periodically delete old logs."""
    if time.time() % 86400 < 300:  # Run once a day (within a 5-minute window)
        delete_old_logs()

def check_and_update_dependencies(args: Dict[str, Any]) -> None:
    """Check and update dependencies if necessary."""
    debug("Starting check_and_update_dependencies")
    if not check_dependencies():
        error("Missing dependencies. Please install required packages.")
        sys.exit(1)

def update_dependencies() -> None:
    """Update all dependencies to their latest versions."""
    debug("Updating dependencies...")
    failed_updates = update_all_dependencies()
    if failed_updates:
        warning(f"Failed to update the following dependencies: {', '.join(failed_updates)}")
    else:
        debug("All dependencies updated successfully")

def implement_unit_tests() -> None:
    """
    Implement unit tests for the Modlet Combiner.
    """
    pass

class SQLCompleter:
    keywords = ['SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'TABLE', 'DROP', 'ALTER', 'INDEX', 'AND', 'OR', 'NOT', 'IN', 'LIKE', 'BETWEEN', 'IS', 'NULL', 'ORDER', 'BY', 'GROUP', 'HAVING', 'LIMIT', 'OFFSET']

    def __init__(self, db_processor):
        self.db_processor = db_processor
        self.all_words = self.keywords + self.get_table_names() + list(CLI_ALIASES.keys())

    def get_table_names(self):
        cursor = self.db_processor.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return [row[0] for row in cursor.fetchall()]

    def complete(self, text, state):
        results = [x for x in self.all_words if x.lower().startswith(text.lower())] + [None]
        return results[state]

def run_sqlite_cli(db_processor: DBProcessor):
    """Run an interactive SQLite CLI."""
    print("Entering SQLite CLI mode. Type 'exit' to quit.")
    print("Available aliases:", ", ".join(CLI_ALIASES.keys()))
    
    completer = SQLCompleter(db_processor)
    readline.set_completer(completer.complete)
    readline.parse_and_bind('tab: complete')
    
    while True:
        try:
            query = input("SQL> ")
            if query.lower() == 'exit':
                print("Exiting SQLite CLI mode.")
                break
            if query.strip() == "":
                continue  # Skip empty inputs
            
            # Check if the input is an alias
            if query.strip() in CLI_ALIASES:
                query = CLI_ALIASES[query.strip()]
                print(f"Executing: {query}")
            
            # Special handling for .columns alias
            if query.startswith("SELECT name FROM pragma_table_info"):
                table_name = input("Enter table name: ")
                query = query.replace("?", f"'{table_name}'")
            
            cursor = db_processor.conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            if results:
                headers = [description[0] for description in cursor.description]
                print(tabulate(results, headers=headers, tablefmt="grid"))
            else:
                print("Query executed successfully.")
            db_processor.conn.commit()
        except sqlite3.Error as e:
            print(f"SQLite error: {e}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()