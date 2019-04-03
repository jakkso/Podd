"""Implement CLI."""

import click

from podd.settings import Config
from podd.database import Feed, Options
from podd.downloader import downloader


@click.group()
def cli_group():
    """Group cli commands"""
    pass


@click.command()
def download():
    """Download all new episodes."""
    downloader()


@click.command()
@click.option(
    "--catalog",
    is_flag=True,
    default=False,
    help="Download all available episodes, rather than just the newest one.",
)
@click.option(
    "--file",
    is_flag=True,
    default=False,
    help="Specify that the input is a file of RSS feed URLs.",
)
@click.argument("feed")
def add(feed: str, catalog: bool, file: bool):
    """Add podcast subscription using supplied RSS feed URL.

    If the --catalog flag is set, then all available episodes will be downloaded,
    not just the newest episode.  The default behavior causes only the latest
    episode to be downloaded.

    If the --file flag is set, then you can supply a filename as the `feed` argument
    to be able to add multiple podcasts at once.  Simply put each RSS feed URL on its
    own line and Podd will attempt to add each URL.

    """
    if file:
        with open(feed) as file:
            urls = [l.strip() for l in file if l.strip()]
        with Feed() as podcast:
            for url in urls:
                podcast.add(url, newest_only=not catalog)
    else:
        Feed().add(feed, newest_only=not catalog)


@click.command()
def ls():
    """Print current subscriptions."""
    Feed().print_subscriptions()


@click.command()
def email():
    """Setup email notifications."""
    Options().email_notification_setup()


@click.command()
def version():
    """Print version number."""
    click.echo(Config.version)


@click.command()
def remove():
    """Interactive subscription deletion menu."""
    Feed().remove()


cli_group.add_command(download)
cli_group.add_command(add)
cli_group.add_command(ls)
cli_group.add_command(remove)
cli_group.add_command(version)
cli_group.add_command(email)
