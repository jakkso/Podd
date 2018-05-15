from collections import namedtuple
from datetime import datetime
from time import mktime

import feedparser as fp

from episode import Episode


class Podcast:

    JinjaPacket = namedtuple('JinjaPacket', 'name link summary image episodes')

    __slots__ = ['database',
                 'last_download_date',
                 'directory',
                 'url',
                 'logger',
                 'parsed',
                 'name',
                 'link',
                 'image',
                 'entries',
                 'summary']

    def __init__(self, database, date, directory, url, logger):
        """
        :param database: str: path to database file
        :param date: datetime obj, obtained from database
        :param directory: string, download directory for this particular podcast
        :param url: string, rss feed url for this podcast
        :param logger: Logger object, passed to Episode instantiations
        """
        self.database = database
        self.last_download_date = date
        self.directory = directory
        self.url = url
        self.logger = logger
        self.parsed = fp.parse(self.url)
        self.name = self.parsed.feed.title
        self.link = self.parsed.feed.link
        self.image = self.parsed.feed.image.href
        self.entries = self.parsed.entries
        try:
            self.summary = self.parsed.feed.summary
        except AttributeError:
            self.summary = None

    def __repr__(self):
        return f'{self.__class__.__name__}({self.database}, ' \
               f'{self.last_download_date}, {self.directory}, {self.url},' \
               f'{self.logger})'

    def downloader(self) -> JinjaPacket or None:
        """
        :return: JinjaPacket if episodes were downloaded
        """
        episodes = [epi for epi in self.episodes()]
        if len(episodes) > 0:
            return self.JinjaPacket(self.name, self.link, self.summary, self.image, episodes)

    def episodes(self):
        """
        Parses feedparser.parse(url).entries, downloads and tags files
        :yield: Episode object for use in jinja templates
        """
        for entry in self.entries:
            if self.last_download_date < datetime.fromtimestamp(mktime(entry.published_parsed)):
                yield Episode(self.database,
                              self.directory,
                              entry,
                              self.name,
                              self.logger)
