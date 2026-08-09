from flask_mail import Message
from flask import current_app

def send_email(
    mail,
    to,
    subject,
    body
):

    msg = Message(
        subject=subject,
        sender=current_app.config["MAIL_DEFAULT_SENDER"],
        recipients=[to]
    )

    msg.html = body

    mail.send(msg)