# src/log_config.py
"""Centralized logging configuration for the SCAGDRFS pipeline.

Call setup_logging() exactly once, from an entry point (a script's
main() or __main__ block).  Library modules should never configure
logging; they should only do:

    logger = logging.getLogger(__name__)
"""
import logging
import sys

LOG_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"
DATE_FORMAT = "%H:%M:%S"


def setup_logging(level=logging.INFO, log_file=None):
    """Configure root logger. Safe to call once per process."""
    handlers = [logging.StreamHandler(sys.stderr)]
    if log_file is not None:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=handlers,
        force=True,  # override any earlier accidental basicConfig
    )
