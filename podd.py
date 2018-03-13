from argparse import ArgumentParser as Ag
from datetime import datetime

from classes import DB, Feed, Message, Podcast
from config import Config


def main():
    parser = Ag()
    parser.add_argument('-d', '--download', help='Refreshes feeds and downloads all new episodes', action='store_true')
    parser.add_argument('-l', '--list', help='Prints all current subscriptions', action='store_true')
    parser.add_argument('-b', '--base', help='Sets the base download directory, absolute references only')
    parser.add_argument('-a', '--add', help='Add single Feed to database')
    parser.add_argument('-A', '--ADD', help='Add line separated file of feeds to database')
    parser.add_argument('-o', '--option', help='Prints currently set options', action='store_true')
    parser.add_argument('-r', '--remove', help='Deletion menu', action='store_true')
    parser.add_argument('-c', '--catalog', help='Sets option to download new episodes only or entire catalog, applied \
    when adding new podcasts. Valid options: all & new.')
    args = parser.parse_args()

    if args.option:
        Feed(Config.database).print_options()
    elif args.catalog:
        Feed(Config.database).set_catalog_option(args.catalog.lower())
    elif args.base:
        Feed(Config.database).set_directory_option(args.base)
    elif args.add:
        Feed(Config.database).add(args.add)
    elif args.ADD:
        with open(args.ADD) as file:
            Feed(Config.database).add([line.strip() for line in file if line.strip() != ''])
    elif args.list:
        Feed(Config.database).print_subscriptions()
    elif args.remove:
        Feed(Config.database).remove()
    elif args.download:
        downloader()
    else:
        parser.print_help()


def downloader():
    downloads = []
    with DB(Config.database) as db:
        subscriptions = db.subscriptions()
    for subscription in subscriptions:
        url, directory, date = subscription
        date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        with Podcast(date, directory, url, Config.database) as podcast:
            jinja_packet = podcast.downloader()
            if jinja_packet is not None:
                downloads.append(podcast.downloader())
    if len(downloads) > 0:
        Message(downloads).send()


if __name__ == '__main__':
    DB.create(Config.database)
    main()
