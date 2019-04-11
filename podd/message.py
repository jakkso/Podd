"""Implement email message functionality."""
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from typing import List, Tuple

from jinja2 import Environment, PackageLoader, select_autoescape

from podd.podcast import Episode
from podd.settings import Config
from podd.utilities import logger


class Message:
    """Render and send emails."""

    __slots__ = [
        "logger", "podcasts", "text", "html", "sender", "password", "recipient"
    ]

    def __init__(
        self,
        podcasts: List[Tuple[str, str, List[Episode]]],
        sender: str,
        password: str,
        recipient: str,
    ):
        """Init method.

        :param podcasts: List of podcast episodes that were successfully downloaded.  Each tuple making up the list
        has three elements: name, image url and a list of Episodes.
        """
        self.sender = sender
        self.password = password
        self.recipient = recipient
        self.logger = logger("message")
        self.podcasts = podcasts
        self.text = self.render_text()
        self.html = self.render_html()

    def __repr__(self):
        """`repr` method."""
        return f"{self.__class__.__name__}({self.podcasts})"

    def render_html(self):
        """Render HTML email.

        Uses self.podcasts to render an html page
        :return: rendered html
        """
        env = Environment(
            loader=PackageLoader("podd", "templates"),
            autoescape=select_autoescape(["html", "xml"]),
        )
        template = env.get_template("base.html")
        return template.render(podcasts=self.podcasts)

    def render_text(self):
        """Render text email.

        Uses self.podcasts to render a text page
        :return: rendered text page
        """
        env = Environment(
            loader=PackageLoader("podd", "templates"),
            autoescape=select_autoescape([".txt"]),
        )
        template = env.get_template("base.txt")
        return template.render(podcasts=self.podcasts)

    def send(self) -> None:
        """Create and send email message.

        Creates an email using the above rendered html and text, logs into
        the email server (I'm using Gmail) and sends said email.
        :return: None
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Podcast Download Report"
        msg["From"] = self.sender
        msg["To"] = self.recipient
        msg.attach(MIMEText(self.text, "plain"))
        msg.attach(MIMEText(self.html, "html"))
        server = smtplib.SMTP(host=Config.host, port=Config.port)
        server.starttls()
        try:
            server.login(user=self.sender, password=self.password)
            server.sendmail(self.sender, self.recipient, msg.as_string())
            server.quit()
        except smtplib.SMTPAuthenticationError:
            msg = "Login failed: Username and/or password not accepted"
            self.logger.exception(msg)
            print(msg)

        self.logger.info(f"Message sent to {self.recipient}")
