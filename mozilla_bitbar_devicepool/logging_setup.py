# logging_setup.py
import logging


def setup_logging(level=logging.INFO, disable_timestamps=False):
    """Configure logging with timestamps and levels."""
    if disable_timestamps:
        # Disable timestamps in the log messages
        logging.basicConfig(
            level=level,
            format="%(levelname)s - %(message)s",
            force=True,  # Force reconfiguration of the root logger
        )
    else:
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            force=True,  # Force reconfiguration of the root logger
        )
