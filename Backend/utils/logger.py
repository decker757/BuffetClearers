"""
Comprehensive logging system
Provides structured logging for all modules
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler


class AppLogger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize logging configuration"""
        # Create logs directory
        log_dir = './logs'
        os.makedirs(log_dir, exist_ok=True)

        # Create logger
        self.logger = logging.getLogger('document_corroboration')
        self.logger.setLevel(logging.DEBUG)

        # Remove existing handlers
        self.logger.handlers = []

        # Console handler (INFO and above)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)

        # File handler for all logs (rotating)
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'app.log'),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        # Error file handler (ERROR and above only)
        error_handler = RotatingFileHandler(
            os.path.join(log_dir, 'error.log'),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)

        # Add handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)

    def get_logger(self, module_name: str = None):
        """Get logger instance for a specific module"""
        if module_name:
            return logging.getLogger(f'document_corroboration.{module_name}')
        return self.logger


# Singleton instance
app_logger = AppLogger()


def get_logger(module_name: str = None):
    """
    Get logger instance

    Usage:
        from utils.logger import get_logger
        logger = get_logger('processing_engine')
        logger.info('Processing started')
    """
    return app_logger.get_logger(module_name)
