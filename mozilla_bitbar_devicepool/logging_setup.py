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

    # hide logging for things we don't want to see
    logging.getLogger("mohawk").setLevel(logging.WARNING)
    logging.getLogger("taskcluster").setLevel(logging.WARNING)

    # enable for debugging the source of messages
    include_name = False

    # inject name into format if include_name is True
    if include_name:
        format_string = "%(name)s - %(levelname)s - %(message)s"
        format_string_with_time = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    else:
        format_string = "%(levelname)s - %(message)s"
        format_string_with_time = "%(asctime)s - %(levelname)s - %(message)s"

    if disable_timestamps:
        # Disable timestamps in the log messages
        logging.basicConfig(
            level=level,
            format=format_string,
            force=True,  # Force reconfiguration of the root logger
        )
    else:
        logging.basicConfig(
            level=level,
            format=format_string_with_time,
            datefmt="%Y-%m-%d %H:%M:%S",
            force=True,  # Force reconfiguration of the root logger
        )
