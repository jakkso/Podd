"""Contain logging utility functions."""

import logging
from logging.handlers import RotatingFileHandler
from os import getenv, mkdir, path
import pathlib

from podd.settings import Config


def logger(name, log_directory=Config.log_directory, level=logging.DEBUG) -> logging.getLogger:
    """Create logger.

    :param name: name of logger
    :param log_directory: directory in which to save logs
    :param level: logging level to use with this logger
    :return: logging.getLogger
    """
    if not log_directory:
        filename = logger_setup(name)
    else:
        filename = pathlib.Path(log_directory) / f'{name}.log'
    log = logging.getLogger(name)
    log.setLevel(level)
    fmt = logging.Formatter("%(asctime)s [%(filename)s] func: [%(funcName)s] [%(levelname)s] "
                            "line: [%(lineno)d] %(message)s")
    # delay=True delays opening file until actually needed, preventing I/O errors
    # That one was fun to figure out
    file_hdlr = RotatingFileHandler(filename=filename,
                                    delay=True,
                                    backupCount=5,
                                    maxBytes=2000000)
    file_hdlr.setLevel(level)
    file_hdlr.setFormatter(fmt)
    if not log.handlers:
        log.addHandler(file_hdlr)
    return log


def logger_setup(name: str) -> str:
    """Setup logger.

    :param name: name of log file.
    Makes general log directory in home folder, then Podd directory inside
    that.  This is a userland utility, therefore creating logs in /var/log
    would require `sudo` access, which isn't a great idea.
    Creates log directory in $HOME, and then Podd directory inside that.

    :return: name of log file
    """
    home = getenv('HOME')
    log_dir = path.join(home, 'logs')
    podd_dir = path.join(log_dir, 'Podd')
    if not path.exists(log_dir):
        mkdir(log_dir)
    if not path.exists(podd_dir):
        mkdir(podd_dir)
    log_file = path.join(podd_dir, f'{name}.log')
    return log_file
