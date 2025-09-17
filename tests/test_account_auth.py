from pathlib import Path

from mud.db.models import Base, PlayerAccount
from mud.db.session import engine, SessionLocal
from mud.account.account_service import (
    create_account,
    login,
    create_character,
    list_characters,
)
from mud.security.hash_utils import verify_password
from mud.security import bans
from mud.security.bans import BanFlag
from mud.account.account_service import login_with_host


def setup_module(module):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()


def test_account_create_and_login():
    assert create_account("alice", "secret")
    assert not create_account("alice", "other")

    account = login("alice", "secret")
    assert account is not None
    assert login("alice", "bad") is None

    # check hash format
    session = SessionLocal()
    db_acc = session.query(PlayerAccount).filter_by(username="alice").first()
    assert db_acc and ":" in db_acc.password_hash
    assert verify_password("secret", db_acc.password_hash)
    session.close()

    assert create_character(account, "Hero")
    account = login("alice", "secret")
    chars = list_characters(account)
    assert "Hero" in chars


def test_banned_account_cannot_login():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()

    assert create_account("bob", "pw")
    bans.add_banned_account("bob")
    # Direct login should be refused for banned account
    assert login("bob", "pw") is None


def test_banned_host_cannot_login():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()

    assert create_account("carol", "pw")
    bans.add_banned_host("203.0.113.9")
    # Host-aware login wrapper should reject banned host
    assert login_with_host("carol", "pw", "203.0.113.9") is None
    # Non-banned host should allow login
    assert login_with_host("carol", "pw", "198.51.100.20") is not None


def test_ban_persistence_roundtrip(tmp_path):
    # Arrange
    bans.clear_all_bans()
    bans.add_banned_host("bad.example")
    bans.add_banned_host("203.0.113.9")
    path = tmp_path / "ban.txt"

    # Act: save → clear → load
    bans.save_bans_file(path)
    text = path.read_text()
    assert "bad.example" in text and "203.0.113.9" in text
    bans.clear_all_bans()
    loaded = bans.load_bans_file(path)

    # Assert
    assert loaded == 2
    assert bans.is_host_banned("bad.example")
    assert bans.is_host_banned("203.0.113.9")


def test_ban_persistence_includes_flags(tmp_path):
    bans.clear_all_bans()
    bans.add_banned_host("*wildcard*")
    bans.add_banned_host("allow.me", flags=BanFlag.PERMIT, level=50)
    bans.add_banned_host("*example.com", flags=BanFlag.NEWBIES, level=60)
    path = tmp_path / "ban.lst"

    bans.save_bans_file(path)

    expected = Path("tests/data/ban_sample.golden.txt").read_text()
    assert path.read_text() == expected


def test_ban_file_round_trip_levels(tmp_path):
    bans.clear_all_bans()
    bans.add_banned_host("*wildcard*")
    bans.add_banned_host("allow.me", flags=BanFlag.PERMIT, level=50)
    bans.add_banned_host("*example.com", flags=BanFlag.NEWBIES, level=60)
    path = tmp_path / "ban.lst"
    bans.save_bans_file(path)

    bans.clear_all_bans()
    loaded = bans.load_bans_file(path)

    assert loaded == 3
    entries = {entry.pattern: entry for entry in bans.get_ban_entries()}
    assert "wildcard" in entries and entries["wildcard"].level == 0
    assert entries["wildcard"].flags & BanFlag.SUFFIX
    assert entries["wildcard"].flags & BanFlag.PREFIX
    assert "allow.me" in entries and entries["allow.me"].level == 50
    assert entries["allow.me"].flags & BanFlag.PERMIT
    assert "example.com" in entries and entries["example.com"].level == 60
    assert entries["example.com"].flags & BanFlag.NEWBIES
    assert entries["example.com"].flags & BanFlag.PREFIX


def test_ban_file_round_trip_preserves_order(tmp_path):
    bans.clear_all_bans()
    bans.add_banned_host("first.example")
    bans.add_banned_host("second.example")
    path = tmp_path / "ban.lst"

    bans.save_bans_file(path)
    original = path.read_text()

    bans.clear_all_bans()
    bans.load_bans_file(path)
    bans.save_bans_file(path)

    assert path.read_text() == original
    assert [entry.pattern for entry in bans.get_ban_entries()] == [
        "first.example",
        "second.example",
    ]


def test_remove_banned_host_ignores_wildcard_markers():
    bans.clear_all_bans()
    bans.add_banned_host("*example.com")
    assert bans.is_host_banned("foo.example.com")
    bans.remove_banned_host("example.com")
    assert not bans.is_host_banned("foo.example.com")


def test_ban_prefix_suffix_types():
    bans.clear_all_bans()
    bans.add_banned_host("*example.com")
    assert bans.is_host_banned("foo.example.com")
    assert not bans.is_host_banned("example.org")

    bans.clear_all_bans()
    bans.add_banned_host("example.*")
    assert bans.is_host_banned("example.net")
    assert not bans.is_host_banned("demoexample.net")

    bans.clear_all_bans()
    bans.add_banned_host("*malicious*")
    assert bans.is_host_banned("verymalicioushost.net")
    assert not bans.is_host_banned("innocent.net")


def test_newbie_permit_enforcement():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()

    assert create_account("elder", "pw")

    bans.add_banned_host("blocked.example", flags=BanFlag.NEWBIES)
    assert login_with_host("elder", "pw", "blocked.example") is not None
    assert login_with_host("fresh", "pw", "blocked.example") is None
    session = SessionLocal()
    try:
        assert (
            session.query(PlayerAccount).filter_by(username="fresh").first()
            is None
        )
    finally:
        session.close()

    bans.clear_all_bans()
    bans.add_banned_host("locked.example", flags=BanFlag.ALL)
    assert login_with_host("elder", "pw", "locked.example") is None

    bans.add_banned_host("locked.example", flags=BanFlag.PERMIT)
    assert login_with_host("elder", "pw", "locked.example") is not None
