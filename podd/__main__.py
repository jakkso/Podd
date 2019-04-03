"""Define the entry point when installing via pip.

Essentially, this is the launch script.
"""

from podd.cli import cli_group
from podd.database import Options, create_database


def podd():
    """Create main routine."""
    if create_database():
        Options().email_notification_setup(initial_setup=True)
    cli_group()


if __name__ == '__main__':
    podd()
