"""
Sets up CLI
"""

from argparse import ArgumentParser as Ag

from podd.config import Config
from podd.database import Feed, Options
from podd.downloader import downloader


def cli() -> None:
    """
    CLI implementation
    :return: None
    """
    parser = parser_creator()
    args = parser.parse_args()
    if args.option:
        Options().print_options()
    elif args.catalog:
        Options().set_catalog_option(args.catalog.lower())
    elif args.base:
        Options().set_directory_option(args.base)
    elif args.add:
        Feed().add(args.add)
    elif args.ADD:
        with open(args.ADD) as file:
            with Feed() as feed:
                for line in file:
                    if line.strip != '':
                        feed.add(line.strip())
    elif args.list:
        Feed().print_subscriptions()
    elif args.remove:
        Feed().remove()
    elif args.download:
        downloader()
    elif args.email_notifications:
        Options().email_notification_setup()
    elif args.notifications:
        Options().toggle_notifications(args.notifications.lower())
    elif args.version:
        print(Config.version)
    else:
        parser.print_help()


def parser_creator() -> Ag:
    """
    Sets up argument parser
    :return: ArgumentParser
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
                            when adding new podcasts. Valid options: `all` or `new`.')
    parser.add_argument('-e', '--email_notifications', action='store_true',
                        help='Setup email notifications')
    parser.add_argument('-n', '--notifications',
                        help='Turns email notifications on and off.'
                             '  Valid options: `on` or `off`.')
    parser.add_argument('-v', '--version',
                        help='Prints program version',
                        action='store_true')
    return parser
