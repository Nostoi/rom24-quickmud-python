from __future__ import annotations

from mud.db.models import Character, PlayerAccount
from mud.db.session import SessionLocal
from mud.security.hash_utils import hash_password


def create_test_account():
    session = SessionLocal()
    if session.query(PlayerAccount).filter_by(username="admin").first():
        session.close()
        return
    account = PlayerAccount(
        username="admin",
        password_hash=hash_password("admin"),
        is_admin=True,
    )
    char = Character(
        name="Testman",
        level=1,
        hp=100,
        room_vnum=3001,
        player=account,
    )
    session.add(account)
    session.add(char)
    session.commit()
    session.close()
