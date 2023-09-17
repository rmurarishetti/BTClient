import logging

def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO

    # Set up the console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # Set up the formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    # Set up the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)