from mud.world import initialize_world, create_test_character
from mud.spawning.obj_spawner import spawn_object
from mud.models.character import character_registry
import mud.persistence as persistence


def test_character_json_persistence(tmp_path, inventory_object_factory):
    persistence.PLAYERS_DIR = tmp_path
    character_registry.clear()
    initialize_world('area/area.lst')
    char = create_test_character('Saver', 3001)
    sword = inventory_object_factory(3022)
    helm = inventory_object_factory(3356)
    char.add_object(sword)
    char.equip_object(helm, 'head')

    persistence.save_character(char)

    loaded = persistence.load_character('Saver')
    assert loaded is not None
    assert loaded.room.vnum == 3001
    assert any(obj.prototype.vnum == 3022 for obj in loaded.inventory)
    assert loaded.equipment['head'].prototype.vnum == 3356


def test_save_is_atomic(tmp_path):
    persistence.PLAYERS_DIR = tmp_path
    character_registry.clear()
    initialize_world('area/area.lst')
    char = create_test_character('Atomic', 3001)
    # create corrupt existing file
    (tmp_path / 'atomic.json').write_text('garbage')
    persistence.save_character(char)
    loaded = persistence.load_character('Atomic')
    assert loaded is not None


def test_save_and_load_world(tmp_path):
    persistence.PLAYERS_DIR = tmp_path
    character_registry.clear()
    initialize_world('area/area.lst')
    create_test_character('One', 3001)
    create_test_character('Two', 3001)
    persistence.save_world()
    character_registry.clear()
    loaded = persistence.load_world()
    names = {c.name for c in loaded}
    assert names == {'One', 'Two'}
    assert all(c.room.vnum == 3001 for c in loaded)
