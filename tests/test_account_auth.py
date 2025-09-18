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


def test_ban_prefix_suffix_types():
    bans.clear_all_bans()
    bans.add_banned_host("*example.com")
    bans.add_banned_host("corp.*")
    bans.add_banned_host("*evil*")

    assert bans.is_host_banned("malicious.example.com", BanFlag.ALL)
    assert bans.is_host_banned("corp.server", BanFlag.ALL)
    assert bans.is_host_banned("very-evil-site.net", BanFlag.ALL)
    assert not bans.is_host_banned("neutral.org", BanFlag.ALL)
    assert not bans.is_host_banned("angelic.net", BanFlag.ALL)


def test_newbie_permit_enforcement():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()

    bans.add_banned_host("rookie.example", flags=BanFlag.NEWBIES)
    assert bans.is_host_banned("rookie.example", BanFlag.NEWBIES)

    # New account should be rejected by login_with_host
    assert login_with_host("rookie", "pw", "rookie.example") is None

    # Existing account may log in despite BAN_NEWBIES
    assert create_account("rookie", "pw")
    assert login_with_host("rookie", "pw", "rookie.example") is not None


def test_permit_hosts_allowed():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()

    bans.add_banned_host("permit.example", flags=BanFlag.PERMIT)
    assert bans.is_host_banned("permit.example", BanFlag.PERMIT)

    assert create_account("traveler", "pw")
    # Without permit flag the host is rejected
    assert login_with_host("traveler", "pw", "permit.example") is None

    assert create_account("warden", "pw")
    session = SessionLocal()
    account = session.query(PlayerAccount).filter_by(username="warden").first()
    assert account is not None
    account.is_admin = True
    session.commit()
    session.close()

    assert login_with_host("warden", "pw", "permit.example") is not None


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
