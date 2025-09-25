import os

from mud.db.models import Base
from mud.db.seed import create_test_account
from mud.db.session import engine


def initialize_database():
    """Initialize the database with tables and seed data."""
    # Create all tables
    Base.metadata.create_all(engine)

    # Create test admin account if it doesn't exist
    create_test_account()

    print(f"Database initialized at: {engine.url}")


def database_exists():
    """Check if the database file exists."""
    if str(engine.url).startswith("sqlite:///"):
        db_path = str(engine.url).replace("sqlite:///", "")
        return os.path.exists(db_path)
    return True  # For non-file databases


if __name__ == "__main__":
    initialize_database()
