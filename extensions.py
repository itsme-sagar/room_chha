from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_socketio import SocketIO
from authlib.integrations.flask_client import OAuth

db = SQLAlchemy()

mail = Mail()

socketio = SocketIO(
    async_mode="threading"
)

oauth = OAuth()