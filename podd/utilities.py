"""
Contains logger utility function
"""
import logging
from logging.handlers import RotatingFileHandler
from os import path


def logger(name, level=logging.DEBUG) -> logging.getLogger:
    """
    Creates logger
    :param name: name of logger
    :param level: logging level to use with this logger
    :return: logging.getLogger
    """
    log = logging.getLogger(name)
    log.setLevel(level)
    fmt = logging.Formatter("%(asctime)s [%(filename)s] func: [%(funcName)s] [%(levelname)s] "
                            "line: [%(lineno)d] %(message)s")
    # delay=True delays opening file until actually needed, preventing I/O errors
    file_hdlr = RotatingFileHandler(filename=f"{path.join(path.dirname(__file__), 'Logs/')}{name}.log",
                                    delay=True, backupCount=5, maxBytes=2000000)
    file_hdlr.setLevel(level)
    file_hdlr.setFormatter(fmt)
    if not log.handlers:
        log.addHandler(file_hdlr)
    return log
