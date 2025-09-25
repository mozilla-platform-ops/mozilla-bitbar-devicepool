# logging_setup.py
import logging


def setup_logging(level=logging.INFO, disable_timestamps=False):
    """Configure logging with timestamps and levels."""

    # Assuming your setup function configures the root logger
    logging.basicConfig(level=level)  # Or however you set the root level

    # for requests, it gets too chatty
    # TODO: make -vv show these or something
    #
    # Get the logger for 'requests' (and others) and set its level to INFO
    logging.getLogger("requests").setLevel(logging.INFO)
    logging.getLogger("requests_cache").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.INFO)

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
