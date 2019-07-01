"""Define the entry point when installing via pip.

Essentially, this is the launch script.
"""

from podd.cli import cli_group
from podd.utilities import bootstrap_app


def podd():
    """Create main routine."""
    bootstrap_app()
    cli_group()


if __name__ == "__main__":
    podd()
