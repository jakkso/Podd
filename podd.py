"""
Sets up CLI and integrates various classes into downloader function
"""

from argparse import ArgumentParser as Ag
import asyncio
from datetime import datetime

import aiohttp

from config import Config
from database import Database, Feed
from message import Message
from podcast import Podcast, episode_downloader


def main() -> None:
    """
    CLI implementation
    :return: None
    """
    parser = Ag()
    parser.add_argument('-d', '--download',
                        help='Refreshes feeds and downloads all new episodes',
                        action='store_true')
    parser.add_argument('-l', '--list',
                        help='Prints all current subscriptions',
                        action='store_true')
    parser.add_argument('-b', '--base',
                        help='Sets the base download directory, absolute references only')
    parser.add_argument('-a', '--add', help='Add single Feed to database')
    parser.add_argument('-A', '--ADD', help='Add line separated file of feeds to database')
    parser.add_argument('-o', '--option', help='Prints currently set options', action='store_true')
    parser.add_argument('-r', '--remove', help='Deletion menu', action='store_true')
    parser.add_argument('-c', '--catalog',
                        help='Sets option to download new episodes only or entire catalog, applied \
                        when adding new podcasts. Valid options: all & new.')
    args = parser.parse_args()

    if args.option:
        Feed().print_options()
    elif args.catalog:
        with Feed() as feed:
            feed.set_catalog_option(args.catalog.lower())
    elif args.base:
        with Feed() as feed:
            feed.set_directory_option(args.base)
    elif args.add:
        with Feed() as feed:
            feed.add(args.add)
    elif args.ADD:
        with open(args.ADD) as file:
            with Feed() as feed:
                feed.add(*[line.strip() for line in file if line.strip() != ''])
    elif args.list:
        Feed().print_subscriptions()
    elif args.remove:
        with Feed() as feed:
            feed.remove()
    elif args.download:
        downloader()
    else:
        parser.print_help()


def downloader() -> None:
    """
    Refreshes subs, downloads episodes and sends email
    """
    async def async_download() -> None:
        """

        :return: None
        """
        async with aiohttp.ClientSession(loop=loop) as session:
            for episode in download_list:
                await episode_downloader(session, episode)

    jinja_packets = []
    download_list = []
    with Database() as _db:
        subs = _db.subscriptions()
    for sub in subs:
        url, directory, date = sub
        date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        with Podcast(date, directory, url) as podcast:
            jinja_packet = podcast.episodes()
            if jinja_packet:
                jinja_packets.append(jinja_packet)
                download_list.extend(jinja_packet.episodes)
    if jinja_packets and download_list:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(async_download())
        Message(jinja_packets).send()


if __name__ == '__main__':
    Database.create(Config.database)
    main()
