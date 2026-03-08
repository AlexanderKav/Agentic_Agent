import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


class EmailService:

    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT"))
        self.email_user = os.getenv("EMAIL_USER")
        self.email_password = os.getenv("EMAIL_PASSWORD")

    def send_email(self, recipient, subject, body):

        msg = MIMEMultipart()
        msg["From"] = self.email_user
        msg["To"] = recipient
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.email_user, self.email_password)
            server.send_message(msg)