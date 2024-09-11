"""
MC Logger for 7 Days to Die Modlet Combiner

This class provides logging functionality with support for different log levels,
syslog, file logging, and stdout logging.

Classes that call this class:
    - modletCombiner.py (main script)
    - All other classes for logging purposes

Methods called from this class:
    - info, debug, error, warning, critical: Called from various parts of the project
    - set_log_level: Called from main script to set log level from command-line argument
    - delete_old_logs: Called periodically to manage log file storage

Visual map:
[mc_logger.py] -> [syslog, file system, stdout]
                <- [modletCombiner.py]
                <- [All other modules for logging]
"""

import logging
import logging.handlers
import os
import sys
import traceback
from typing import Optional
from .configuration import get_config, versioned
from logging.handlers import RotatingFileHandler

@versioned("1.3.4")
class MCLogger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCLogger, cls).__new__(cls)
            cls._instance._initialize_logger()
        return cls._instance

    def _initialize_logger(self):
        self.logger = logging.getLogger('7DTD-ModletCombiner')
        self.logger.setLevel(logging.INFO)

        # Clear any existing handlers
        self.logger.handlers.clear()

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # File handler with rotation
        log_file = get_config('LOG_FILE', 'modlet_combiner.log')
        max_bytes = int(get_config('LOG_MAX_BYTES', 1024 * 1024))  # 1 MB
        backup_count = int(get_config('LOG_BACKUP_COUNT', 5))
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Syslog handler (optional)
        try:
            syslog_address = '/var/run/syslog' if sys.platform == 'darwin' else '/dev/log'
            if os.path.exists(syslog_address):
                syslog_handler = logging.handlers.SysLogHandler(address=syslog_address)
                syslog_handler.setFormatter(formatter)
                self.logger.addHandler(syslog_handler)
        except Exception as e:
            print(f"Warning: Unable to initialize syslog handler: {e}")

    def info(self, message: str) -> None:
        self.logger.info(message)

    def debug(self, message: str) -> None:
        self.logger.debug(message)

    def error(self, message: str, exc_info=False) -> None:
        if exc_info:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            self.logger.error(f"{message}\n{tb_str}")
            # Print a truncated version to stdout
            print(f"Error: {message}")
            print("Traceback (most recent call last):")
            print('\n'.join(tb_str.split('\n')[-5:]))  # Print last 5 lines of traceback
        else:
            self.logger.error(message)

    def warning(self, message: str) -> None:
        self.logger.warning(message)

    def critical(self, message: str) -> None:
        self.logger.critical(message)

    def log_long_output(self, message: str, max_length=1000) -> None:
        if len(message) > max_length:
            truncated_message = message[:max_length] + "... (truncated, see log file for full output)"
            self.logger.info(truncated_message)
            self.logger.debug(message)  # Log full message to file
        else:
            self.logger.info(message)

    def set_log_level(self, level: str) -> None:
        level = level.upper()
        self.logger.setLevel(level)
        # Update all handlers to use the new level
        for handler in self.logger.handlers:
            handler.setLevel(level)
        self.debug(f"Log level set to {level}")

    def get_log_level(self) -> str:
        return logging.getLevelName(self.logger.level)

    def delete_old_logs(self) -> None:
        log_dir = os.path.dirname(get_config('LOG_FILE', 'modlet_combiner.log'))
        max_age_days = int(get_config('LOG_MAX_AGE_DAYS', 30))
        current_time = time.time()

        for filename in os.listdir(log_dir):
            if filename.startswith('modlet_combiner') and filename.endswith('.log'):
                file_path = os.path.join(log_dir, filename)
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > max_age_days * 86400:  # 86400 seconds in a day
                    os.remove(file_path)
                    self.info(f"Deleted old log file: {filename}")

# Create a single instance of MCLogger
logger = MCLogger()

# Add convenience functions to access the logger directly
def info(message: str) -> None:
    logger.info(message)

def debug(message: str) -> None:
    logger.debug(message)

def error(message: str) -> None:
    logger.error(message)

def warning(message: str) -> None:
    logger.warning(message)

def critical(message: str) -> None:
    logger.critical(message)

def exception(message: str) -> None:
    logger.exception(message)

def set_log_level(level: str) -> None:
    logger.set_log_level(level)

def delete_old_logs() -> None:
    logger.delete_old_logs()
