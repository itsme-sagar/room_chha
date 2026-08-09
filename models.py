from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

from datetime import datetime


db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(
    db.String(120),
    unique=True,
    index=True
    )

    role = db.Column(
    db.String(20),
    index=True
    )
    password = db.Column(db.String(200))
    profile_image = db.Column(db.String(255), default="default.png")
    verified_owner = db.Column(
        db.Boolean,
        default=False
    )
    premium_plan = db.Column(
        db.String(20)
    )

    premium_until = db.Column(
        db.DateTime,
        nullable=True
    )
    # Preferred Search Settings

    preferred_city = db.Column(
        db.String(100)
    )

    preferred_room_type = db.Column(
        db.String(100)
    )

    preferred_budget = db.Column(
        db.Integer,
        default=0
    )

    email_notifications = db.Column(
        db.Boolean,
        default=True
    )


    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)
    

# class CityFollow(db.Model):

#     id = db.Column(
#         db.Integer,
#         primary_key=True
#     )

#     user_id = db.Column(
#         db.Integer,
#         db.ForeignKey("user.id")
#     )

#     city = db.Column(
#         db.String(100)
#     )

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    owner_id = db.Column(
    db.Integer,
    db.ForeignKey("user.id"),
    nullable=False,
    index=True
    )

    owner = db.relationship(
        "User",
        backref="rooms"
    )

    city = db.Column(
    db.String(50),
    index=True
    )
    area = db.Column(db.String(100))
    rent = db.Column(db.Integer)
    room_type = db.Column(db.String(50))
    facilities = db.Column(
    db.Text
    )
    description = db.Column(db.Text)
    approved = db.Column(db.Boolean, default=False, index=True)
    images = db.Column(db.Text)  # comma-separated filenames
    featured = db.Column(
        db.Boolean,
        default=False, index=True
    )

    featured_until = db.Column(
        db.DateTime,
        nullable=True
    )

    # Basic Info
    title = db.Column(
        db.String(200)
    )

    deposit_amount = db.Column(
        db.Integer,
        default=0
    )

    available_from = db.Column(
        db.Date
    )

    # Location
    province = db.Column(
        db.String(100)
    )

    district = db.Column(
        db.String(100)
    )

    address = db.Column(
        db.Text
    )

    postal_code = db.Column(
        db.String(20)
    )

    latitude = db.Column(
        db.Float
    )

    longitude = db.Column(
        db.Float
    )

    # Room Details
    room_capacity = db.Column(
        db.Integer,
        default=1
    )

    bathroom_count = db.Column(
        db.Integer,
        default=1
    )

    kitchen_available = db.Column(
        db.Boolean,
        default=False
    )

    parking_available = db.Column(
        db.Boolean,
        default=False
    )

    balcony_available = db.Column(
        db.Boolean,
        default=False
    )

    furnished = db.Column(
        db.Boolean,
        default=False
    )

    floor_number = db.Column(
        db.Integer,
        default=0
    )
    room_size = db.Column(
    db.Integer
    )

    attached_bathroom = db.Column(
        db.Boolean,
        default=False
    )

    facing_direction = db.Column(
        db.String(50)
    )

    building_type = db.Column(
        db.String(50)
    )

    # Preferences
    tenant_preference = db.Column(
        db.String(100)
    )

    gender_preference = db.Column(
        db.String(50)
    )

    smoking_allowed = db.Column(
        db.Boolean,
        default=False
    )

    alcohol_allowed = db.Column(
        db.Boolean,
        default=False
    )

    pets_allowed = db.Column(
        db.Boolean,
        default=False
    )

    # Contact
    owner_phone = db.Column(
        db.String(30)
    )

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), index=True)
    renter_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    status = db.Column(db.String(20), default="pending", index=True)

from datetime import datetime

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, index=True)
    sender_id = db.Column(db.Integer, index=True)
    receiver_id = db.Column(db.Integer, index=True)
    text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    is_read = db.Column(db.Boolean, default=False, index=True)

class Notification(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        index=True
    )

    title = db.Column(db.String(100))

    message = db.Column(db.String(300))

    icon = db.Column(db.String(50))

    color = db.Column(db.String(30))

    link = db.Column(db.String(200))

    is_read = db.Column(
        db.Boolean,
        default=False, index=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow, index=True
    )


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer)
    renter_id = db.Column(db.Integer)
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)

# class RoomImage(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     room_id = db.Column(db.Integer, db.ForeignKey("room.id"))
#     image = db.Column(db.String(200), nullable=False)


class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    renter_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"), index=True
    )

    room_id = db.Column(
        db.Integer,
        db.ForeignKey("room.id"), index=True    
    )

class PremiumRequest(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"), index=True
    )

    request_type = db.Column(
        db.String(50)
    )
    plan = db.Column(
    db.String(20)
    )

    status = db.Column(
        db.String(20),
        default="pending", index=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow, index=True
    )    
class FeaturedRoomRequest(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    room_id = db.Column(
        db.Integer,
        db.ForeignKey("room.id"),
        index=True
    )

    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"), index=True
    )

    status = db.Column(
        db.String(20),
        default="pending", index=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow, index=True
    )
class Wallet(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),index=True,
        unique=True
    )

    balance = db.Column(
        db.Float,
        default=0
    )

class WalletTransaction(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"), index=True
    )

    amount = db.Column(
        db.Float
    )
    transaction_code = db.Column(
    db.String(100)
    )

    screenshot = db.Column(
        db.String(255)
    )

    status = db.Column(
        db.String(20),
        default="pending", index=True
    )

    transaction_type = db.Column(
        db.String(20),
        default="deposit", index=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow, index=True
    )