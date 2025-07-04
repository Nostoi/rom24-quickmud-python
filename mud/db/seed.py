from __future__ import annotations

import hashlib

from mud.db.session import SessionLocal
from mud.db.models import PlayerAccount, Character


def create_test_account():
    session = SessionLocal()
    if session.query(PlayerAccount).filter_by(username="admin").first():
        session.close()
        return
    account = PlayerAccount(
        username="admin",
        password_hash=hashlib.sha256(b"admin").hexdigest(),
    )
    char = Character(name="Testman", level=1, hp=100, room_vnum=3001, player=account)
    session.add(account)
    session.add(char)
    session.commit()
    session.close()
