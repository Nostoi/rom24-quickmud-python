import mud.persistence as persistence
from mud.account.account_manager import load_character, save_character
from mud.db.models import Base
from mud.db.session import engine
from mud.world import create_test_character, initialize_world


def test_inventory_and_equipment_persistence(tmp_path, inventory_object_factory):
    # Redirect pfile writes to a throwaway directory (INV-008 hybrid: JSON is primary)
    persistence.PLAYERS_DIR = tmp_path / "players"

    # use fresh in-memory sqlite database
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    initialize_world("area/area.lst")

    char = create_test_character("Tester", 3001)
    # Save the character directly — no account record needed (ROM character-first login)
    save_character(char)

    sword = inventory_object_factory(3022)
    helmet = inventory_object_factory(3356)
    char.add_object(sword)
    char.equip_object(helmet, "head")

    save_character(char)

    loaded = load_character(char.name)
    assert loaded is not None
    assert any(obj.prototype.vnum == 3022 for obj in loaded.inventory)
    assert loaded.equipment["head"].prototype.vnum == 3356
