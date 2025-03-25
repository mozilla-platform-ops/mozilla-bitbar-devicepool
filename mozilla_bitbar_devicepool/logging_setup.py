# logging_setup.py
import logging


def setup_logging(level=logging.INFO):
    """Configure logging with timestamps and levels."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,  # Force reconfiguration of the root logger
    )
