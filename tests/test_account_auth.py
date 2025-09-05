from mud.db.models import Base, PlayerAccount
from mud.db.session import engine, SessionLocal
from mud.account.account_service import (
    create_account,
    login,
    create_character,
    list_characters,
)
from mud.security.hash_utils import verify_password


def setup_module(module):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_account_create_and_login():
    assert create_account("alice", "secret")
    assert not create_account("alice", "other")

    account = login("alice", "secret")
    assert account is not None
    assert login("alice", "bad") is None

    # check hash format
    session = SessionLocal()
    db_acc = session.query(PlayerAccount).filter_by(username="alice").first()
    assert db_acc and db_acc.password_hash.startswith("$2")
    assert verify_password("secret", db_acc.password_hash)
    session.close()

    assert create_character(account, "Hero")
    account = login("alice", "secret")
    chars = list_characters(account)
    assert "Hero" in chars
