from sqlalchemy import inspect

from mud.db.models import Base
from mud.db.session import engine


def _ensure_true_sex_column(conn) -> None:
    """Add the characters.true_sex column when migrating legacy databases."""

    inspector = inspect(conn)
    try:
        columns = {column["name"] for column in inspector.get_columns("characters")}
    except Exception:
        return

    if "true_sex" in columns:
        return

    conn.exec_driver_sql("ALTER TABLE characters ADD COLUMN true_sex INTEGER DEFAULT 0")
    conn.exec_driver_sql("UPDATE characters SET true_sex = sex")


def _ensure_perm_stat_columns(conn) -> None:
    """Add perm_hit/perm_mana/perm_move columns for ROM parity (src/merc.h PCData structure)."""

    inspector = inspect(conn)
    try:
        columns = {column["name"] for column in inspector.get_columns("characters")}
    except Exception:
        return

    # Add perm_hit column if missing
    if "perm_hit" not in columns:
        conn.exec_driver_sql("ALTER TABLE characters ADD COLUMN perm_hit INTEGER DEFAULT 20")
        conn.exec_driver_sql("UPDATE characters SET perm_hit = hp WHERE perm_hit IS NULL")

    # Add perm_mana column if missing
    if "perm_mana" not in columns:
        conn.exec_driver_sql("ALTER TABLE characters ADD COLUMN perm_mana INTEGER DEFAULT 100")

    # Add perm_move column if missing
    if "perm_move" not in columns:
        conn.exec_driver_sql("ALTER TABLE characters ADD COLUMN perm_move INTEGER DEFAULT 100")


def run_migrations() -> None:
    with engine.begin() as conn:
        Base.metadata.create_all(bind=conn)
        _ensure_true_sex_column(conn)
        _ensure_perm_stat_columns(conn)
    print("✅ Migrations complete.")
