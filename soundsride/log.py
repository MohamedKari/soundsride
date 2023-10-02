import logging
from typing import List

logger_setup = False

def setup_logger(module_exclusions: List[str] = ["werkzeug"]):
    global logger_setup

    if logger_setup:
        return
    
    logger_setup = True
    
    root_logger = logging.getLogger()
    root_logger.setLevel("DEBUG")

    formatter = logging.Formatter(
        "%(asctime)s %(name)-25s %(threadName)s %(levelname)-6s %(message)s")

    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)
    root_logger.addHandler(streamHandler)

    logging.getLogger(__name__).info("initialized logger")

    if module_exclusions:
        for module_exclusion in module_exclusions:
            logging.getLogger(module_exclusion).setLevel(logging.WARNING)