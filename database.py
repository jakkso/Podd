import datetime
import logging
from os import listdir, path
import pathlib
import sqlite3
import traceback
from types import TracebackType


class DB:

    def __init__(self, db_file: str):
        """
        :param db_file: string, path to sqlite database file
        """
        self.database = db_file
        self.conn = sqlite3.connect(self.database)
        self.cursor = self.conn.cursor()
        self.logger = logging.getLogger('database')
        self.logger.setLevel(logging.DEBUG)
        format_ = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler('database.log')
        file_handler.setLevel(logging.ERROR)
        file_handler.setFormatter(format_)
        self.logger.addHandler(file_handler)

    def __enter__(self):
        return self

    def __exit__(self,
                 exc_type: BaseException,
                 exc_val: str,
                 exc_tb: TracebackType):
        """
        If there are exceptions, rolls back and calls logger
        :param exc_type: exception type
        :param exc_val:  exception value
        :param exc_tb: exception traceback
        :return: None
        """
        if exc_type is not None:
            self.conn.rollback()
            self.conn.close()
            self.log_errors(exc_type, exc_val, exc_tb)

        else:
            self.conn.commit()
            self.conn.close()

    def __repr__(self):
        return f'{self.__class__.__name__}({self.database})'

    def log_errors(self,
                   err_type: BaseException,
                   err_value: str,
                   traceback_: TracebackType,
                   level=logging.ERROR) -> None:
        """
        Thanks to SO for help on this:
        https://stackoverflow.com/questions/5191830/how-do-i-log-a-python-error-with-debug \
        -information?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa
        :param err_type:
        :param err_value:
        :param traceback_:
        :param level: logging level
        :return: None
        """
        traceback_ = traceback.format_exception(err_type, err_value, traceback_)
        traceback_lines = []
        for line in [line.rstrip('\n') for line in traceback_]:
            traceback_lines.extend(line.splitlines())
        self.logger.log(level, traceback_lines.__str__())

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
            with DB(database) as db:
                c = db.cursor
                c.execute('CREATE TABLE IF NOT EXISTS podcasts \
                             (name text, url text, directory text, date text)')
                c.execute('CREATE TABLE IF NOT EXISTS settings \
                             (id INTEGER, new_only INTEGER, base_directory TEXT)')
                c.execute('INSERT INTO settings VALUES (?,?,?)',
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

    def change_download_date(self, date: datetime.date, podcast_name: str) -> None:
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
        All valued input by the user are parameterized, which mitigates the threat.
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

    def remove_podcast(self, url: str) -> None:
        """
        Deletes row where url matches
        :param url: rss feed url
        :return: None
        """
        self.cursor.execute('DELETE FROM podcasts WHERE name is ?', (url,))


class Logger:
    """
    Used to log events
    TODO change to be more abstract, accept kwargs to create loggers with
    different levels / file handlers per logger.  Is this best practice?
    Probably.
    """

    def __init__(self, log_name: str) -> logging.getLogger:
        """
        :param log_name: name of log
        """
        self.log_name = log_name
        self.logger = logging.getLogger(self.log_name)
        self.logger.setLevel(logging.DEBUG)
        fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_hdlr = logging.FileHandler(f'{self.log_name}.log')
        file_hdlr.setLevel(logging.DEBUG)
        file_hdlr.setFormatter(fmt)
        self.logger.addHandler(file_hdlr)

    def log(self,
            err_type: BaseException,
            err_value: str,
            traceback_: TracebackType,
            level=logging.ERROR) -> None:
        """
        Thanks to SO for help on this:
        https://stackoverflow.com/questions/5191830/how-do-i-log-a-python-error-with-debug \
        -information?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa
        :param err_type:
        :param err_value:
        :param traceback_:
        :param level: logging level
        :return: None
        """
        traceback_ = traceback.format_exception(err_type, err_value, traceback_)
        traceback_lines = []
        for line in [line.rstrip('\n') for line in traceback_]:
            traceback_lines.extend(line.splitlines())
        self.logger.log(level, traceback_lines.__str__())
