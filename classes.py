from collections import namedtuple
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from os import access, listdir, path, R_OK, W_OK
import pathlib
from pickle import dump, load
import smtplib
import sqlite3
from time import mktime
from urllib.request import urlretrieve

import feedparser as fp
from jinja2 import Environment, PackageLoader, select_autoescape
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp4 import MP4

from config import Config


class DB:

    __slots__ = ['database', 'conn', 'c']

    def __init__(self, database):
        """
        :param database: string, path to database file
        """
        self.database = database
        self.conn = sqlite3.connect(self.database)
        self.c = self.conn.cursor()

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
        return f'{self.__class__.__name__}("{self.database}")'

    def __str__(self):
        return f'{self.__class__.__name__} using {self.database} file'

    @property
    def cursor(self):
        return self.c

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
        self.c.execute('SELECT new_only, base_directory FROM settings')
        return self.c.fetchone()

    def subscriptions(self):
        """

        :return: list of 3-tuples, consisting of the url, download directory
        and latest download date of each podcast
        """
        self.c.execute('SELECT url, directory, date FROM podcasts')
        return self.c.fetchall()

    def change_download_date(self, date, podcast_name):
        """

        :param date: datetime object, coerced to a string
        :param podcast_name: name of podcast
        :return: None
        """
        self.c.execute('UPDATE podcasts SET date = ? WHERE name = ?',
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
        self.c.execute(f'UPDATE settings SET {option} = ? WHERE id = 1', (value,))

    def fetch_single_column(self, column):
        """
        :param column: name of column to fetch
        :return: list of contents of said column
        """
        self.c.execute(f'SELECT {column} FROM podcasts')
        return [item[0] for item in self.c.fetchall()]

    def add_podcast(self, podcast_name, feed_url, download_directory, date):
        """
        Adds podcast to database
        :param podcast_name:
        :param feed_url:
        :param download_directory: directory in which to save future downloads
        :param date: download episodes newer than this date
        :return: None
        """
        self.c.executemany('INSERT INTO podcasts VALUES (?,?,?,?)',
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
        self.c.execute('DELETE FROM podcasts WHERE url is ?', (url,))


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


class Podcast:

    JinjaPacket = namedtuple('JinjaPacket', 'name link summary image episodes')
    types = ['.mp3', '.m4a', '.wav', '.mp4', '.m4v', '.mov', '.avi', '.wmv']

    def __init__(self, date, directory, url, database):
        """
        :param date: datetime obj, gotten from database
        :param directory: string, download directory for this particular podcast
        :param url: string, rss feed url for this podcast
        :param database: string, location of database file
        """
        self.date = date
        self.directory = directory
        self.url = url
        self.database = database
        self.parsed = fp.parse(self.url)
        self.name = self.parsed.feed.title
        self.link = self.parsed.feed.link
        self.summary = self.parsed.feed.summary
        self.image = self.parsed.feed.image.href
        self.entries = self.parsed.entries

    def __repr__(self):
        return f'{self.__class__.__name__}({self.date}, {self.directory},' \
               f' {self.url}, {self.database})'

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

    def downloader(self):
        """
        :return: JinjaPacket if episodes were downloaded, else None
        """
        episodes = []
        for episode in self.episodes():
            episodes.append(episode)
        if len(episodes) > 0:
            return self.JinjaPacket(self.name, self.link, self.summary, self.image, episodes)

    def episodes(self):
        """
        Parses feedparser.parse(url).entries, downloads and tags files
        :yield: Episode objects for use in jinja templates
        """
        for entry in self.entries:
            if self.date < datetime.fromtimestamp(mktime(entry.published_parsed)):
                title = entry.title
                summary = entry.summary
                image = self._episode_image(entry)
                link = self._episode_link(entry)
                ext = self._episode_file_type(link)
                filename = path.join(self.directory, ''.join([title, ext]))
                date = datetime.fromtimestamp(mktime(entry.published_parsed))
                episode = Episode(title, summary, image, link, filename, date)
                self._episode_downloader(episode)
                self._episode_tag(episode)
                yield episode

    def _episode_downloader(self, episode):
        """
        uses urlretrieve to download file, then updates last download date in
        database
        :param episode: Episode object
        :return: None
        """
        urlretrieve(episode.link, filename=episode.filename)
        with DB(self.database) as db:
            db.change_download_date(episode.date, self.name)

    @staticmethod
    def _episode_image(entry):
        """

        :param entry: a single feedparser.parse(url).entries entry
        :return: link to episode image if it exists, else None
        """
        try:
            return entry.image.href
        except AttributeError:
            return

    @staticmethod
    def _episode_link(entry):
        """
        :param entry: a single feedparser.parse(url).entries entry
        :return: link to episode file
        """
        for link in entry.links:
            if link.rel == 'enclosure':
                return link.href

    def _episode_file_type(self, link):
        """
        Rudimentary extension parser.  Most files are .mp3, so that's the
        default
        :param link: link to episode file
        :return: string of extension, else .mp3
        """
        for ext in self.types:
            if ext in link:
                return ext
        return '.mp3'

    def _episode_tag(self, episode):
        """
        Uses mutagen's File class to try to discover what type of audio file
        is being tagged, then uses either mp3 or mp4 tagger on file, if type
        is either mp3 or mp4.  Otherwise, passes
        :param episode: Episode object
        :return: None
        """
        try:
            audio = mutagen.File(episode.filename).pprint()
            if 'mp3' in audio:
                self._mp3_tagger(episode)
            elif 'mp4' in audio:
                self._mp4_tagger(episode)
        except AttributeError:
            pass

    def _mp3_tagger(self, episode):
        """
        Uses mutagen to write tags to mp3 file
        :param episode: Episode object
        :return: None
        """
        try:
            tag = EasyID3(episode.filename)
        except ID3NoHeaderError:
            tag = mutagen.File(episode.filename, easy=True)
            tag.add_tags()
        tag[u'title'] = episode.title
        tag[u'artist'] = self.name
        tag[u'album'] = self.name
        tag[u'genre'] = 'Podcast'
        tag.save(episode.filename)

    def _mp4_tagger(self, episode):
        """
        Uses mutagen to write tags to mp4 file
        :param episode: Episode object
        :return: None
        """
        tag = mutagen.mp4.MP4(episode.filename).tags
        tag['\xa9day'] = episode.date.strftime('%x')
        tag['\xa9nam'] = episode.title
        tag['\xa9ART'] = self.name  # Artist
        tag['\xa9alb'] = self.name  # Album
        tag['\xa9gen'] = 'Podcast'  # Genre
        tag.save(episode.filename)


class Episode:

    __slots__ = ['title', 'summary', 'image', 'link', 'filename', 'date']

    def __init__(self, title, summary, image, link, filename, date):
        """

        :param title: string, episode title
        :param summary: string, episode summary
        :param image: string, url link to episode image, or None
        :param link: string, url link to episode file
        :param filename: string, name with which to save file
        :param date: datetime object, date when this episode was released
        """
        self.title = title
        self.summary = summary
        self.image = image
        self.link = link
        self.filename = filename
        self.date = date

    def __repr__(self):
        return f'Episode({self.title}, {self.summary}, {self.image},' \
               f' {self.link}, {self.filename}, {self.date})'


class Message:

    __slots__ = ['podcasts', 'text', 'html']

    def __init__(self, podcasts):
        """
        :param podcasts: a list of named tuples, made up of JinjaPackets, as
        described below, where name, link summary and image are all attributes
        related to that individual podcast.  Episodes are are a list
        of class Episode, as described below.

        JinjaPacket = namedtuple('JinjaPacket', 'name link summary image episodes')
        Episode(title, summary, image, link, filename, date)
        """
        self.podcasts = podcasts
        self.text = self.render_text()
        self.html = self.render_html()

    def __repr__(self):
        return f'{self.__class__.__name__}({self.podcasts})'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger(exc_type, exc_val, exc_tb)

    def render_html(self):
        """
        Uses self.podcasts to render an html page
        :return: rendered html
        """
        env = Environment(
            loader=PackageLoader('classes', 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        template = env.get_template('base.html')
        render = template.render(podcasts=self.podcasts)
        return render

    def render_text(self):
        """
        Uses self.podcasts to render a text page
        :return: rendered text page
        """
        env = Environment(
            loader=PackageLoader('classes', 'templates'),
            autoescape=select_autoescape(['.txt'])
        )
        template = env.get_template('base.txt')
        render = template.render(podcasts=self.podcasts)
        return render

    def send(self):
        """
        Creates an email using the above rendered html and text, logs into
        gmail and sends said email.
        :return: None
        """
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Podcast Download Report'
        msg['From'] = Config.bot
        msg['To'] = Config.recipient
        msg.attach(MIMEText(self.text, 'plain'))
        msg.attach(MIMEText(self.html, 'html'))
        server = smtplib.SMTP(host='smtp.gmail.com', port=587)
        server.starttls()
        server.login(user=Config.bot, password=Config.pw)
        server.sendmail(Config.bot, Config.recipient, msg.as_string())
        server.quit()


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
