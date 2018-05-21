"""
Sets up CLI and integrates various classes into downloader function
"""

from argparse import ArgumentParser as Ag
from datetime import datetime
# from multiprocessing import Pool, Process, Queue
# from multiprocessing.pool import ThreadPool
from multiprocessing.dummy import Pool as ThreadPool
from os import cpu_count
from queue import Queue

# from multiprocess.pool import Pool,

from config import Config
from database import Database, DataB, Feeds, Feed, Worker
from message import Message
from podcast import Podcast, multiprocess_episode_downloader as mp_dl, NewPodcast, threaded_download as th_dl

QUEUE = Queue()


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
        new_downloader()
    else:
        parser.print_help()


def downloader() -> None:
    """
    Refreshes subs, downloads episodes and sends email
    """
    jinja_packets = []
    to_dl = []
    with Database() as _db:
        subs = _db.subscriptions()
    for sub in subs:
        url, directory, date = sub
        date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        with Podcast(date, directory, url) as podcast:
            jinja_packet = podcast.episodes()
            if jinja_packet:
                jinja_packets.append(jinja_packet)
                for epi in jinja_packet.episodes:
                    to_dl.append((epi.url, epi.filename, epi))
                    epi.increment_date()
    if jinja_packets:
        pool = Pool(cpu_count())
        pool.map(mp_dl, to_dl)
        Message(jinja_packets).send()
    #  Alright, it totally works.  Now to figure out how to tag & update the database
    # Tomorrow, I'll get it working.


def new_downloader() -> None:
    """
    refreshes subscriptions, downloads new episodes, sends email messages
    :return:
    """
    jinja_packets = []
    to_dl = []
    with DataB() as db:
        subs = db.get_podcasts()
    for sub in subs:
        _, url, dl_dir = sub
        with NewPodcast(url, dl_dir) as pod:
            j_packet = pod.episodes()
            if j_packet:
                jinja_packets.append(j_packet)
                to_dl.extend(j_packet.episodes)
    if jinja_packets:
        Worker(QUEUE)
        pool = ThreadPool(4)
        pool.map(th_dl, to_dl)
        pool.join()
        Message(jinja_packets).send()


if __name__ == '__main__':
    Database.create(Config.database)
    main()
