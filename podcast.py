from collections import namedtuple
from datetime import datetime
from os import path
from time import mktime
from urllib.request import urlretrieve

import feedparser as fp
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp4 import MP4

from miscfunctions import logger
from database import DB


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
