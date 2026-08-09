from models import db, Notification


def notify(
    user_id,
    message,
    link="/"
):
    """
    Create an in-app notification.
    """

    notification = Notification(
        user_id=user_id,
        message=message,
        link=link,
        is_read=False
    )

    db.session.add(notification)