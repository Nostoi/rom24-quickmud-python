import mud.persistence as persistence
from mud.models.character import character_registry
from mud.models.constants import WearLocation
from mud.models.obj import Affect
from mud.world import create_test_character, initialize_world


def test_character_json_persistence(tmp_path, inventory_object_factory):
    persistence.PLAYERS_DIR = tmp_path
    character_registry.clear()
    initialize_world("area/area.lst")
    char = create_test_character("Saver", 3001)
    sword = inventory_object_factory(3022)
    helm = inventory_object_factory(3356)
    char.add_object(sword)
    char.equip_object(helm, "head")

    persistence.save_character(char)

    loaded = persistence.load_character("Saver")
    assert loaded is not None
    assert loaded.room.vnum == 3001
    assert any(obj.prototype.vnum == 3022 for obj in loaded.inventory)
    assert loaded.equipment["head"].prototype.vnum == 3356


def test_save_is_atomic(tmp_path):
    persistence.PLAYERS_DIR = tmp_path
    character_registry.clear()
    initialize_world("area/area.lst")
    char = create_test_character("Atomic", 3001)
    # create corrupt existing file
    (tmp_path / "atomic.json").write_text("garbage")
    persistence.save_character(char)
    loaded = persistence.load_character("Atomic")
    assert loaded is not None


def test_save_and_load_world(tmp_path):
    persistence.PLAYERS_DIR = tmp_path
    character_registry.clear()
    initialize_world("area/area.lst")
    create_test_character("One", 3001)
    create_test_character("Two", 3001)
    persistence.save_world()
    character_registry.clear()
    loaded = persistence.load_world()
    names = {c.name for c in loaded}
    assert names == {"One", "Two"}
    assert all(c.room.vnum == 3001 for c in loaded)


def test_inventory_round_trip_preserves_object_state(
    tmp_path,
    inventory_object_factory,
):
    persistence.PLAYERS_DIR = tmp_path
    character_registry.clear()
    initialize_world("area/area.lst")

    char = create_test_character("Saver", 3001)
    container = inventory_object_factory(3010)
    nested = inventory_object_factory(3012)
    weapon = inventory_object_factory(3022)

    container.timer = 12
    container.cost = 777
    container.level = 8
    container.value[0] = 999
    container.affected = [Affect(where=0, type=0, level=5, duration=3, location=2, modifier=4, bitvector=0)]
    container.contained_items.append(nested)

    nested.timer = 2
    nested.value[1] = 55

    weapon.timer = 5
    weapon.cost = 4444
    weapon.value[2] = 13
    weapon.wear_loc = int(WearLocation.WIELD)

    char.add_object(container)
    char.equip_object(weapon, "wield")

    persistence.save_character(char)

    loaded = persistence.load_character("Saver")
    assert loaded is not None

    loaded_container = next(obj for obj in loaded.inventory if obj.prototype.vnum == 3010)
    assert loaded_container.timer == 12
    assert loaded_container.cost == 777
    assert loaded_container.level == 8
    assert loaded_container.value[0] == 999
    assert loaded_container.affected and loaded_container.affected[0].modifier == 4
    assert len(loaded_container.contained_items) == 1
    child = loaded_container.contained_items[0]
    assert child.prototype.vnum == nested.prototype.vnum
    assert child.timer == 2
    assert child.value[1] == 55

    equipped = loaded.equipment["wield"]
    assert equipped.prototype.vnum == weapon.prototype.vnum
    assert equipped.timer == 5
    assert equipped.cost == 4444
    assert equipped.value[2] == 13
    assert int(getattr(equipped, "wear_loc", WearLocation.NONE)) == int(WearLocation.WIELD)


def test_skill_progress_persists(tmp_path):
    persistence.PLAYERS_DIR = tmp_path
    character_registry.clear()
    initialize_world("area/area.lst")

    char = create_test_character("Learner", 3001)
    char.level = 20
    char.skills["fireball"] = 75
    char.skills["backstab"] = 42
    char.pcdata.group_known = ("rom basics",)

    persistence.save_character(char)

    loaded = persistence.load_character("Learner")
    assert loaded is not None
    assert loaded.skills["fireball"] == 75
    assert loaded.skills["backstab"] == 42
    assert loaded.pcdata.learned["fireball"] == 75


def test_group_knowledge_persists(tmp_path):
    persistence.PLAYERS_DIR = tmp_path
    character_registry.clear()
    initialize_world("area/area.lst")

    char = create_test_character("Scholar", 3001)
    char.pcdata.group_known = ("rom basics", "Mage Default", "rom basics")

    persistence.save_character(char)

    loaded = persistence.load_character("Scholar")
    assert loaded is not None
    assert loaded.pcdata.group_known == ("rom basics", "mage default")
