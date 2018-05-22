"""
Contains email message implementation
"""
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

from jinja2 import Environment, PackageLoader, select_autoescape

from config import Config
from utilities import logger


class Message:
    """
    Email renderer and sender-er
    """

    __slots__ = ['logger', 'podcasts', 'text', 'html']

    def __init__(self, podcasts: list):
        """
        :param podcasts: a list of named tuples, made up of JinjaPackets, as
        described below, where name, link, summary and image are all attributes
        related to that individual podcast.  Episodes are are a list
        of class Episode, as described below.
        JinjaPacket = namedtuple('JinjaPacket', 'name link summary image episodes')
        Episode(title, summary, image, link, filename, date)
        """
        self.logger = logger('Logs/message')
        self.podcasts = podcasts
        self.text = self.render_text()
        self.html = self.render_html()

    def __repr__(self):
        return f'{self.__class__.__name__}({self.podcasts})'

    def render_html(self):
        """
        Uses self.podcasts to render an html page
        :return: rendered html
        """
        env = Environment(
            loader=PackageLoader('message', 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        template = env.get_template('base.html')
        return template.render(podcasts=self.podcasts)

    def render_text(self):
        """
        Uses self.podcasts to render a text page
        :return: rendered text page
        """
        env = Environment(
            loader=PackageLoader('message', 'templates'),
            autoescape=select_autoescape(['.txt'])
        )
        template = env.get_template('base.txt')
        return template.render(podcasts=self.podcasts)

    def send(self) -> None:
        """
        Creates an email using the above rendered html and text, logs into
        gmail and sends said email.
        :return: None
        """
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Podcast Download Report'
        msg['From'] = Config.sender
        msg['To'] = Config.recipient
        msg.attach(MIMEText(self.text, 'plain'))
        msg.attach(MIMEText(self.html, 'html'))
        server = smtplib.SMTP(host=Config.host, port=Config.port)
        server.starttls()
        server.login(user=Config.sender, password=Config.pw)
        server.sendmail(Config.sender, Config.recipient, msg.as_string())
        server.quit()
        self.logger.info(f'Message sent to {Config.recipient}')
