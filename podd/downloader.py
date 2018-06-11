"""
Contains update and download functions
"""

from multiprocessing.dummy import Pool as ThreadPool

from podd.database import Database
from podd.message import Message
from podd.podcast import Episode, Podcast


def downloader() -> None:
    """
    Refreshes subscriptions, downloads new episodes, sends email messages.
    :return: None.
    """
    with Database() as _db:
        _, _, send_notifications, _ = _db.get_options()
        sender, password, recipient = _db.get_credentials()
        jinja_packets, eps_to_download = threaded_update(_db.get_podcasts())
    if jinja_packets and eps_to_download:
        threaded_downloader(eps_to_download)
        if send_notifications:
            Message(jinja_packets, sender, password, recipient).send()
    else:
        print('No new episodes')


def threaded_update(subscriptions: list) -> tuple:
    """
    Creates a ThreadPool to get new episodes to download from rss feed.
    :param subscriptions: list of tuples of names, rss feed urls and download
    directories of individual podcasts
    :return: 2-tuple of lists of jinja_packets and a list of episodes to download.
    """

    def update_worker(subscription: tuple) -> tuple or None:
        """
        Function used by ThreadPool to update RSS feed.
        :param subscription: tuple of name, rss feed url and download directory
        :return:
        """
        name, url, dl_dir = subscription
        print(f'Updating {name}')
        with Podcast(url, dl_dir) as pod:
            j_packet = pod.episodes()
            if j_packet:
                return j_packet, j_packet.episodes
        return False

    jinja_packets, to_dl = [], []
    pool = ThreadPool(3)
    results = pool.map(update_worker, subscriptions)
    pool.close()
    pool.join()
    for item in results:
        if item:
            jinja_packets.append(item[0])
            to_dl.extend(item[1])
    return jinja_packets, to_dl


def threaded_downloader(eps_to_download: list) -> None:
    """
    Creates thread-pool to download episodes, then adds said episodes to the database
    :param eps_to_download: list of Episodes to be downloaded
    :return: None
    """
    def download_worker(episode: Episode) -> Episode:
        """
        Function used by ThreadPool.map to download each episode.
        :param: episode Episode obj
        :return: None
        """
        print(f'Downloading {episode.podcast_name} - {episode.title}')
        episode.download()
        episode.tag()
        return episode

    if eps_to_download:
        pool = ThreadPool(3)
        results = pool.map(download_worker, eps_to_download)
        pool.close()
        pool.join()
        with Database() as _db:
            for epi in results:
                _db.add_episode(podcast_url=epi.podcast_url,
                                feed_id=epi.entry.id)
