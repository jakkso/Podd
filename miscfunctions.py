
from datetime import datetime
from os import listdir, path
import pathlib
from pickle import dump, load

import feedparser as fp


def logger(exc_type, exc_val, exc_tb):
    """
    Appends extremely basic error info to error log file.
    :param exc_type: exception type
    :param exc_val:  exception value
    :param exc_tb: exception traceback
    :return: None
    """
    with open('errors.log', 'a') as file:
        file.write('\n'.join([datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                   str(exc_type.__name__),
                   str(exc_val),
                   f'Line {exc_tb.tb_lineno}'
                   '\n\n']))


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
                with open(path.join('testfiles', name), 'wb') as f:
                    dump(fp.parse(url), f)


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
