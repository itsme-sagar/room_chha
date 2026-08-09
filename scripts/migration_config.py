import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

SQLITE_DB = os.path.join(
    BASE_DIR,
    "database",
    "room_chha.db"
)

POSTGRES_URI = os.getenv("DATABASE_URL")