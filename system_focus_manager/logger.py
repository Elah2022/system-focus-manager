"""
My logging system.
Here I log everything that happens to be able to debug if something fails.
"""

import logging
import os
from datetime import datetime
from pathlib import Path


class FocusLogger:
    """My custom logger that saves everything in files by day"""

    def __init__(self, log_dir: str = None):
        if log_dir is None:
            log_dir = Path(__file__).parent / 'logs'

        # Create logs directory if it doesn't exist
        Path(log_dir).mkdir(parents=True, exist_ok=True)

        # File name: logs/YYYY-MM-DD.log
        log_filename = datetime.now().strftime('%Y-%m-%d.log')
        log_path = Path(log_dir) / log_filename

        # Configure logger
        self.logger = logging.getLogger('FocusManager')
        self.logger.setLevel(logging.DEBUG)

        # Avoid duplicating handlers
        if not self.logger.handlers:
            # File handler
            file_handler = logging.FileHandler(log_path, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)

            # Console handler (optional)
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)

            # Log format
            formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] %(message)s',
                datefmt='%H:%M:%S'
            )

            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

    def info(self, message: str):
        """General information log"""
        self.logger.info(message)

    def warning(self, message: str):
        """Warning log"""
        self.logger.warning(message)

    def error(self, message: str):
        """Error log"""
        self.logger.error(message)

    def debug(self, message: str):
        """Debugging log"""
        self.logger.debug(message)

    def mode_changed(self, mode_name: str):
        """Log when mode is changed"""
        self.info(f"Modo cambiado a: {mode_name}")

    def process_closed(self, process_name: str):
        """Log when a process is closed"""
        self.info(f"Proceso cerrado: {process_name}")

    def app_opened(self, app_name: str):
        """Log when an application is opened"""
        self.info(f"Aplicación abierta: {app_name}")

    def session_started(self, mode_name: str):
        """Log when a session starts"""
        self.info(f"Sesión iniciada en modo: {mode_name}")

    def session_ended(self, mode_name: str, duration: str):
        """Log when a session ends"""
        self.info(f"Sesión terminada. Modo: {mode_name}, Duración: {duration}")
