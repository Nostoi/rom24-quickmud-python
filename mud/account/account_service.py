from collections.abc import Iterable
from enum import Enum
from typing import NamedTuple

from mud.db.models import Character, PlayerAccount
from mud.db.session import SessionLocal
from mud.security import bans
from mud.security.bans import BanFlag
from mud.security.hash_utils import hash_password, verify_password
from mud.world.world_state import (
    is_newlock_enabled,
    is_wizlock_enabled,
)


class LoginFailureReason(Enum):
    """Reasons an account login can be rejected."""

    ACCOUNT_BANNED = "account_banned"
    HOST_BANNED = "host_banned"
    HOST_NEWBIES = "host_newbies"
    DUPLICATE_SESSION = "duplicate_session"
    WIZLOCK = "wizlock"
    NEWLOCK = "newlock"
    BAD_CREDENTIALS = "bad_credentials"
    UNKNOWN_ACCOUNT = "unknown_account"


class LoginResult(NamedTuple):
    """Outcome of a login attempt."""

    account: PlayerAccount | None
    failure: LoginFailureReason | None


_active_accounts: set[str] = set()


def _normalize(username: str) -> str:
    return username.strip().lower()


def _mark_account_active(username: str) -> None:
    _active_accounts.add(_normalize(username))


def release_account(username: str) -> None:
    """Clear the active-session marker for this account."""

    _active_accounts.discard(_normalize(username))


def clear_active_accounts() -> None:
    """Reset all active-session markers (test helper)."""

    _active_accounts.clear()


def active_accounts() -> Iterable[str]:
    """Return a snapshot of active account usernames (lowercased)."""

    return tuple(_active_accounts)


def _is_account_active(username: str) -> bool:
    return _normalize(username) in _active_accounts


def is_account_active(username: str) -> bool:
    """Return True when the account currently has an active session."""

    return _is_account_active(username)


def create_account(username: str, raw_password: str) -> bool:
    """Create a new PlayerAccount if username is available."""
    if is_newlock_enabled():
        return False
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


def login(username: str, raw_password: str) -> PlayerAccount | None:
    """Return PlayerAccount if credentials match."""
    # Enforce account-name bans irrespective of host.
    if bans.is_account_banned(username):
        return None
    session = SessionLocal()
    account = session.query(PlayerAccount).filter_by(username=username).first()
    if account and verify_password(raw_password, account.password_hash):
        # pre-load characters before detaching
        _ = account.characters  # type: ignore[unused-any]
        session.expunge(account)
        session.close()
        return account
    session.close()
    return None


def login_with_host(
    username: str,
    raw_password: str,
    host: str | None,
    *,
    allow_reconnect: bool = False,
) -> LoginResult:
    """Login that also enforces site bans.

    Returns a :class:`LoginResult` detailing the authenticated account (if
    successful) or the reason the attempt failed so callers can mirror ROM's
    nanny prompts.
    """

    if bans.is_account_banned(username):
        return LoginResult(None, LoginFailureReason.ACCOUNT_BANNED)

    was_active = _is_account_active(username)
    if was_active and not allow_reconnect:
        return LoginResult(None, LoginFailureReason.DUPLICATE_SESSION)

    permit_host = bool(host and bans.is_host_banned(host, BanFlag.PERMIT))
    if host and not permit_host and bans.is_host_banned(host, BanFlag.ALL):
        return LoginResult(None, LoginFailureReason.HOST_BANNED)

    session = SessionLocal()
    account_record: PlayerAccount | None = None
    exists = False
    is_admin = False
    password_valid = False
    try:
        account_record = session.query(PlayerAccount).filter_by(username=username).first()
        if account_record:
            exists = True
            is_admin = bool(getattr(account_record, "is_admin", False))
            password_valid = verify_password(raw_password, account_record.password_hash)
            if password_valid:
                # Preload related characters before detaching.
                _ = account_record.characters  # type: ignore[unused-any]
                session.expunge(account_record)
    finally:
        session.close()

    if host and not permit_host and not exists and bans.is_host_banned(host, BanFlag.NEWBIES):
        return LoginResult(None, LoginFailureReason.HOST_NEWBIES)
    if is_newlock_enabled() and not exists:
        return LoginResult(None, LoginFailureReason.NEWLOCK)
    if is_wizlock_enabled() and not is_admin and not (allow_reconnect and was_active):
        return LoginResult(None, LoginFailureReason.WIZLOCK)

    account: PlayerAccount | None = None
    if password_valid and account_record is not None:
        account = account_record

    if not account and not exists and create_account(username, raw_password):
        # Re-run login to detach the newly created account instance with characters loaded.
        account = login(username, raw_password)
        exists = account is not None

    if account:
        if was_active:
            release_account(username)
        _mark_account_active(username)
        return LoginResult(account, None)

    failure = (
        LoginFailureReason.BAD_CREDENTIALS if exists else LoginFailureReason.UNKNOWN_ACCOUNT
    )
    return LoginResult(None, failure)


def list_characters(account: PlayerAccount) -> list[str]:
    """Return list of character names for this account."""
    return [char.name for char in getattr(account, "characters", [])]


def create_character(account: PlayerAccount, name: str, starting_room_vnum: int = 3001) -> bool:
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
