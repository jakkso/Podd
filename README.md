## Podd 
I wanted to write a useful tool; I listen to a lot of podcasts and I needed a CLI podcast downloader program, 
so I took the opportunity and wrote one.  It uses: feedparser for parsing rss feeds; an sqlite3 database to store subscription info; 
mutagen for rudimentary tagging functionality.  It is by no means polished, it's still pretty buggy, but functional.

#####License
GPL v2.0, see LICENSE.txt

## Usagde


`python3 podd.py -a [feedurl]` to add a single feed, or `python3 podd.py -A [file]` to add a line-separated file of feeds.
`python3 podd.py -d` refreshes feeds and downloads new episodes.

Run `python3 podd.py --help` to see all available commands.  Most are scriptable.

## Installation
Clone the repo, run `pip3 install -r requirements.txt`
