"""
Contains classes used to refresh podcast feeds and download episodes
"""
from collections import namedtuple
from os import path
from http import client
from urllib.request import urlretrieve
from urllib.error import HTTPError

import feedparser as fp
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp4 import MP4

from database import Database
from utilities import logger

# Some podcast feeds send a silly amount of headers, crashing downloader func. Default is 100
client._MAXHEADERS = 1000


class Podcast:
    """
    Contains data about a specific podcast
    """

    JinjaPacket = namedtuple('JinjaPacket', 'name image episodes')

    __slots__ = ['_url',
                 '_dl_dir',
                 '_logger',
                 '_name',
                 '_image',
                 '_new_episodes']

    def __init__(self, url: str, directory: str):
        """

        :param url: rss feed url for this podcast
        :param directory: download directory for this podcast
        """
        self._url = url
        self._dl_dir = directory
        self._logger = logger('podcast')
        _old_eps = Database().get_episodes(self._url)
        _feed = fp.parse(self._url)
        self._name = _feed.feed.title
        self._image = _feed.feed.image.href
        self._new_episodes = [item for item in _feed.entries if item.id not in _old_eps]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._logger.error(exc_type, exc_val, exc_tb)

    def episodes(self) -> JinjaPacket or False:
        """
        :return: JinjaPacket if episodes need to be downloaded, False otherwise
        """
        if self._new_episodes:
            episode_list = [Episode(self._dl_dir,
                                    entry,
                                    self._name,
                                    self._url)
                            for entry in self._new_episodes]
            return self.JinjaPacket(self._name,
                                    self._image,
                                    episode_list)
        return False


class Episode:
    """
    Contains data and methods to generate that data, about an episode
    """

    types = ('.mp3', '.m4a', '.wav', '.mp4', '.m4v', '.mov', '.avi', '.wmv')

    __slots__ = ['_dl_dir',
                 'entry',
                 '_podcast_name',
                 '_logger',
                 'podcast_url',
                 'title',
                 'summary',
                 'image',
                 'url',
                 'filename']

    def __init__(self,
                 directory: str,
                 entry: fp.FeedParserDict,
                 podcast_name: str,
                 podcast_url: str):
        """
        :param directory: download directory
        :param entry: single FeedParserDict from fp.parse(url).entries list
        :param podcast_name:
        """
        self._dl_dir = directory
        self.entry = entry
        self._podcast_name = podcast_name
        self._logger = logger('episode')
        self.podcast_url = podcast_url
        self.title = self.entry.title
        self.summary = self.entry.summary
        self.image = self._image_url()
        self.url = self._audio_file_url()
        self.filename = self._file_parser()

    def download(self) -> None:
        """
        Attempts to download episode
        :return: None
        """
        try:
            urlretrieve(self.url, filename=self.filename)
            self._logger.info(f'Downloaded {self.filename}')
        except HTTPError:
            self._logger.exception(f'Connection error, unable to download {self.url}')
            print(f'Connection error, unable to download {self.url}')
        except FileNotFoundError:
            self._logger.exception(f'Unable to open file or directory at {self.filename}')
            print(f'Unable to open {self.filename}')

    def tag(self) -> None:
        """
        Uses mutagen's File class to try to discover what type of audio file
        is being tagged, then uses either mp3 or mp4 tagger on file, if type
        is either mp3 or mp4.  Otherwise, passes
        :return: None
        """
        try:
            audio = mutagen.File(self.filename).pprint()
            if 'mp3' in audio:
                self._mp3_tagger()
            elif 'mp4' in audio:
                self._mp4_tagger()
            else:
                self._logger.warning(f'Unable to determine filetype for {self.filename}')
        except AttributeError or mutagen.MutagenError:
            self._logger.warning(f'Unable to tag {self.filename}')

    def _image_url(self):
        """
        :return: link to episode image if it exists and isn't the same as
        the podcast image, else None
        """
        try:
            image = self.entry.image.href
        except AttributeError:
            image = None
            self._logger.info(f'No image found for {self._podcast_name}'
                              f' episode {self.title})')
        return image

    def _audio_file_url(self) -> str:
        """
        :return: url to episode audio file.  Feed parser encloses file links in ...
        enclosures!  There might be a better way to parse this.
        """
        url = None
        for link in self.entry.links:
            if link.rel == 'enclosure':
                url = link.href
        return url

    def _file_parser(self) -> path:
        """
        :return: str, ex: path/to/podcast/directory/episode.m4a
        Defaults to .mp3 as that's the most common filetype
        """
        for ext in self.types:
            if ext in self.url:
                return path.join(self._dl_dir, ''.join([self.title.replace('/', '-'), ext]))
        return path.join(self._dl_dir, ''.join([self.title, '.mp3']))

    def _mp3_tagger(self) -> None:
        """
        Uses mutagen to write tags to mp3 file
        :return: None
        """
        try:
            tag = EasyID3(self.filename)
        except ID3NoHeaderError:
            tag = mutagen.File(self.filename, easy=True)
            tag.add_tags()
        tag[u'title'] = self.title
        tag[u'artist'] = self._podcast_name
        tag[u'album'] = self._podcast_name
        tag[u'genre'] = 'Podcast'
        tag.save(self.filename)
        self._logger.info(f'Tagged {self.filename}')

    def _mp4_tagger(self) -> None:
        """
        Uses mutagen to write tags to mp4 file
        :return: None
        """
        tag = mutagen.mp4.MP4(self.filename).tags
        tag['\xa9nam'] = self.title
        tag['\xa9ART'] = self._podcast_name  # Artist
        tag['\xa9alb'] = self._podcast_name  # Album
        tag['\xa9gen'] = 'Podcast'  # Genre
        tag.save(self.filename)
        self._logger.info(f'Tagged {self.filename}')
