import feedparser as fp
from datetime import datetime, timedelta
from os import access, path, R_OK, W_OK
import pathlib
from time import mktime

from database import DB
from miscfunctions import logger


class Feed:

    __slots__ = ['database']

    def __init__(self, database):
        """
        :param database: string, abs location of database file.
        """
        self.database = database

    def __repr__(self):
        return f'{self.__class__.__name__}({self.database})'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Calls logger function if there are exceptions
        :param exc_type: exception type
        :param exc_val:  exception value
        :param exc_tb: exception traceback
        :return: None
        """
        if exc_type is not None:
            logger(exc_type, exc_val, exc_tb)

    def add(self, *urls):
        """
        Uses feedparser.parse(url) on each url in urls and if valid, adds to
        database and create download directory
        :param urls:
        :return: None
        """
        with DB(self.database) as db:
            podcasts = db.fetch_single_column('url')
            option, base_directory = db.options()
        for url in urls:
            if url not in podcasts:
                try:
                    page = fp.parse(url)
                    episodes = page.entries
                    if len(episodes) == 0:
                        print('No episodes found')
                        return
                    if option == 1:
                        date = self.last_episode_only(episodes)
                    else:
                        date = datetime.fromtimestamp(0)
                    if len(page) > 0:
                        podcast_name = page.feed.title
                        download_dir = path.join(base_directory, podcast_name)
                        with DB(self.database) as db:
                            db.add_podcast(podcast_name, url, download_dir, date)
                        pathlib.Path(base_directory).joinpath(podcast_name).\
                            mkdir(parents=True, exist_ok=True)
                        print(f'{page.feed.title} added!')
                except KeyError:
                    print('Error, podcast not added')

    def remove(self):
        """
        Intended to be used non-programmatically via CLI, used to remove a
        a podcast from database.
        :return: None
        """
        with DB(self.database) as db:
            podcasts = {i[0]: i[1] for i in enumerate(db.fetch_single_column('name'))}
            if len(podcasts) == 0:
                print('You have no subscriptions!')
                return
            for num, podcast in podcasts.items():
                print(f'{num}: {podcast}')
            try:
                choice = int(input('Podcast number to remove: '))
                if choice not in podcasts:
                    print('Invalid option')
                    return
                db.remove_podcast(podcasts[choice])
            except ValueError:
                print('Invalid Option, enter a number')

    @staticmethod
    def last_episode_only(episodes):
        """
        When adding a podcast to database, a date is needed, this method
        is used when option is set to only download new episodes.
        :param episodes: feedparse.parse(url).entries
        :return: datetime object 1 min older than latest released episode
        """
        a, b = datetime.fromtimestamp(mktime(episodes[0].published_parsed)), \
            datetime.fromtimestamp(mktime(episodes[1].published_parsed))
        if a < b:
            episodes = episodes[::-1]
        latest_episode = datetime.fromtimestamp(mktime(episodes[0].published_parsed))
        return latest_episode - timedelta(minutes=1)

    def print_subscriptions(self):
        """
        Prints out current subscriptions, intended to be used with CLI.
        :return: if there are subscriptions, list of podcast names else None
        """
        with DB(self.database) as db:
            podcasts = db.fetch_single_column('name')
        if len(podcasts) > 0:
            print(' -- Current Subscriptions -- ')
            for podcast in podcasts:
                print(podcast)
            return podcasts
        else:
            print('You have no subscriptions!')
            return

    def print_options(self):
        """
        Prints currently selected options
        :return: options
        """
        valid_options = {0: 'New podcasts download all episodes\n',
                         1: 'New podcasts download only new episodes\n'}
        with DB(self.database) as db:
            new_only, download_directory = db.options()
        print('-- Options --')
        print(f'{valid_options[new_only]}Download Directory: \
        {download_directory}')
        return new_only, download_directory

    def set_directory_option(self, directory):
        """
        :param directory: string, abs path to base download directory
        :return: None
        """
        if access(directory, W_OK) and access(directory, R_OK):
            with DB(self.database) as db:
                db.change_option('base_directory', directory)
            return True
        else:
            print('Invalid location')
            return

    def set_catalog_option(self, option):
        """
        :param option: string, catalog option desired
        :return: None if invalid option, True otherwise
        """
        valid_options = {'all': 0, 'new': 1}

        if option not in valid_options:
            print('Invalid option.  See help menu')
            return
        with DB(self.database) as db:
            db.change_option('new_only', valid_options[option])
            return True
