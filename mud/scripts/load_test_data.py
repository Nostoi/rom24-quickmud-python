from mud.db.models import Character, PlayerAccount
from mud.db.session import SessionLocal


def load_test_user():
    db = SessionLocal()

    account = PlayerAccount(username="test", email="test@example.com")
    account.set_password("test123")
    db.add(account)
    db.flush()

    char = Character(name="Tester", hp=100, room_vnum=3001, player_id=account.id)
    db.add(char)
    db.commit()
    print("✅ Test user created: login=test / pw=test123")
