"""
Contains classes that directly use the database
"""
from datetime import datetime, timedelta
from os import access, listdir, path, R_OK, W_OK
from queue import Queue
import pathlib
import sqlite3
from threading import Thread
from time import mktime
from types import TracebackType

import feedparser as fp

from config import Config
from utilities import logger


class Database:
    """
    Defines SQLite database creation and usage methods
    """

    def __init__(self, db_file: str = Config.database):
        self._db_file = db_file
        self._conn = sqlite3.connect(self._db_file)
        self.cursor = self._conn.cursor()
        self._logger = logger()

    def __enter__(self):
        return self

    def __exit__(self,
                 exc_type,
                 exc_val,
                 exc_tb: TracebackType):
        """
        If there are exceptions, rolls back and calls logger
        :param exc_type: exception type
        :param exc_val:  exception value
        :param exc_tb: exception traceback
        :return: None
        """
        if exc_type is not None:
            self._conn.rollback()
            self._logger.error(exc_type, exc_val, exc_tb)

        else:
            self._conn.commit()
        self._conn.close()

    def __repr__(self):
        return f'{self.__class__.__name__}({self._db_file})'

    @staticmethod
    def create(database: str) -> None:
        """
        Looks in the directory of the given filename, if the file is absent,
        it creates the database with default values.
        :param database: string, abs path of database file
        :return: None
        """
        files = [path.join(path.dirname(database), item) for item in
                 listdir(path.dirname(database))]
        if database not in files:
            with Database(database) as _db:
                cur = _db.cursor
                cur.execute('CREATE TABLE IF NOT EXISTS podcasts \
                             (name text, url text, directory text, date text)')
                cur.execute('CREATE TABLE IF NOT EXISTS settings \
                             (id INTEGER, new_only INTEGER, base_directory TEXT)')
                cur.execute('INSERT INTO settings VALUES (?,?,?)',
                            (1, 1, path.join(pathlib.Path.home(), 'Podcasts')), )

    def options(self) -> tuple:
        """
        :return: tuple of currently set options
        """
        self.cursor.execute('SELECT new_only, base_directory FROM settings')
        return self.cursor.fetchone()

    def subscriptions(self) -> list:
        """

        :return: list of 3-tuples, consisting of the url, download directory
        and latest download date of each podcast
        """
        self.cursor.execute('SELECT url, directory, date FROM podcasts')
        return self.cursor.fetchall()

    def change_download_date(self, date: datetime, podcast_name: str) -> None:
        """
        Changes download date for podcast name
        :param date: datetime object, coerced to a string
        :param podcast_name: name of podcast
        :return: None
        """
        self.cursor.execute('UPDATE podcasts SET date = ? WHERE name = ?',
                            (date, podcast_name), )

    def change_option(self, option: str, value: str) -> None:
        """
        I know, I know, using a database query with an fstring is problematic,
        à la bobby tables, but the user doesn't interact directly with the
        database with this or any other queries that use fstrings in queries.
        All values input by the user are parameterized, which mitigates the threat.
        Given what this application is and does, I'm not sure why any user would
        try to sql injection on a local db of which they have sole access.
        :param option: string, option to change
        :param value: string, option's new value
        :return: None
        """
        self.cursor.execute(f'UPDATE settings SET {option} = ? WHERE id = 1', (value,))

    def fetch_single_column(self, column: str) -> list:
        """
        :param column: name of column to fetch
        :return: list of contents of said column
        """
        self.cursor.execute(f'SELECT {column} FROM podcasts')
        return [item[0] for item in self.cursor.fetchall()]

    def add_podcast(self,
                    podcast_name: str,
                    feed_url: str,
                    download_directory: str,
                    date: str) -> None:
        """
        Adds podcast to database
        :param podcast_name:
        :param feed_url:
        :param download_directory: directory in which to save future downloads
        :param date: download episodes newer than this date
        :return: None
        """
        self.cursor.executemany('INSERT INTO podcasts VALUES (?,?,?,?)',
                                ((podcast_name,
                                  feed_url,
                                  download_directory,
                                  date),))

    def remove_podcast(self, name: str) -> None:
        """
        Deletes row where name matches
        :param name: rss feed url
        :return: None
        """
        self.cursor.execute('DELETE FROM podcasts WHERE name = ?', (name,))


class Feed(Database):
    """
    Contains methods for managing rss feed subscriptions
    """

    def __init__(self, db_file: str = Config.database):
        self._db_file = db_file
        super(Feed, self).__init__(self._db_file)
        self._logger = logger('feed')

    def add(self, *urls) -> None:
        """
        Parses and validates rss feed urls, adds to
        database and create download directory for each new feed
        :param urls: rss feed urls to add to subscription database
        :return: None
        """
        podcasts = self.fetch_single_column('url')
        option, base_directory = self.options()
        for url in urls:
            if url not in podcasts:
                try:
                    page = fp.parse(url)
                    episodes = page.entries
                    if not episodes:
                        msg = f'No episodes found for {url}'
                        print(msg)
                        self._logger.warning(msg)
                        return
                    if option == 1:
                        date = str(self.last_episode_only(episodes))
                    else:
                        date = str(datetime.fromtimestamp(0))
                    if page:
                        podcast_name = page.feed.title
                        download_dir = path.join(base_directory, podcast_name)
                        self.add_podcast(podcast_name, url, download_dir, date)
                        pathlib.Path(base_directory).joinpath(podcast_name).\
                            mkdir(parents=True, exist_ok=True)
                        msg = f'{page.feed.title} added!'
                        print(msg)
                        self._logger.info(msg)
                except KeyError:
                    msg = 'Error, podcast not added!'
                    print(msg)
                    self._logger.warning(msg)
            else:
                msg = f'{url} already in database!'
                print(msg)
                self._logger.warning(msg)

    def remove(self) -> None:
        """
        Used to remove a podcast from database.
        :return: None
        """
        podcasts = {i[0]: i[1] for i in enumerate(self.fetch_single_column('name'))}
        if not podcasts:
            print('You have no subscriptions!')
            return
        for num, podcast in podcasts.items():
            print(f'{num}: {podcast}')
        try:
            choice = int(input('Podcast number to remove: '))
            if choice not in podcasts:
                print('Invalid option')
                return
            self.remove_podcast(podcasts[choice])
            msg = f'Removed {podcasts[choice]}'
            print(msg)
            self._logger.info(msg)
        except ValueError:
            print('Invalid Option, enter a number')

    @staticmethod
    def last_episode_only(episodes) -> datetime:
        """
        TODO this probably isn't a great way to do this.  It causes problems like podcasts
        that download repeatedly each time the program is run
        When adding a podcast to database, a date is needed, this method
        is used when option is set to only download new episodes.
        :param episodes: feedparse.parse(url).entries
        :return: datetime object 1 min older than latest released episode
        """
        first, second = datetime.fromtimestamp(mktime(episodes[0].published_parsed)), \
            datetime.fromtimestamp(mktime(episodes[1].published_parsed))
        if first < second:
            episodes = episodes[::-1]
        latest_episode = datetime.fromtimestamp(mktime(episodes[0].published_parsed))
        return latest_episode - timedelta(minutes=1)

    def print_subscriptions(self) -> False or list:
        """
        Prints out current subscriptions, intended to be used with CLI.
        :return: None
        """
        podcasts = self.fetch_single_column('name')
        if podcasts:
            print(' -- Current Subscriptions -- ')
            for podcast in podcasts:
                print(podcast)
            return podcasts
        else:
            print('You have no subscriptions!')
        return False

    def print_options(self) -> tuple:
        """
        Prints currently selected options
        :return: None
        """
        valid_options = {0: 'New podcasts download all episodes\n',
                         1: 'New podcasts download only new episodes\n'}
        new_only, download_directory = self.options()
        print('-- Options --')
        print(f'{valid_options[new_only]}Download Directory: {download_directory}')
        print('-------------')
        return new_only, download_directory

    def set_directory_option(self, directory) -> bool:
        """
        :param directory: string, abs path to base download directory
        :return: None
        """
        if access(directory, W_OK) and access(directory, R_OK):
            self.change_option('base_directory', directory)
            msg = f'Changed download directory to {directory}'
            print(msg)
            self._logger.info(msg)
            return True
        msg = f'Invalid directory: {directory}'
        print(msg)
        self._logger.warning(msg)
        return False

    def set_catalog_option(self, option) -> bool:
        """
        :param option: string, catalog option desired
        :return: None
        """
        valid_options = {'all': '0', 'new': '1'}
        if option not in valid_options:
            msg = f'Invalid option: {option}'
            print(msg)
            self._logger.warning(msg)
            return False
        self.change_option('new_only', valid_options[option])
        msg = f'Set catalog option to {option}'
        print(msg)
        self._logger.info(msg)
        return True


class DataB:
    """
    Handles database operations
    """
    def __init__(self, db_file: str = Config.database):
        self._db_file = db_file
        self._conn = sqlite3.connect(self._db_file)
        self._conn.execute('PRAGMA foreign_keys=ON')
        self.cursor = self._conn.cursor()
        self._logger = logger()

    def __enter__(self):
        return self

    def __exit__(self,
                 exc_type,
                 exc_val,
                 exc_tb: TracebackType):
        """
        If there are exceptions, rolls back and calls logger
        :param exc_type: exception type
        :param exc_val:  exception value
        :param exc_tb: exception traceback
        :return: None
        """
        if exc_type is not None:
            self._conn.rollback()
            self._logger.error(exc_type, exc_val, exc_tb)

        else:
            self._conn.commit()
        self._conn.close()

    def __repr__(self):
        return f'{self.__class__.__name__}({self._db_file})'

    def add_podcast(self, name: str, url: str, directory: str) -> None:
        """

        :param name: podcast name
        :param url: rss feed url
        :param directory: directory to store this podcast's downloaded episodes
        :return: None
        """
        self.cursor.executemany('INSERT INTO podcasts (name, url, directory) VALUES (?,?,?)',
                                ((name, url, directory),))
        self._conn.commit()

    def remove_podcast(self, url: str) -> None:
        """

        :param url: rss feed url
        :return: None
        """
        self.cursor.execute('DELETE FROM episodes WHERE podcast_id IN'
                            ' (SELECT id FROM podcasts p WHERE p.url = ?)', (url,))
        self.cursor.execute('DELETE FROM  podcasts WHERE url = ?',
                            (url,))
        self._conn.commit()

    def get_podcasts(self) -> list:
        """
        :return: list of tuples
        """
        self.cursor.execute('SELECT name, url, directory FROM main.podcasts')
        return self.cursor.fetchall()

    def add_episode(self,
                    podcast_url: str,
                    feed_id: str,) -> None:
        """
        :param podcast_url: RSS feed URL
        :param feed_id: id generated by rss feed for each episode
        :return: None
        """
        self.cursor.execute('INSERT INTO episodes (feed_id, podcast_id) '
                            'SELECT ?, id FROM main.podcasts WHERE url = ?',
                            (feed_id, podcast_url))

    def get_episodes(self, url: str) -> list:
        """
        :param url: rss feed url
        :return: list of episode ids associated with url
        """
        self.cursor.execute('SELECT feed_id FROM episodes '
                            'JOIN podcasts p ON episodes.podcast_id = p.id AND p.url = ?',
                            (url,))
        return [item[0] for item in self.cursor.fetchall()]

    def get_options(self) -> tuple:
        """
        :return: tuple of currently set options
        """
        self.cursor.execute('SELECT new_only, download_directory FROM settings')
        return self.cursor.fetchone()

    def change_option(self, option: str, value: str or int) -> None:
        """
        I know, I know, using a database query with an fstring is problematic,
        à la bobby tables, but the user doesn't interact directly with the
        database with this or any other queries that use fstrings in queries.
        All values input by the user are parameterized, which mitigates the threat.
        Given what this application is and does, I'm not sure why any user would
        try to sql injection on a local db of which they have sole access.
        :param option: string, option to change
        :param value: string, option's new value
        :return: None
        """
        self.cursor.execute(f'UPDATE settings SET {option} = ? WHERE id = 1', (value,))
        self._conn.commit()


class Feeds(DataB):
    """
    Contains methods for managing rss feeds
    """

    def add(self, *urls) -> None:
        """
        Parses and validates rss feed urls, adds to database, creates
        download directory for each new feed added
        :param urls: rss feed urls
        :return: None
        """
        try:
            for url in urls:
                catalog_option, dl_dir = self.get_options()
                feed = fp.parse(url)
                episodes = feed.entries
                if not episodes:
                    msg = f'No episodes at {url}'
                    print(msg)
                    self._logger.info(msg)
                    return
                podcast_name = feed.feed.title
                podcast_dir = path.join(dl_dir, podcast_name)
                self.add_podcast(name=podcast_name, url=url, directory=podcast_dir)
                if catalog_option:  # If true, add all episodes except newest to database
                    self.new_podcast_only(feed=feed)
                pathlib.Path(dl_dir).joinpath(podcast_name).\
                    mkdir(parents=True, exist_ok=True)
                msg = f'{podcast_name} added!'
                print(msg)
                self._logger.info(msg)

        except sqlite3.IntegrityError:
            self._logger.warning('Podcast already in feed.')
        except KeyError:
            self._logger.exception('Error, podcast not added')

    def remove(self) -> None:
        """
        Used with simple CLI interface, used to remove a podcast from database
        :return: None
        """
        podcasts = {i[0]: i[1] for i in enumerate(self.get_podcasts())}
        if not podcasts:
            print('You have no subscriptions!')
            return
        print(podcasts)
        for num, podcast in podcasts.items():
            print(f'{num}: {podcast[0]}')
        try:
            choice = int(input('Podcast number to remove: '))
            if choice not in podcasts:
                print('Invalid option')
                return
            self.remove_podcast(podcasts[choice][1])
            msg = f'Removed {podcasts[choice][0]}'
            print(msg)
            self._logger.info(msg)
        except ValueError:
            print('Invalid option, enter a number')

    def new_podcast_only(self, feed: fp.FeedParserDict) -> None:
        """
        Loops through episodes, adding all episodes to the database, except for the newest one
        :param feed: FeedParserDict of a single feed
        :return:
        """
        episodes = feed.entries
        first = episodes[0].published_parsed
        last = episodes[-1].published_parsed
        if first < last:  # Last is the latest episode, i.e., feed is reversed
            episodes = episodes[:-1]
        else:
            episodes = episodes[1:]
        for epi in episodes:
            self.add_episode(feed_id=epi.id, podcast_url=feed.href)

    def print_options(self) -> tuple:
        """
        Prints currently selected options
        :return: None
        """
        valid_options = {0: 'New podcasts download all episodes\n',
                         1: 'New podcasts download only new episodes\n'}
        new_only, download_directory = self.get_options()
        print('-- Options --')
        print(f'{valid_options[new_only]}Download Directory: {download_directory}')
        print('-------------')
        return new_only, download_directory

    def set_directory_option(self, directory) -> bool:
        """
        :param directory: string, abs path to base download directory
        :return: None
        """
        if access(directory, W_OK) and access(directory, R_OK):
            self.change_option('download_directory', directory)
            msg = f'Changed download directory to {directory}'
            print(msg)
            self._logger.info(msg)
            return True
        msg = f'Invalid directory: {directory}'
        print(msg)
        self._logger.warning(msg)
        return False

    def set_catalog_option(self, option) -> bool:
        """
        :param option: string, catalog option desired
        :return: None
        """
        valid_options = {'all': '0', 'new': '1'}
        if option not in valid_options:
            msg = f'Invalid option: {option}'
            print(msg)
            self._logger.warning(msg)
            return False
        self.change_option('new_only', valid_options[option])
        msg = f'Set catalog option to {option}'
        print(msg)
        self._logger.info(msg)
        return True


class Worker:
    """
    Gets items from Queue, adds those episodes to the database
    """

    def __init__(self, queue: Queue):
        """
        :param queue: Queue
        """
        self.queue = queue
        self.database = DataB
        self.thread = Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

    def _run(self):
        while True:
            if not self.queue.empty():
                episode = self.queue.get()
                with self.database() as db:
                    db.add_episode(episode.entry.id, episode.podcast_url)


def create_database(database: str = Config.database) -> None:
    """
            Looks in the directory of the given filename, if the file is absent,
            it creates the database with default values.
            :param database: string, abs path of database file
            :return: None
            """
    files = [path.join(path.dirname(database), item) for item in
             listdir(path.dirname(database))]
    if database not in files:
        with DataB(database) as db:
            cur = db.cursor
            cur.execute('CREATE TABLE IF NOT EXISTS podcasts '
                        '(id INTEGER PRIMARY KEY, '
                        'name TEXT, '
                        'url TEXT UNIQUE, '
                        'directory TEXT)')
            cur.execute('CREATE TABLE IF NOT EXISTS episodes '
                        '(id INTEGER PRIMARY KEY, '
                        'feed_id TEXT, '
                        'podcast_id INTEGER NOT NULL,'
                        'FOREIGN KEY (podcast_id) REFERENCES podcasts(id))')
            cur.execute('CREATE TABLE IF NOT EXISTS settings '
                        '(id INTEGER PRIMARY KEY, '
                        'new_only BOOLEAN, '
                        'download_directory TEXT)')
            cur.execute('INSERT INTO settings (new_only, download_directory) VALUES (?,?)',
                        (1, path.join(pathlib.Path.home(), 'Podcasts')),)
