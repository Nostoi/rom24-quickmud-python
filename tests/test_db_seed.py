from mud.db.models import Base, Character
from mud.db.seed import create_test_account
from mud.db.session import SessionLocal, engine
from mud.security.hash_utils import verify_password


def setup_module(module):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_seed_creates_admin_with_hashed_password():
    create_test_account()
    session = SessionLocal()
    char = session.query(Character).filter_by(name="Admin").first()
    assert char is not None
    assert ":" in char.password_hash
    assert verify_password("admin", char.password_hash)
    session.close()

    # idempotent — second call must not create a duplicate
    create_test_account()
    session = SessionLocal()
    assert session.query(Character).filter_by(name="Admin").count() == 1
    session.close()
