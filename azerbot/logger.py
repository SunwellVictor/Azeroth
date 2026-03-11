import logging
import sys
import os

def setup_logger(name="azerbot"):
    """
    Sets up a simple logger that outputs to stdout.
    Format: timestamp - level - message
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Check if handlers already exist to avoid duplicate logs
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
