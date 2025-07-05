from mud.db.session import engine
from mud.db.models import Base


def run_migrations() -> None:
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
    print("\u2705 Migrations complete.")
