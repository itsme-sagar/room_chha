import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
os.makedirs(DB_DIR, exist_ok=True)


class Config:

    # Secret Key
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "room_chha_secret"
    )

    # Read DATABASE_URL from .env
    database_url = os.getenv("DATABASE_URL")

    # Render/Neon compatibility
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://",
            "postgresql://",
            1
        )

    # ---------- LOCAL SQLITE DATABASE ----------
    sqlite_path = os.path.abspath(
        os.path.join(DB_DIR, "room_chha.db")
    ).replace("\\", "/")

    SQLITE_DATABASE_URI = f"sqlite:///{sqlite_path}"

    # ---------- PRODUCTION DATABASE ----------
    POSTGRES_DATABASE_URI = os.getenv(
        "POSTGRES_DATABASE_URI"
    )

    # Main database used by Flask
    SQLALCHEMY_DATABASE_URI = (
        database_url
        if database_url
        else SQLITE_DATABASE_URI
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False