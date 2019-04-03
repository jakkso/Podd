# Podd: a CLI podcatcher

If you're anything like me, you listen to a lot of podcasts.  I like to archive all of my favorites on my home server, where I serve them to all my various devices via Plex.  I looked around for a podcatcher that would manage my podcasts and could be run as a cron job, but I didn't find anything that really met my needs.  So I decided to write my own.

Podd uses [feedparser](https://pypi.org/project/feedparser/) to parse RSS feeds, a sqlite3 database to store subscription info, 
and [mutagen](https://mutagen.readthedocs.io/en/latest/) for basic tagging functionality, plus it sends you an email letting you know which episodes were downloaded, along with a summary of each episode.  

## Installation
#### PYPI
`pip install podd`

#### Github
1. `git clone https://github.com/jakkso/Podd.git`
2. `cd Podd`
3. `pip3 install -r requirements.txt` to install dependencies.
4. Configure `settings.py`
	* 	I use a spare Gmail account to send the notification email messages, if you plan on doing the same, the `host` and `port` values are fine.  Using app-specific passwords like I'm doing here is a bit of a security risk, which is why I recommend not using your main Gmail acc ount.  If you want to go this route,  you'll need to enable [app-specific passwords](https://support.google.com/accounts/answer/185833?hl=en).
	* By default, `database` setting places the sqlite database in the same directory as `settings.py`.  If you want to put it someplace else, just change that line to where you want it to be.

### Requirements
* Python 3.6+ (F-strings are the bomb!)
* Some *nix flavor.  It runs on the latest version of MacOS and Ubuntu with no problems, but I lack a working windows installation to test.  If you want to port it, go nuts.

## Usage

In your terminal of choice, enter `python3 podd.py` followed by one of the following switches:

| Argument | Description |
| --- | --- |
| `--help` | Print help menu |
| `version` | Prints version number |
| `download` | Run download routine |
| `email` | Run email credential storage routine.  Password is stored in OS keyring.|
| `ls` | Print list of subscriptions |
| `add [--all] [--file] $FEED` | Subscribe to podcast with an rss feed url.  If `--all` is  specified, then all available episodes will be downloaded when `download` command is run.  If `--file` is set, `$FEED` will be treated as a file with a single RSS feed URL per line and `podd` will attempt to add each line as a separate RSS feed URL.|
| `remove` | Display the deletion menu |


##### License
GPL v2.0, see LICENSE.txt
