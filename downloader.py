from multiprocessing.dummy import Pool as ThreadPool

from database import Database
from message import Message
from podcast import Episode, Podcast


def downloader() -> None:
    """
    refreshes subscriptions, downloads new episodes, sends email messages
    :return:
    """
    with Database() as _db:
        jinja_packets, eps_to_download = threaded_update(_db.get_podcasts())
    if jinja_packets and eps_to_download:
        threaded_downloader(eps_to_download)
        Message(jinja_packets).send()
    else:
        print('No new episodes')


def threaded_update(subscriptions: list) -> tuple:
    """
    Creates a threadpool to get new episodes to download from rss feed.
    :param subscriptions: list of tuples of names, rss feed urls and download
    directories of individual podcasts
    :return: 2-tuple of lists
    """

    def update_worker(subscription: tuple) -> tuple or None:
        """

        :param subscription: tuple of name, rss feed url and download directory
        :return:
        """
        _, url, dl_dir = subscription
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
        if item:  # Filters out False returns from update_worker
            jinja_packets.append(item[0])
            to_dl.extend(item[1])
    return jinja_packets, to_dl


def threaded_downloader(eps_to_download: list):
    """
    :param eps_to_download: list of Episodes to be downloaded
    :return: None
    """
    def download_worker(episode: Episode) -> Episode:
        """
        :param: episode Episode obj
        :return: None
        """
        print(f'Downloading {episode.title}')
        episode.download()
        episode.tag()
        return episode

    def add_episode_to_db(episode: Episode) -> None:
        """
        Adds episode ID to database.  Because of SQLite can only have a single writer,
        after the downloads complete, all new episode IDs are added by a map function
        :param episode:
        :return:
        """
        with Database() as _db:
            _db.add_episode(podcast_url=episode.podcast_url,
                            feed_id=episode.entry.id)

    if eps_to_download:
        pool = ThreadPool(3)
        results = pool.map(download_worker, eps_to_download)
        pool.close()
        pool.join()
        map(add_episode_to_db, results)

