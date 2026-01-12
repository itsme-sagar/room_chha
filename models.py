
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

from datetime import datetime


db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20))
    profile_image = db.Column(db.String(255), default="default.png")


    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    owner = db.relationship(
        "User",
        backref="rooms"
    )

    city = db.Column(db.String(50))
    area = db.Column(db.String(100))
    rent = db.Column(db.Integer)
    room_type = db.Column(db.String(50))
    facilities = db.Column(db.String(255))
    description = db.Column(db.Text)
    approved = db.Column(db.Boolean, default=False)
    images = db.Column(db.Text)  # comma-separated filenames



class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"))
    renter_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    status = db.Column(db.String(20), default="pending")

from datetime import datetime

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer)
    sender_id = db.Column(db.Integer)
    receiver_id = db.Column(db.Integer)
    text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)


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
