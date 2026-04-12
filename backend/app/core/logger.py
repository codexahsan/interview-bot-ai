# backend/app/core/logger.py

"""
Minimal logger setup. Logs errors and important events only.
"""

import logging
import sys
from typing import Optional

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Returns a configured logger instance.
    Logs to stdout with a standard format.
    """
    logger = logging.getLogger(name or __name__)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger