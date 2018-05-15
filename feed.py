"""
Contains classes used to manage podcast feeds
"""
from collections import namedtuple
from datetime import datetime, timedelta
from os import access, path, R_OK, W_OK
import pathlib
from time import mktime
from urllib.request import urlretrieve
from urllib.error import HTTPError

import feedparser as fp
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp4 import MP4

from database import Database, Logger


class Feed:
    """
    Contains methods for managing rss feeds
    """

    def __init__(self):
        self._database = Database
        self._logger = Logger('feed')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._logger.error(exc_type, exc_val, exc_tb)

    def add(self, *urls) -> None:
        """
        Parses and validates rss feed urls, adds to
        database and create download directory for each new feed
        :param urls: rss feed urls to add to subscription database
        :return: None
        """
        with self._database() as _db:
            podcasts = _db.fetch_single_column('url')
            option, base_directory = _db.options()
        for url in urls:
            if url not in podcasts:
                try:
                    page = fp.parse(url)
                    episodes = page.entries
                    if not episodes:
                        print('No episodes found!')
                        return
                    if option == 1:
                        date = str(self.last_episode_only(episodes))
                    else:
                        date = str(datetime.fromtimestamp(0))
                    if page:
                        podcast_name = page.feed.title
                        download_dir = path.join(base_directory, podcast_name)
                        with self._database as _db:
                            _db.add_podcast(podcast_name, url, download_dir, date)
                        pathlib.Path(base_directory).joinpath(podcast_name).\
                            mkdir(parents=True, exist_ok=True)
                        print(f'{page.feed.title} added!')
                        self._logger.info(f'{page.feed.title} added!')
                except KeyError:
                    print('Error, podcast not added!')
                    self._logger.warning('Error, podcast not added!')

    def remove(self) -> None:
        """
        Used to remove a podcast from database.
        :return: None
        """
        with self._database() as _db:
            podcasts = {i[0]: i[1] for i in enumerate(_db.fetch_single_column('name'))}
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
            with self._database() as _db:
                _db.remove_podcast(podcasts[choice])
        except ValueError:
            print('Invalid Option, enter a number')

    @staticmethod
    def last_episode_only(episodes) -> datetime:
        """
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

    def print_subscriptions(self) -> None:
        """
        Prints out current subscriptions, intended to be used with CLI.
        :return: None
        """
        with self._database() as _db:
            podcasts = _db.fetch_single_column('name')
        if podcasts:
            print(' -- Current Subscriptions -- ')
            for podcast in podcasts:
                print(podcast)
        else:
            print('You have no subscriptions!')

    def print_options(self) -> None:
        """
        Prints currently selected options
        :return: None
        """
        valid_options = {0: 'New podcasts download all episodes\n',
                         1: 'New podcasts download only new episodes\n'}
        with self._database() as _db:
            new_only, download_directory = _db.options()
        print('-- Options --')
        print(f'{valid_options[new_only]}Download Directory: {download_directory}')
        print('-------------')

    def set_directory_option(self, directory) -> None:
        """
        :param directory: string, abs path to base download directory
        :return: None
        """
        if access(directory, W_OK) and access(directory, R_OK):
            with self._database() as _db:
                _db.change_option('base_directory', directory)
        else:
            print('Invalid location')

    def set_catalog_option(self, option) -> None:
        """
        :param option: string, catalog option desired
        :return: None
        """
        valid_options = {'all': '0', 'new': '1'}
        if option not in valid_options:
            print('Invalid option.  See help menu')
            return
        with self._database() as _db:
            _db.change_option('new_only', valid_options[option])


class Podcast:
    """
    Instantiated by Downloader function, contains data about a particular podcast
    """

    JinjaPacket = namedtuple('JinjaPacket', 'name link summary image episodes')

    __slots__ = ['_last_download_date',
                 '_directory',
                 '_url',
                 '_logger',
                 '_parsed',
                 '_name',
                 '_link',
                 '_image',
                 '_entries',
                 '_summary']

    def __init__(self, date, directory, url, logger):
        """
        :param date: datetime obj, obtained from database
        :param directory: string, download directory for this particular podcast
        :param url: string, rss feed url for this podcast
        :param logger: Logger object, passed to Episode instantiations
        """
        self._last_download_date = date
        self._directory = directory
        self._url = url
        self._logger = logger
        self._parsed = fp.parse(self._url)
        self._name = self._parsed.feed.title
        self._link = self._parsed.feed.link
        self._image = self._parsed.feed.image.href
        self._entries = self._parsed.entries
        try:
            self._summary = self._parsed.feed.summary
        except AttributeError:
            self._summary = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._logger.error(exc_type, exc_val, exc_tb)

    def __repr__(self):
        return f'{self.__class__.__name__}({self._last_download_date},' \
               f' {self._directory}, {self._url}, {self._logger})'

    def downloader(self) -> JinjaPacket or False:
        """
        :return: JinjaPacket if episodes were downloaded
        """
        # I'm pretty sure this is horrific.  Using a generator
        # and then dumping output into a list makes no sense.
        episodes = [epi for epi in self.episodes()]
        if episodes:
            return self.JinjaPacket(self._name,
                                    self._link,
                                    self._summary,
                                    self._image, episodes)
        return False

    def episodes(self):
        """
        Parses feedparser.parse(url).entries, downloads and tags files
        :yield: Episode object for use in jinja templates
        """
        for entry in self._entries:
            if self._last_download_date < datetime.fromtimestamp(mktime(entry.published_parsed)):
                yield Episode(self._directory,
                              entry,
                              self._name,
                              self._logger)


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
                 '_file_link',
                 '_file',
                 '_publish_date',
                 '_logger']

    def __init__(self, directory, entry, podcast_name, logger):
        """
        :param directory:
        :param entry:
        :param podcast_name:
        :param logger:
        """
        self._database = Database
        self._directory = directory
        self._entry = entry
        self._podcast_name = podcast_name
        self._logger = logger
        self.title = self._entry.title
        self.summary = self._entry.summary
        self.image = self._episode_image_link()
        self._file_link = self._audio_file_link()
        self._file = self._file_parser()
        self._publish_date = datetime.fromtimestamp(mktime(self._entry.published_parsed))
        self.download()
        self.tag()

    def __repr__(self):
        return f'{self.__class__.__name__}({self._directory},' f'{self._entry}, ' \
               f'{self._podcast_name}, {self._logger})'

    def download(self) -> None:
        """
        uses urlretrieve to download file, then updates last download date in
        database, then calls Episode.tagger
        :return: None
        """
        try:
            urlretrieve(self._file_link, filename=self._file)
            with self._database as _db:
                _db.change_download_date(self._publish_date, self._podcast_name)
            self._logger.info(f'Downloaded {self._file}')
        except HTTPError as err:
            self._logger.error(HTTPError, err, err.__traceback__)

    def tag(self) -> None:
        """
        Uses mutagen's File class to try to discover what type of audio file
        is being tagged, then uses either mp3 or mp4 tagger on file, if type
        is either mp3 or mp4.  Otherwise, passes
        :return: None
        """
        try:
            audio = mutagen.File(self._file).pprint()
            if 'mp3' in audio:
                self._mp3_tagger()
            elif 'mp4' in audio:
                self._mp4_tagger()
            else:
                self._logger.warning(f'Unable to determine filetype for {self._file}')
        except AttributeError:
            self._logger.warning(f'Unable to tag {self._file}')

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

    def _audio_file_link(self) -> str:
        """
        :return: link to episode audio file.  Feed parser encloses file links in ...
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
            if ext in self._file_link:
                return path.join(self._directory, ''.join([self.title, ext]))
        return path.join(self._directory, ''.join([self.title, '.mp3']))

    def _mp3_tagger(self) -> None:
        """
        Uses mutagen to write tags to mp3 file
        :return: None
        """
        try:
            tag = EasyID3(self._file)
        except ID3NoHeaderError:
            tag = mutagen.File(self._file, easy=True)
            tag.add_tags()
        tag[u'title'] = self.title
        tag[u'artist'] = self._podcast_name
        tag[u'album'] = self._podcast_name
        tag[u'genre'] = 'Podcast'
        tag.save(self._file)
        self._logger.info(f'Tagged {self._file}')

    def _mp4_tagger(self) -> None:
        """
        Uses mutagen to write tags to mp4 file
        :return: None
        """
        tag = mutagen.mp4.MP4(self._file).tags
        tag['\xa9day'] = self._publish_date.strftime('%x')
        tag['\xa9nam'] = self.title
        tag['\xa9ART'] = self._podcast_name  # Artist
        tag['\xa9alb'] = self._podcast_name  # Album
        tag['\xa9gen'] = 'Podcast'  # Genre
        tag.save(self._file)
        self._logger.info(f'Tagged {self._file}')
