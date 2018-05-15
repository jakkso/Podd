from datetime import datetime as dt
from os import path
from time import mktime
from urllib.request import urlretrieve
from urllib.error import HTTPError

import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp4 import MP4

from database import Database

"""


"""


class Episode:

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

    def __init__(self, database, directory, entry, podcast_name, logger):
        """
        :param database:
        :param directory:
        :param entry:
        :param podcast_name:
        :param logger:
        """
        self._database = Database(database)
        self._directory = directory
        self._entry = entry
        self._podcast_name = podcast_name
        self._logger = logger
        self.title = self._entry.title
        self.summary = self._entry.summary
        self.image = self._episode_image_link()
        self._file_link = self._audio_file_link()
        self._file = self._file_parser()
        self._publish_date = dt.fromtimestamp(mktime(self._entry.published_parsed))
        self.download()
        self.tag()

    def __repr__(self):
        return f'{self.__class__.__name__}({self._database}, ' \
               f'{self._directory},' f'{self._entry}, {self._podcast_name}, {self._logger})'

    def download(self) -> None:
        """
        uses urlretrieve to download file, then updates last download date in
        database, then calls Episode.tagger
        :return: None
        """
        try:
            urlretrieve(self._file_link, filename=self._file)
            with self._database as db:
                db.change_download_date(self._publish_date, self._podcast_name)
            self._logger.info(f'Downloaded {self._file}')
        except HTTPError as err:
            # TODO fix error logging to just take error type and  error
            self._logger.error(HTTPError, err.__repr__(), err.__traceback__)

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
            return image
        except AttributeError as err:
            # TODO fix error logging to just take error type and  error
            self._logger.error(AttributeError, err.__repr__(), err.__traceback__)
            return

    def _audio_file_link(self) -> str:
        """
        :return: link to episode audio file.  Feed parser encloses file links in ...
        enclosures!  There might be a better way to parse this.
        """
        for link in self._entry.links:
            if link.rel == 'enclosure':
                return link.href

    def _file_parser(self) -> path:
        """
        :return: str, ex: path/to/podcast/directory/episode.m4a
        Defaults to .mp3 as that's the most common filetype
        TODO This is hot garbage, there's got to be a better way that this insane hack
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
        self._logger.info(f'Successfully tagged {self._file}')

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
        self._logger.info(f'Successfully tagged {self._file}')
