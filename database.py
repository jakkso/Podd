from os import listdir, path
import pathlib
import sqlite3

from miscfunctions import logger


class DB:

    def __init__(self, database):
        """
        :param database: string, path to database file
        """
        self.database = database
        self.conn = sqlite3.connect(self.database)
        self.cursor = self.conn.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
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
            print('Error')
            logger(exc_type, exc_val, exc_tb)
        else:
            self.conn.commit()
            self.conn.close()

    def __repr__(self):
        return f'{self.__class__.__name__}({self.database})'

    @staticmethod
    def create(database):
        """
        Looks in the directory of the given filename, if the file is absent,
        it creates the database with default values.
        :param database: string, path of database file
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

    def options(self):
        """
        :return: tuple of currently set options
        """
        self.cursor.execute('SELECT new_only, base_directory FROM settings')
        return self.cursor.fetchone()

    def subscriptions(self):
        """

        :return: list of 3-tuples, consisting of the url, download directory
        and latest download date of each podcast
        """
        self.cursor.execute('SELECT url, directory, date FROM podcasts')
        return self.cursor.fetchall()

    def change_download_date(self, date, podcast_name):
        """
        Changes download date for podcast name
        :param date: datetime object, coerced to a string
        :param podcast_name: name of podcast
        :return: None
        """
        self.cursor.execute('UPDATE podcasts SET date = ? WHERE name = ?',
                            (date, podcast_name), )

    def change_option(self, option, value):
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

    def fetch_single_column(self, column):
        """
        :param column: name of column to fetch
        :return: list of contents of said column
        """
        self.cursor.execute(f'SELECT {column} FROM podcasts')
        return [item[0] for item in self.cursor.fetchall()]

    def add_podcast(self, podcast_name, feed_url, download_directory, date):
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

    def remove_podcast(self, url):
        """
        Deletes row where url matches
        :param url: rss feed url
        :return: None
        """
        self.cursor.execute('DELETE FROM podcasts WHERE name is ?', (url,))

