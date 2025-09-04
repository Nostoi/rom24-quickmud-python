from mud.world import initialize_world, create_test_character
from mud.spawning.obj_spawner import spawn_object
import mud.persistence as persistence


def test_character_json_persistence(tmp_path):
    persistence.PLAYERS_DIR = tmp_path
    initialize_world('area/area.lst')
    char = create_test_character('Saver', 3001)
    sword = spawn_object(3022)
    helm = spawn_object(3356)
    assert sword and helm
    char.add_object(sword)
    char.equip_object(helm, 'head')

    persistence.save_character(char)

    loaded = persistence.load_character('Saver')
    assert loaded is not None
    assert loaded.room.vnum == 3001
    assert any(obj.prototype.vnum == 3022 for obj in loaded.inventory)
    assert loaded.equipment['head'].prototype.vnum == 3356
