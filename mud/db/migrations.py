from mud.db.models import Base
from mud.db.session import engine


def run_migrations() -> None:
    Base.metadata.create_all(bind=engine)
    print("✅ Migrations complete.")
