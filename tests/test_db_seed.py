from mud.db.models import Base, Character, PlayerAccount
from mud.db.seed import create_test_account
from mud.db.session import SessionLocal, engine
from mud.security.hash_utils import verify_password


def setup_module(module):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_seed_creates_admin_with_hashed_password():
    create_test_account()
    session = SessionLocal()
    acc = session.query(PlayerAccount).filter_by(username="admin").first()
    assert acc and acc.is_admin
    assert ":" in acc.password_hash
    assert verify_password("admin", acc.password_hash)
    char = session.query(Character).filter_by(name="Testman").first()
    assert char and char.player_id == acc.id
    session.close()

    create_test_account()
    session = SessionLocal()
    assert session.query(PlayerAccount).filter_by(username="admin").count() == 1
    session.close()
