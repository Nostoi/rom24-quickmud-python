from __future__ import annotations

from typing import Optional, List

from mud.db.session import SessionLocal
from mud.db.models import PlayerAccount, Character
from mud.security.hash_utils import hash_password, verify_password
from mud.security import bans


def create_account(username: str, raw_password: str) -> bool:
    """Create a new PlayerAccount if username is available."""
    session = SessionLocal()
    if session.query(PlayerAccount).filter_by(username=username).first():
        session.close()
        return False
    account = PlayerAccount(
        username=username,
        password_hash=hash_password(raw_password),
    )
    session.add(account)
    session.commit()
    session.close()
    return True


def login(username: str, raw_password: str) -> Optional[PlayerAccount]:
    """Return PlayerAccount if credentials match."""
    # Enforce account-name bans irrespective of host.
    if bans.is_account_banned(username):
        return None
    session = SessionLocal()
    account = session.query(PlayerAccount).filter_by(username=username).first()
    if account and verify_password(raw_password, account.password_hash):
        # pre-load characters before detaching
        account.characters  # type: ignore[unused-any]
        session.expunge(account)
        session.close()
        return account
    session.close()
    return None


def login_with_host(
    username: str, raw_password: str, host: str | None
) -> Optional[PlayerAccount]:
    """Login that also enforces site bans.

    This wrapper checks both account and host bans and only then delegates to
    the standard login function.
    """
    if bans.is_host_banned(host):
        return None
    return login(username, raw_password)


def list_characters(account: PlayerAccount) -> List[str]:
    """Return list of character names for this account."""
    return [char.name for char in getattr(account, "characters", [])]


def create_character(
    account: PlayerAccount, name: str, starting_room_vnum: int = 3001
) -> bool:
    """Create a new character for the account."""
    session = SessionLocal()
    if session.query(Character).filter_by(name=name).first():
        session.close()
        return False
    new_char = Character(
        name=name,
        level=1,
        hp=100,
        room_vnum=starting_room_vnum,
        player_id=account.id,
    )
    session.add(new_char)
    session.commit()
    session.close()
    return True
