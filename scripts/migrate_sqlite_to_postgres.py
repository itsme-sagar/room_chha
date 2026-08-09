import os
import sys

# Project root directory
BASE_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

# Add project root to Python path
sys.path.insert(0, BASE_DIR)
from scripts.migration_config import SQLITE_DB, POSTGRES_URI
from scripts.migration_utils import (
    create_session,
    migrate_table
)

from models import (
    User,
    Room,
    Application,
    Message,
    Notification,
    Review,
    Favorite,
    PremiumRequest,
    FeaturedRoomRequest,
    Wallet,
    WalletTransaction,
)

sqlite_uri = f"sqlite:///{SQLITE_DB}"

print("Connecting SQLite...")
sqlite_session = create_session(sqlite_uri)

print("Connecting PostgreSQL...")
postgres_session = create_session(POSTGRES_URI)

print("Both sessions created successfully.")
# ==========================================
# Migrate Tables
# ==========================================

# ==========================================
# Migrate Tables
# ==========================================

migrate_table(sqlite_session, postgres_session, User)
migrate_table(sqlite_session, postgres_session, Room)
migrate_table(sqlite_session, postgres_session, Application)
migrate_table(sqlite_session, postgres_session, Message)
migrate_table(sqlite_session, postgres_session, Notification)
migrate_table(sqlite_session, postgres_session, Review)
migrate_table(sqlite_session, postgres_session, Favorite)
migrate_table(sqlite_session, postgres_session, PremiumRequest)
migrate_table(sqlite_session, postgres_session, FeaturedRoomRequest)
migrate_table(sqlite_session, postgres_session, Wallet)
migrate_table(sqlite_session, postgres_session, WalletTransaction)

print("\n🎉 ALL TABLES MIGRATED SUCCESSFULLY!")