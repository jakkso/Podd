from datetime import datetime
from os import path
from time import mktime
from urllib.request import urlretrieve

import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp4 import MP4

from database import DB


class Episode(DB):

    types = ['.mp3', '.m4a', '.wav', '.mp4', '.m4v', '.mov', '.avi', '.wmv']

    def __init__(self, database, directory, entry, podcast_name):
        DB.__init__(self, database)
        self.directory = directory
        self.entry = entry
        self.podcast_name = podcast_name
        self.title = self.entry.title
        self.summary = self.entry.summary
        self.image = self._episode_image_link()
        self.file_link = self._audio_file_link()
        self.file = self._file()
        self.publish_date = datetime.fromtimestamp(mktime(self.entry.published_parsed))

    def __repr__(self):
        return f'{self.__class__.__name__}({self.database}, ' \
               f'{self.directory},' f'{self.entry}, {self.podcast_name})'

    def downloader(self):
        """
        uses urlretrieve to download file, then updates last download date in
        database
        :return: None
        """
        print(f'Downloading {self.title}')
        urlretrieve(self.file_link, filename=self.file)
        with self as db:
            db.change_download_date(self.publish_date, self.podcast_name)

    def _episode_image_link(self):
        """
        :return: link to episode image if it exists and isn't the same as
        the podcast image, else None
        """
        try:
            image = self.entry.image.href
            if image == self._episode_image_link:
                image = None
            return image
        except AttributeError:
            return

    def _audio_file_link(self):
        """
        :return: link to episode audio file
        """
        for link in self.entry.links:
            if link.rel == 'enclosure':
                return link.href

    def _file(self):
        """
        :return: str, ex: path/to/podcast/directory/episode.m4a
        Defaults to .mp3 as that's the most common filetype
        """
        for ext in self.types:
            if ext in self.file_link:
                return path.join(self.directory, ''.join([self.title, ext]))
        return path.join(self.directory, ''.join([self.title, '.mp3']))

    def tagger(self):
        """
        Uses mutagen's File class to try to discover what type of audio file
        is being tagged, then uses either mp3 or mp4 tagger on file, if type
        is either mp3 or mp4.  Otherwise, passes
        :return: None
        """
        try:
            audio = mutagen.File(self.file).pprint()
            if 'mp3' in audio:
                self._mp3_tagger()
            elif 'mp4' in audio:
                self._mp4_tagger()
        except AttributeError:
            pass

    def _mp3_tagger(self):
        """
        Uses mutagen to write tags to mp3 file
        :return: None
        """
        try:
            tag = EasyID3(self.file)
        except ID3NoHeaderError:
            tag = mutagen.File(self.file, easy=True)
            tag.add_tags()
        tag[u'title'] = self.title
        tag[u'artist'] = self.podcast_name
        tag[u'album'] = self.podcast_name
        tag[u'genre'] = 'Podcast'
        tag.save(self.file)

    def _mp4_tagger(self):
        """
        Uses mutagen to write tags to mp4 file
        :return: None
        """
        tag = mutagen.mp4.MP4(self.file).tags
        tag['\xa9day'] = self.publish_date.strftime('%x')
        tag['\xa9nam'] = self.title
        tag['\xa9ART'] = self.podcast_name  # Artist
        tag['\xa9alb'] = self.podcast_name  # Album
        tag['\xa9gen'] = 'Podcast'  # Genre
        tag.save(self.file)
