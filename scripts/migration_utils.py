from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def create_session(database_uri):
    """
    Create SQLAlchemy session
    """
    engine = create_engine(database_uri)

    Session = sessionmaker(bind=engine)

    return Session()
def migrate_table(sqlite_session, postgres_session, model):
    """
    Generic table migration using SQLAlchemy ORM.
    """

    print(f"\n========== {model.__name__} ==========")

    records = sqlite_session.query(model).all()

    print(f"Found {len(records)} records.")

    for record in records:
        postgres_session.merge(record)

    postgres_session.commit()

    print(f"✅ {model.__name__} migrated successfully.")

