from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, PackageLoader, select_autoescape
import smtplib

from miscfunctions import logger
from config import Config


class Message:

    __slots__ = ['podcasts', 'text', 'html']

    def __init__(self, podcasts):
        """
        :param podcasts: a list of named tuples, made up of JinjaPackets, as
        described below, where name, link summary and image are all attributes
        related to that individual podcast.  Episodes are are a list
        of class Episode, as described below.

        JinjaPacket = namedtuple('JinjaPacket', 'name link summary image episodes')
        Episode(title, summary, image, link, filename, date)
        """
        self.podcasts = podcasts
        self.text = self.render_text()
        self.html = self.render_html()

    def __repr__(self):
        return f'{self.__class__.__name__}({self.podcasts})'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger(exc_type, exc_val, exc_tb)

    def render_html(self):
        """
        Uses self.podcasts to render an html page
        :return: rendered html
        """
        env = Environment(
            loader=PackageLoader('classes', 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        template = env.get_template('base.html')
        render = template.render(podcasts=self.podcasts)
        return render

    def render_text(self):
        """
        Uses self.podcasts to render a text page
        :return: rendered text page
        """
        env = Environment(
            loader=PackageLoader('classes', 'templates'),
            autoescape=select_autoescape(['.txt'])
        )
        template = env.get_template('base.txt')
        render = template.render(podcasts=self.podcasts)
        return render

    def send(self):
        """
        Creates an email using the above rendered html and text, logs into
        gmail and sends said email.
        :return: None
        """
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Podcast Download Report'
        msg['From'] = Config.bot
        msg['To'] = Config.recipient
        msg.attach(MIMEText(self.text, 'plain'))
        msg.attach(MIMEText(self.html, 'html'))
        server = smtplib.SMTP(host='smtp.gmail.com', port=587)
        server.starttls()
        server.login(user=Config.bot, password=Config.pw)
        server.sendmail(Config.bot, Config.recipient, msg.as_string())
        server.quit()