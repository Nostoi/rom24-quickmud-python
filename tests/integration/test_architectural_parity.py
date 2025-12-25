from __future__ import annotations

from pathlib import Path

import pytest

from mud.commands.dispatcher import process_command
from mud.commands.inventory import do_get
from mud.loaders.help_loader import load_help_file
from mud.loaders.reset_loader import validate_resets
from mud.models.area import Area
from mud.models.character import Character
from mud.models.constants import OHELPS_FILE, Direction, ItemType
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Exit, Room
from mud.models.room_json import ResetJson
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.spawning.reset_handler import apply_resets
from mud.world.movement import can_carry_n, can_carry_w, move_character


@pytest.fixture(autouse=True)
def _clear_registries():
    area_registry.clear()
    room_registry.clear()
    obj_registry.clear()
    mob_registry.clear()
    yield
    area_registry.clear()
    room_registry.clear()
    obj_registry.clear()
    mob_registry.clear()


class TestResetsIntegration:
    def test_p_resets_use_lastobj_container(self):
        area = Area(vnum=9000, name="Integration Area", min_vnum=9000, max_vnum=9010)
        area_registry[area.vnum] = area
        room = Room(vnum=9001, name="Reset Room", area=area)
        room_registry[room.vnum] = room

        container_proto = ObjIndex(
            vnum=9002,
            short_descr="a steel chest",
            item_type=int(ItemType.CONTAINER),
            value=[0, 0, 0, 0, 100],
        )
        gem_proto = ObjIndex(vnum=9003, short_descr="a crimson gem")
        obj_registry[container_proto.vnum] = container_proto
        obj_registry[gem_proto.vnum] = gem_proto

        area.resets = [
            ResetJson(command="O", arg1=container_proto.vnum, arg3=room.vnum),
            ResetJson(command="P", arg1=gem_proto.vnum, arg3=container_proto.vnum, arg4=2),
        ]

        apply_resets(area)
        apply_resets(area)

        containers = [
            obj
            for obj in room.contents
            if getattr(getattr(obj, "prototype", None), "vnum", None) == container_proto.vnum
        ]
        assert len(containers) == 1
        chest = containers[0]
        assert len(chest.contained_items) == 2
        assert all(
            getattr(getattr(item, "prototype", None), "vnum", None) == gem_proto.vnum for item in chest.contained_items
        )


class TestEncumbranceIntegration:
    def test_inventory_limits_block_pickup_and_movement(self):
        area = Area(vnum=9100, name="Encumbrance Area")
        start = Room(vnum=9101, name="Start", area=area)
        dest = Room(vnum=9102, name="Destination", area=area)
        start.exits[Direction.NORTH.value] = Exit(to_room=dest)
        area_registry[area.vnum] = area
        room_registry[start.vnum] = start
        room_registry[dest.vnum] = dest

        heavy_proto = ObjIndex(vnum=9103, short_descr="a heavy stone", weight=5)
        obj_registry[heavy_proto.vnum] = heavy_proto
        heavy_obj = Object(instance_id=None, prototype=heavy_proto)
        start.add_object(heavy_obj)

        carrier = Character(name="Carrier", level=1)
        carrier.room = start
        start.add_character(carrier)
        carrier.carry_weight = can_carry_w(carrier)
        denial = do_get(carrier, "stone")
        assert "can't carry that much weight" in denial
        assert heavy_obj in start.contents

        walker = Character(name="Walker", move=10)
        walker.room = start
        start.add_character(walker)
        walker.gold = 1000
        walker.carry_number = can_carry_n(walker) + 5
        walker.carry_weight = can_carry_w(walker) + 5
        blocked = move_character(walker, "north")
        assert blocked == "You are too encumbered to move."
        assert walker.wait >= 1
        assert walker.room is start

        walker.gold = 0
        walker.carry_number = 0
        walker.carry_weight = 0
        success = move_character(walker, "north")
        assert success == "You walk north to Destination."
        assert walker.room is dest


class TestHelpIntegration:
    def test_dynamic_command_topics_and_trust_filtering(self, monkeypatch, tmp_path):
        help_src = Path(__file__).resolve().parents[2] / "data" / "help.json"
        tmp_help = tmp_path / "help.json"
        tmp_help.write_text(help_src.read_text(encoding="utf-8"), encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        load_help_file(str(tmp_help))

        mortal = Character(name="Newbie", level=1, trust=0, is_npc=False)
        mortal.room = Room(vnum=3001)
        denied = process_command(mortal, "help wizhelp")
        assert denied == "No help on that word.\r\n"

        hero = Character(name="Hero", level=60, is_npc=False)
        hero.room = mortal.room
        immortal_help = process_command(hero, "help wizhelp")
        assert "Syntax: wizhelp" in immortal_help

        fallback = process_command(hero, "help unalias")
        assert fallback.startswith("Command: unalias")
        log_path = Path("log") / OHELPS_FILE
        assert log_path.exists()
        assert "unalias" in log_path.read_text(encoding="utf-8")


class TestAreaLoaderIntegration:
    def test_validate_resets_allows_cross_area_references(self):
        area = Area(vnum=9200, name="Loader Area", min_vnum=9200, max_vnum=9210)
        room = Room(vnum=9201, name="Arena", area=area)
        area_registry[area.vnum] = area
        room_registry[room.vnum] = room

        local_proto = ObjIndex(vnum=9202, short_descr="a shield")
        obj_registry[local_proto.vnum] = local_proto
        area.resets = [
            ResetJson(command="O", arg1=9203, arg3=room.vnum),
            ResetJson(command="O", arg1=local_proto.vnum, arg3=room.vnum),
        ]

        errors = validate_resets(area)
        assert len(errors) == 1
        assert errors[0] == "Reset O references missing object 9203"

        area.resets.append(ResetJson(command="O", arg1=9500, arg3=room.vnum))
        errors = validate_resets(area)
        assert len(errors) == 1
        assert errors[0] == "Reset O references missing object 9203"
