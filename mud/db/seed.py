from __future__ import annotations

from mud.db.models import Character
from mud.db.session import SessionLocal
from mud.security.hash_utils import hash_password


def create_test_account():
    """Create a seed admin character for development.

    Mirrors ROM src/save.c — password is stored directly on the Character row
    (PCData.pwd), no separate account table.
    """
    session = SessionLocal()
    if session.query(Character).filter_by(name="Admin").first():
        session.close()
        return
    char = Character(
        name="Admin",
        password_hash=hash_password("admin"),
        level=60,
        hp=1000,
        room_vnum=3001,
    )
    session.add(char)
    session.commit()
    session.close()
