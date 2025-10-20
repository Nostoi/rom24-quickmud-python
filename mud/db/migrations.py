from sqlalchemy import inspect

from mud.db.models import Base
from mud.db.session import engine


def _ensure_true_sex_column(conn) -> None:
    """Add the characters.true_sex column when migrating legacy databases."""

    inspector = inspect(conn)
    try:
        columns = {column["name"] for column in inspector.get_columns("characters")}
    except Exception:
        # If the characters table does not exist yet, create_all() below will
        # build it with the correct schema; nothing to migrate.
        return

    if "true_sex" in columns:
        return

    conn.exec_driver_sql("ALTER TABLE characters ADD COLUMN true_sex INTEGER DEFAULT 0")
    conn.exec_driver_sql("UPDATE characters SET true_sex = sex")


def run_migrations() -> None:
    with engine.begin() as conn:
        Base.metadata.create_all(bind=conn)
        _ensure_true_sex_column(conn)
    print("✅ Migrations complete.")
