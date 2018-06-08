import getpass
from os import listdir, path
import pathlib
from pickle import dump, load

import feedparser as fp


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
