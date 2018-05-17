"""
Contains utility functions for testing purposes
"""
import logging
from os import listdir, path
import pathlib
from pickle import dump, load

import feedparser as fp


def logger(name=__name__, level=logging.DEBUG) -> logging.getLogger:
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
    file_hdlr = logging.FileHandler(f'{name}.log', delay=True)  # delay=True delays opening file until actually needed
    file_hdlr.setLevel(logging.DEBUG)
    file_hdlr.setFormatter(fmt)
    if not log.handlers:
        log.addHandler(file_hdlr)
    return log


def create_test_objects():
    """
    Creates pickled feedparser.parse(url) objects used for testing
    as well as the directory containing them
    :return: None
    """
    if 'testfiles' not in listdir(path.dirname(__file__)):
        pathlib.Path(path.join(path.dirname(__file__), 'testfiles')).mkdir()
    files = listdir(path.join(path.dirname(__file__), 'testfiles/'))
    with open('overcast_feeds.txt') as file:
        for line in file:
            url, name = line.split()
            name = f'{name}.p'
            if name not in files:
                with open(path.join('testfiles', name), 'wb') as file_:
                    dump(fp.parse(url), file_)


def load_test_objects():
    """
    :return: un-pickled feedparser.parse(url) objects used for testing
    """
    with open(path.join('testfiles', 'tangentiallyspeaking.p'), 'rb') as file:
        ryan = load(file)
    with open(path.join('testfiles', 'goldmansachs.p'), 'rb') as file:
        gold = load(file)
    with open(path.join('testfiles', 'peterson.p'), 'rb') as file:
        peterson = load(file)
    return ryan, gold, peterson
