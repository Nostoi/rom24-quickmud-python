from mud.db.session import SessionLocal
from mud.db.models import PlayerAccount, Character
from mud.security.hash_utils import hash_password


def load_test_user() -> None:
    db = SessionLocal()

    account = PlayerAccount(
        username="test",
        password_hash=hash_password("test123"),
    )
    db.add(account)
    db.flush()

    char = Character(name="Tester", hp=100, room_vnum=3001, player_id=account.id)
    db.add(char)
    db.commit()
    db.close()
    print("✅ Test user created: login=test / pw=test123")
