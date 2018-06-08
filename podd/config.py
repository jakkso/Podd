from os import path


class Config:
    """
   Edit the below entries to your desired preferences.

    As an example, I've used a setup that will work with gmail, but in order to use
    gmail, you must enable app passwords (See https://support.google.com/mail/answer/185833?hl=en
    for instructions).  Given that this weakens security, I would advise you to make an
    account specifically for this purpose and not your main gmail account.

    Use absolute database locations to prevent pathing issues.
    """
    host = 'smtp.gmail.com'
    port = 587
    sender = 'Replace with gmail address'
    pw = 'Replace with gmail app specific password'
    recipient = 'Replace with recipient email address'
    # Database file will be placed in the same directory as this file.
    database = path.join(path.dirname(path.abspath(__file__)), 'podcasts.db')
