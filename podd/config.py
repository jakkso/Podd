import pathlib


class Config:
    """
    Edit the below entries to your desired preferences.
    As an example, I've used a setup that will work with Gmail, as far as host and port go.

    By default, database file will be placed in the same directory as this file.
    Use absolute database locations to prevent pathing issues.
    """
    host = 'smtp.gmail.com'
    port = 587
    database = str(pathlib.Path(__file__).parent.joinpath('podcasts.db'))
    version = '0.1.12'
