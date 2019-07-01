""""""
import logging
from logging.handlers import RotatingFileHandler

from podd.settings import Config


def logger(
    name, log_directory=Config.log_directory, level=logging.DEBUG
) -> logging.getLogger:
    """Create and configure logger.

    :param name: name of logger
    :param log_directory: directory in which to save logs
    :param level: logging level to use with this logger
    :return: logging.getLogger
    """
    filename = log_directory / f"{name}.log"
    log = logging.getLogger(name)
    log.setLevel(level)
    fmt = logging.Formatter(
        "%(asctime)s [%(filename)s] func: [%(funcName)s] [%(levelname)s] "
        "line: [%(lineno)d] %(message)s"
    )
    # delay=True delays opening file until actually needed, preventing I/O errors
    # That one was fun to figure out
    file_hdlr = RotatingFileHandler(
        filename=filename, delay=True, backupCount=5, maxBytes=2000000
    )
    file_hdlr.setLevel(level)
    file_hdlr.setFormatter(fmt)
    if not log.handlers:
        log.addHandler(file_hdlr)
    return log
