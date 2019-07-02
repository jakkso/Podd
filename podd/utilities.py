"""Contain utility functions."""

import pathlib
import re
import typing as tp

from podd.database import Options
from podd.settings import Config


def bootstrap_app(database: str = Config.database) -> None:
    """Create database file, ask user for download and log directories, create said directories.
    :type database: str
    :param database: location of database file.  By default, it's in the same
    directory as `podd.settings`
    """

    # Look for database file
    for file in pathlib.Path(database).parent.iterdir():
        # If database file is found, return early
        if database == str(file):
            return
    # Otherwise, bootstrap application:

    # Define database structure
    with Options(database) as _db:
        cur = _db.cursor
        cur.execute(
            "CREATE TABLE IF NOT EXISTS podcasts "
            "(id INTEGER PRIMARY KEY, "
            "name TEXT, "
            "url TEXT UNIQUE, "
            "directory TEXT)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS episodes "
            "(id INTEGER PRIMARY KEY, "
            "feed_id TEXT, "
            "podcast_id INTEGER NOT NULL,"
            "FOREIGN KEY (podcast_id) REFERENCES podcasts(id))"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS settings "
            "(id INTEGER PRIMARY KEY, "
            "download_directory TEXT,"
            "notification_status BOOLEAN,"
            "sender_address TEXT,"
            "recipient_address TEXT)"
        )
        # Ensure that log_dir exists
        Config.log_directory.mkdir(exist_ok=True, parents=True)
        # Get user input for where to put download directory, add to db
        dl_dir = get_directory(
            name="Download directory", default=pathlib.Path.home() / "Podcasts"
        )
        cur.execute(
            "INSERT INTO settings (download_directory, notification_status) VALUES (?,?)",
            (str(dl_dir), False),
        )
        # Do email notification setup.
        _db.email_notification_setup(initial_setup=True)


def get_directory(name: str, default: pathlib.Path) -> pathlib.Path:
    """Prompt user for directory, create and then return path."""
    while True:
        prompt = f"{name} (Leave blank for {default}): "
        raw_input = input(prompt)
        if not raw_input:
            path = default
        elif raw_input[0] == "~":
            path = pathlib.Path("~").expanduser()
            try:
                if raw_input[1] == "/":
                    path /= raw_input[2:]
            except IndexError:
                pass  # Catch case where user enters just `~` or `~/`
        else:
            path = pathlib.Path(raw_input)
        try:
            path.mkdir(exist_ok=True, parents=True)
            return path
        except (IOError, PermissionError, OSError) as err:
            print(f"Invalid directory: {err}")


def compile_regex() -> tp.List[re.compile]:
    """Return compiled regex patterns.

    These patterns are used to try to match episode numbers in order to tag
    episodes.
    """
    return [
        re.compile(r"EPISODE #?(\d+)", re.IGNORECASE),
        re.compile(r"#?(\d+)", re.IGNORECASE),
        re.compile(r"^Show (\d+)", re.IGNORECASE),
        re.compile(r'Ep\.? (\d+)', re.IGNORECASE),
    ]


def get_episode_number(title: str) -> str or None:
    """Attempt to parse episode number out of a title.

    This is functionally identical
    """
    for pattern in compile_regex():
        match = pattern.search(title)
        if match:
            return match.groups()[0]
