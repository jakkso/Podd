"""
Sets up CLI and integrates various classes into downloader function
"""

from argparse import ArgumentParser as Ag
import getpass
import smtplib


from podd.config import Config
from podd.database import Database, Feed, create_database
from podd.downloader import downloader


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
    parser.add_argument('-e', '--email_notifications', action='store_true',
                        help='Setup email notifications')
    parser.add_argument('-n', '--notifications',
                        help='Turns email notifications on and off.  Valid options are "on" and "off".')
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
    elif args.email_notifications:
        email_notification_setup()
    elif args.notifications:
        toggle_notifications(args.notifications.lower())
    else:
        parser.print_help()


def email_notification_setup(initial_setup: bool=False):
    """
    Interacts with user, get's sender email address and password, as well as recipient address
    :param initial_setup: bool if True, prints additional info
    :return: namedtuple of sender address and password and recipient address
    """
    if initial_setup:
        print('Looks like this is your first time running the program.')
        choice = input('Would you like to enable email notifications? (y/n) ').lower()
        if choice != 'y':
            print('Email notifications disabled.')
            return False
    print('\nNote: if you are using a Gmail account for this purpose, you need \n'
          'to enable app-specific passwords and enter one you\'ve generated, \n'
          'rather than your normal password.  This is somewhat risky, so it is\n'
          'advised that you do NOT use your main gmail account for this purpose. \n'
          'See https://support.google.com/accounts/answer/185833?hl=en for more info.\n'
          'The default values in config.py use the ones provided by gmail, \n'
          'if you choose to use a different email provider, replace them with the\n'
          'correct values.\n')
    print('First, enter in the address you want to use to send notifications')
    try:
        sender_address = input('Email address: ')
        password = getpass.getpass('Password: ')
        print('Validating password...')
        attempt = credential_validation(sender_address, password)
        if not attempt:
            print('Login attempt failed!')
            return
        print('Login successful!')
        print('\nNow enter the recipient email address.')
        recipient_address = input('Email address: ')
        with Database() as _db:
            _db.change_option('sender_address', sender_address)
            _db.change_option('sender_password', password)
            _db.change_option('recipient_address', recipient_address)
            _db.change_option('notification_status', True)
        print('Email notification enabled!')
    except KeyboardInterrupt:
        print('\nCanceling')
        quit()


def credential_validation(email_address: str, password: str) -> bool:
    """
    creates a simple smtp server and attempts to log in to server using the
    provided credentials
    :param email_address:
    :param password:
    :return: bool, True if login attempt was successful, False if not
    """
    server = smtplib.SMTP(host=Config.host, port=Config.port)
    server.starttls()
    try:
        server.login(user=email_address, password=password)
        server.quit()
        return True
    except smtplib.SMTPAuthenticationError:
        return False


def toggle_notifications(value: str) -> None:
    """
    Turns email notifications on or off, depending upon supplied value
    :param value:
    :return:
    """
    valid = {'on': True, 'off': False}
    if value not in valid:
        print('Invalid option')
        return
    with Database() as _db:
        _db.change_option('notification_status', valid[value])
    print(f'Notifications turned {value}.')


if __name__ == '__main__':
    if create_database():
        email_notification_setup(initial_setup=True)
    main()
