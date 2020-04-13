from threading import Thread
from flask import current_app
from flask_mail import Message
from flask_mail import Mail
import os
mail = Mail()

def send_async_email(app, subject, sender, recipients, html_body, attachments):
    with app.app_context():
        msg = Message(subject, sender=sender, recipients=recipients)
        msg.html = html_body
        if attachments:
            for attachment in attachments:
                # msg.attach(*attachment)
                file_name = os.path.basename(attachment)
                with current_app.open_resource(attachment) as fp:
                    msg.attach(file_name, 'application/x-gzip', fp.read())
        mail.send(msg)


def send_email(subject, sender, recipients, html_body,
               attachments=None):
        Thread(target=send_async_email, args=(current_app._get_current_object(), \
            subject, sender, recipients, html_body, attachments)).start()
