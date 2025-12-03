import logging


def setup_logger(log_file="logs/app.log"):
    """Sets up a logger that logs to a single file."""
    logger = logging.getLogger("shared_logger")
    logger.setLevel(logging.DEBUG)

    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)

    # Create formatter and add it to the handler
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    # Avoid adding handlers multiple times
    if not logger.handlers:
        logger.addHandler(file_handler)

    return logger
