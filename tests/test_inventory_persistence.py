from mud.world import initialize_world, create_test_character
from mud.spawning.obj_spawner import spawn_object
from mud.account.account_manager import save_character, load_character
from mud.db.models import Base, PlayerAccount
from mud.db.session import engine, SessionLocal
from mud.models.character import to_orm


def test_inventory_and_equipment_persistence(tmp_path, inventory_object_factory):
    # use fresh in-memory sqlite database
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    initialize_world('area/area.lst')

    char = create_test_character('Tester', 3001)
    session = SessionLocal()
    account = PlayerAccount(username='tester', password_hash='x')
    session.add(account)
    session.commit()
    db_char = to_orm(char, account.id)
    session.add(db_char)
    session.commit()
    session.close()
    sword = inventory_object_factory(3022)
    helmet = inventory_object_factory(3356)
    char.add_object(sword)
    char.equip_object(helmet, 'head')

    save_character(char)

    loaded = load_character('tester', char.name)
    assert loaded is not None
    assert any(obj.prototype.vnum == 3022 for obj in loaded.inventory)
    assert loaded.equipment['head'].prototype.vnum == 3356
