"""
Defines the entry point when installing via pip.
Essentially, this is the launch script.
"""

from podd.cli import cli
from podd.database import Options, create_database


def podd():
    """
    The main routine for CLI interactions
    :return:
    """
    if create_database():
        Options().email_notification_setup(initial_setup=True)
    cli()


if __name__ == '__main__':
    podd()
