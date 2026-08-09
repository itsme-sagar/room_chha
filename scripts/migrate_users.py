import os
import sqlite3
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# -------------------------
# SQLite
# -------------------------

sqlite_db = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "database",
        "room_chha.db"
    )
)

sqlite_conn = sqlite3.connect(sqlite_db)
sqlite_cur = sqlite_conn.cursor()

print("✅ SQLite Connected")

# -------------------------
# PostgreSQL
# -------------------------

postgres_conn = psycopg2.connect(
    os.getenv("POSTGRES_DATABASE_URI")
)

postgres_cur = postgres_conn.cursor()

print("✅ PostgreSQL Connected")

# -------------------------
# Read Users
# -------------------------

sqlite_cur.execute("SELECT * FROM user")

users = sqlite_cur.fetchall()

print(f"\nFound {len(users)} users.\n")

for user in users:
    print(user)

sqlite_conn.close()
postgres_conn.close()