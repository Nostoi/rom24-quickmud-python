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


def _ensure_password_hash_column(conn) -> None:
    """Add characters.password_hash for ROM character-first login (src/save.c PCData.pwd)."""
    inspector = inspect(conn)
    try:
        columns = {column["name"] for column in inspector.get_columns("characters")}
    except Exception:
        return
    if "password_hash" not in columns:
        conn.exec_driver_sql("ALTER TABLE characters ADD COLUMN password_hash VARCHAR DEFAULT ''")


def _ensure_character_schema_columns(conn) -> None:
    """Add DB-canonical character columns required by `load_character()` queries."""

    inspector = inspect(conn)
    try:
        columns = {column["name"] for column in inspector.get_columns("characters")}
    except Exception:
        return

    additions: tuple[tuple[str, str, str | None], ...] = (
        ("max_hit", "INTEGER DEFAULT 20", "UPDATE characters SET max_hit = hp WHERE max_hit IS NULL"),
        ("max_mana", "INTEGER DEFAULT 100", None),
        ("max_move", "INTEGER DEFAULT 100", None),
        ("mana", "INTEGER DEFAULT 100", None),
        ("move", "INTEGER DEFAULT 100", None),
        ("gold", "INTEGER DEFAULT 0", None),
        ("silver", "INTEGER DEFAULT 0", None),
        ("exp", "INTEGER DEFAULT 0", None),
        ("trust", "INTEGER DEFAULT 0", None),
        ("invis_level", "INTEGER DEFAULT 0", None),
        ("incog_level", "INTEGER DEFAULT 0", None),
        ("saving_throw", "INTEGER DEFAULT 0", None),
        ("hitroll", "INTEGER DEFAULT 0", None),
        ("damroll", "INTEGER DEFAULT 0", None),
        ("wimpy", "INTEGER DEFAULT 0", None),
        ("position", "INTEGER DEFAULT 8", None),
        ("played", "INTEGER DEFAULT 0", None),
        ("logon", "INTEGER DEFAULT 0", None),
        ("lines", "INTEGER DEFAULT 22", None),
        ("prompt", "VARCHAR", None),
        ("prefix", "VARCHAR", None),
        ("title", "VARCHAR", None),
        ("bamfin", "VARCHAR", None),
        ("bamfout", "VARCHAR", None),
        ("security", "INTEGER DEFAULT 0", None),
        ("points", "INTEGER DEFAULT 0", "UPDATE characters SET points = creation_points WHERE points IS NULL"),
        ("last_level", "INTEGER DEFAULT 0", None),
        ("affected_by", "INTEGER DEFAULT 0", None),
        ("comm", "INTEGER DEFAULT 0", None),
        ("wiznet", "INTEGER DEFAULT 0", None),
        ("log_commands", "BOOLEAN DEFAULT 0", None),
        ("pfile_version", "INTEGER DEFAULT 1", None),
        ("board", "VARCHAR DEFAULT 'general'", None),
        ("mod_stat", "JSON", None),
        ("armor", "JSON", None),
        ("conditions", "JSON", None),
        ("aliases", "JSON", None),
        ("skills", "JSON", None),
        ("groups", "JSON", None),
        ("last_notes", "JSON", None),
        ("colours", "JSON", None),
        ("pet_state", "JSON", None),
        ("inventory_state", "JSON", None),
        ("equipment_state", "JSON", None),
    )

    for name, ddl, backfill_sql in additions:
        if name in columns:
            continue
        conn.exec_driver_sql(f"ALTER TABLE characters ADD COLUMN {name} {ddl}")
        if backfill_sql is not None:
            conn.exec_driver_sql(backfill_sql)
        columns.add(name)


def run_migrations() -> None:
    with engine.begin() as conn:
        Base.metadata.create_all(bind=conn)
        _ensure_true_sex_column(conn)
        _ensure_perm_stat_columns(conn)
        _ensure_password_hash_column(conn)
        _ensure_character_schema_columns(conn)
    print("✅ Migrations complete.")
