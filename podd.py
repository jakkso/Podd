"""
Sets up CLI and integrates various classes into downloader function
"""

from argparse import ArgumentParser as Ag
from multiprocessing.dummy import Pool as ThreadPool
from queue import Queue

from database import Database, Feed, EpisodeUpdater, create_database
from message import Message
from podcast import Podcast, Episode

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
                for line in file:
                    if line.strip != '':
                        feed.add(line.strip())
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
    refreshes subscriptions, downloads new episodes, sends email messages
    :return:
    """
    jinja_packets = []
    to_dl = []
    with Database() as _db:
        subs = _db.get_podcasts()
    for sub in subs:
        _, url, dl_dir = sub
        with Podcast(url, dl_dir) as pod:
            j_packet = pod.episodes()
            if j_packet:
                jinja_packets.append(j_packet)
                to_dl.extend(j_packet.episodes)
    if jinja_packets:
        EpisodeUpdater(QUEUE)
        pool = ThreadPool(3)
        pool.map(threaded_download, to_dl)
        pool.close()
        pool.join()
        QUEUE.put('stop')  # 'Poison pill' to kill EpisodeUpdater worker
        Message(jinja_packets).send()
    else:
        print('No new episodes')


def threaded_download(episode: Episode) -> None:
    """
    :param: episode Episode obj
    :return:
    """
    print(f'Downloading {episode.title}')
    QUEUE.put(episode)
    episode.download()
    episode.tag()


if __name__ == '__main__':
    create_database()
    main()
