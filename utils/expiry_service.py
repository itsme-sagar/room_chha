from datetime import datetime

from models import db, User, Room
from utils.notification_service import notify


def check_premium_expiry():
    """
    Check and remove expired Premium plans.

    Lifetime Premium users are excluded.
    """

    users = User.query.filter_by(
        verified_owner=True
    ).all()

    expired_count = 0

    for user in users:

        if (
            user.premium_plan != "lifetime"
            and user.premium_until
            and user.premium_until < datetime.utcnow()
        ):

            user.verified_owner = False

            user.premium_plan = None

            user.premium_until = None

            notify(
                user.id,
                "Your Premium Plan has expired.",
                "/premium"
            )

            expired_count += 1

    db.session.commit()

    return expired_count


def check_featured_expiry():
    """
    Check and remove expired Featured status from rooms.
    """

    featured_rooms = Room.query.filter_by(
        featured=True
    ).all()

    expired_count = 0

    for room in featured_rooms:

        if (
            room.featured_until
            and room.featured_until < datetime.utcnow()
        ):

            room.featured = False

            room.featured_until = None

            notify(
                room.owner_id,
                f"Featured status expired for room in {room.city}",
                "/owner/rooms"
            )

            expired_count += 1

    db.session.commit()

    return expired_count


def run_expiry_checks():
    """
    Run all Premium and Featured expiry checks.
    """

    premium_expired = check_premium_expiry()

    featured_expired = check_featured_expiry()

    return {
        "premium_expired": premium_expired,
        "featured_expired": featured_expired
    }