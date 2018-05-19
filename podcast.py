"""
Contains classes used to refresh podcast feeds and download episodes
"""
from collections import namedtuple
from datetime import datetime
from os import path
from time import mktime
from urllib.request import urlretrieve
from urllib.error import HTTPError

import aiofiles
import aiohttp
import feedparser as fp
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp4 import MP4

from database import Database
from utilities import logger


class Podcast:
    """
    Contains data about a particular podcast
    """

    JinjaPacket = namedtuple('JinjaPacket', 'name link image episodes')

    __slots__ = ['_last_download_date',
                 '_directory',
                 '_url',
                 '_logger',
                 '_parsed',
                 '_name',
                 '_link',
                 '_image',
                 '_entries']

    def __init__(self, date, directory, url):
        """
        :param date: datetime obj, obtained from database
        :param directory: string, download directory for this particular podcast
        :param url: string, rss feed url for this podcast
        """
        self._last_download_date = date
        self._directory = directory
        self._url = url
        self._logger = logger('podcast')
        self._parsed = fp.parse(self._url)
        self._name = self._parsed.feed.title
        self._link = self._parsed.feed.link
        self._image = self._parsed.feed.image.href
        self._entries = self._parsed.entries

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._logger.error(f'{exc_type} {exc_val} {exc_tb}')

    def __repr__(self):
        return f'{self.__class__.__name__}({self._last_download_date},' \
               f' {self._directory}, {self._url})'

    def episodes(self) -> JinjaPacket or False:
        """
        :return: JinjaPacket if episodes need to be downloaded, False otherwise
        """
        episode_list = []
        for entry in self._entries:
            if self._last_download_date < datetime.fromtimestamp(mktime(entry.published_parsed)):
                episode_list.append(Episode(self._directory,
                                            entry,
                                            self._name))
        if episode_list:
            return self.JinjaPacket(self._name,
                                    self._link,
                                    self._image,
                                    episode_list)
        return False


class Episode:
    """
    Contains methods to download and tag episodes
    """

    types = ('.mp3', '.m4a', '.wav', '.mp4', '.m4v', '.mov', '.avi', '.wmv')

    __slots__ = ['db_file',
                 '_database',
                 '_directory',
                 '_entry',
                 '_podcast_name',
                 'title',
                 'summary',
                 'image',
                 'url',
                 'filename',
                 '_publish_date',
                 '_logger']

    def __init__(self, directory: str, entry: fp.FeedParserDict, podcast_name: str):
        """
        :param directory:
        :param entry: single FeedParserDict from fp.parse(url).entries list
        :param podcast_name:
        """
        self._directory = directory
        self._entry = entry
        self._podcast_name = podcast_name
        self._logger = logger('episode')
        self.title = self._entry.title
        self.summary = self._entry.summary
        self.image = self._episode_image_link()
        self.url = self._audio_file_url()
        self.filename = self._file_parser()
        self._publish_date = datetime.fromtimestamp(mktime(self._entry.published_parsed))

    def __repr__(self):
        return f'{self.__class__.__name__}({self._directory},' f'{self._entry}, ' \
               f'{self._podcast_name})'

    def download(self) -> None:
        """
        Synchronous download method, not currently being used
        uses urlretrieve to download file, then updates last download date in
        database, then calls Episode.tagger
        :return: None
        """
        try:
            urlretrieve(self.url, filename=self.filename)
            self.increment_date()
            self._logger.info(f'Downloaded {self.filename}')
        except HTTPError:
            self._logger.exception(f'Connection error; unable to download {self.title}')
        except FileNotFoundError:
            self._logger.exception(f'Unable to open file or directory at {self.filename}.'
                                   f'  Probably because parent directory is missing.')

    def increment_date(self) -> None:
        """
        Changes download date in database to publish date.
        :return: None
        """
        with Database() as _db:
            _db.change_download_date(self._publish_date, self._podcast_name)

    def _episode_image_link(self) -> str or None:
        """
        :return: link to episode image if it exists and isn't the same as
        the podcast image, else None
        This isn't even working correctly.  Well, it is and it isn't: if the
        same image is hosted in different places, it can't detect that, but if
        the same URL is in both places, then it will work.  At the moment,
        I just link to the image and don't want to download the image to
        compare them.  I wonder if there's some sort of metadata that I could
        use instead?  More research needed
        """
        try:
            image = self._entry.image.href
            if image == self._episode_image_link:
                image = None
        except AttributeError:
            image = None
            self._logger.warning(f'No image found for {self._podcast_name}'
                                 f' episode {self.title})')
        return image

    def _audio_file_url(self) -> str:
        """
        :return: url to episode audio file.  Feed parser encloses file links in ...
        enclosures!  There might be a better way to parse this.
        """
        url = None
        for link in self._entry.links:
            if link.rel == 'enclosure':
                url = link.href
        return url

    def _file_parser(self) -> path:
        """
        :return: str, ex: path/to/podcast/directory/episode.m4a
        Defaults to .mp3 as that's the most common filetype
        TODO This is hot garbage, there's got to be a better way that this insane,
        TODO presumptuous hack
        """
        for ext in self.types:
            if ext in self.url:
                return path.join(self._directory, ''.join([self.title, ext]))
        return path.join(self._directory, ''.join([self.title, '.mp3']))

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
        except AttributeError:
            self._logger.warning(f'Unable to tag {self.filename}')

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
        tag['\xa9day'] = self._publish_date.strftime('%x')
        tag['\xa9nam'] = self.title
        tag['\xa9ART'] = self._podcast_name  # Artist
        tag['\xa9alb'] = self._podcast_name  # Album
        tag['\xa9gen'] = 'Podcast'  # Genre
        tag.save(self.filename)
        self._logger.info(f'Tagged {self.filename}')


async def episode_downloader(session: aiohttp.ClientSession,
                             episode: Episode,
                             chunk_size: int = 1024) -> None:
    """
    Downloads and tags episodes
    :param session: aiohttp.ClientSession
    :param episode: Episode object
    :param chunk_size: chunk size, default 1024 bytes
    :return: None
    """
    try:
        async with session.get(episode.url) as response:
            async with aiofiles.open(episode.filename, 'wb') as file:
                while True:
                    chunk = await response.content.read(chunk_size)
                    if not chunk:
                        break
                    await file.write(chunk)
            response.release()
            episode.increment_date()
            logger('episode').info(f'Downloaded {episode.filename}')
            episode.tag()
            return
    except FileNotFoundError:
        logger('episode').exception(f'Unable to open file or directory '
                                    f'at {episode.filename}')
