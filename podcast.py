from collections import namedtuple
from datetime import datetime
from time import mktime

import feedparser as fp

from database import DB
from episode import Episode


class Podcast(DB):

    JinjaPacket = namedtuple('JinjaPacket', 'name link summary image episodes')

    def __init__(self, database, date, directory, url):
        """
        :param date: datetime obj, gotten from database
        :param directory: string, download directory for this particular podcast
        :param url: string, rss feed url for this podcast
        :param database: string, location of database file
        """

        DB.__init__(self, database)
        self.last_download_date = date
        self.directory = directory
        self.url = url
        self.parsed = fp.parse(self.url)
        self.name = self.parsed.feed.title
        self.link = self.parsed.feed.link
        self.summary = self.parsed.feed.summary
        self.image = self.parsed.feed.image.href
        self.entries = self.parsed.entries

    def __repr__(self):
        return f'{self.__class__.__name__}({self.database}, ' \
               f'{self.last_download_date}, {self.directory}, {self.url})'

    def downloader(self):
        """
        :return: JinjaPacket if episodes were downloaded, else None
        """
        episodes = [epi for epi in self.episodes()]
        if len(episodes) > 0:
            return self.JinjaPacket(self.name, self.link, self.summary, self.image, episodes)

    def episodes(self):
        """
        Parses feedparser.parse(url).entries, downloads and tags files
        :yield: Episode objects for use in jinja templates
        """
        for entry in self.entries:
            if self.last_download_date < datetime.fromtimestamp(mktime(entry.published_parsed)):
                episode = Episode(self.database, self.directory, entry, self.name)
                episode.downloader()
                episode.tagger()
                yield episode
