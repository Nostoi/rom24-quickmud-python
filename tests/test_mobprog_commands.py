from __future__ import annotations

import pytest

from mud import mob_cmds
from mud.models.area import Area
from mud.models.character import Character, character_registry
from mud.models.mob import MobIndex
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Exit, Room
from mud.registry import area_registry, mob_registry, obj_registry, room_registry


@pytest.fixture(autouse=True)
def clear_registries():
    room_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    area_registry.clear()
    character_registry.clear()
    yield
    room_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    area_registry.clear()
    character_registry.clear()


def _setup_area(vnum: int = 1) -> tuple[Area, Room, Room]:
    area = Area(vnum=vnum, name="Test Area")
    area_registry[vnum] = area
    room_a = Room(vnum=100 + vnum, name="Room A", area=area)
    room_b = Room(vnum=200 + vnum, name="Room B", area=area)
    room_a.exits[0] = Exit(to_room=room_b)  # arbitrary direction linkage
    room_b.exits[2] = Exit(to_room=room_a)
    room_registry[room_a.vnum] = room_a
    room_registry[room_b.vnum] = room_b
    return area, room_a, room_b


def test_mob_broadcast_commands_deliver_expected_messages():
    area, origin, adjacent = _setup_area()
    extra_room = Room(vnum=300, name="Room C", area=area)
    room_registry[extra_room.vnum] = extra_room
    other_area = Area(vnum=99, name="Elsewhere")
    area_registry[other_area.vnum] = other_area
    remote_room = Room(vnum=400, name="Remote", area=other_area)
    room_registry[remote_room.vnum] = remote_room

    mob = Character(name="Guard", is_npc=True)
    origin.add_character(mob)
    character_registry.append(mob)

    scout = Character(name="Scout", is_npc=False)
    adjacent.add_character(scout)
    character_registry.append(scout)

    sentinel = Character(name="Sentinel", is_npc=False)
    extra_room.add_character(sentinel)
    character_registry.append(sentinel)

    bystander = Character(name="Bystander", is_npc=False)
    remote_room.add_character(bystander)
    character_registry.append(bystander)

    victim = Character(name="Hero", is_npc=False)
    observer = Character(name="Watcher", is_npc=False)
    origin.add_character(victim)
    origin.add_character(observer)
    character_registry.extend([victim, observer])

    mob_cmds.mob_interpret(mob, "asound Alarm!")
    assert scout.messages[-1] == "Alarm!"

    mob_cmds.mob_interpret(mob, "zecho Brace yourselves!")
    assert sentinel.messages[-1] == "Brace yourselves!"
    assert victim.messages[-1] == "Brace yourselves!"
    assert not bystander.messages

    mob_cmds.mob_interpret(mob, "echoaround Hero Guard growls at you.")
    assert observer.messages[-1] == "Guard growls at you."
    assert victim.messages[-1] == "Brace yourselves!"

    mob_cmds.mob_interpret(mob, "echoat Hero You shall not pass.")
    assert victim.messages[-1] == "You shall not pass."


def test_spawn_move_and_force_commands_use_rom_semantics(monkeypatch):
    _, origin, target = _setup_area()

    mob_proto = MobIndex(vnum=2000, short_descr="test mob")
    mob_registry[mob_proto.vnum] = mob_proto
    obj_proto_room = ObjIndex(vnum=3001, short_descr="a room token", name="token")
    obj_proto_inv = ObjIndex(vnum=3000, short_descr="an inventory charm", name="charm")
    obj_registry[obj_proto_room.vnum] = obj_proto_room
    obj_registry[obj_proto_inv.vnum] = obj_proto_inv

    controller = Character(name="Controller", is_npc=True)
    origin.add_character(controller)
    character_registry.append(controller)

    mob_cmds.mob_interpret(controller, "mload 2000")
    spawned = [
        occupant
        for occupant in origin.people
        if occupant is not controller and getattr(occupant, "prototype", None)
    ]
    assert spawned and getattr(spawned[0].prototype, "vnum", None) == 2000

    mob_cmds.mob_interpret(controller, "oload 3000")
    assert any(getattr(obj.prototype, "vnum", None) == 3000 for obj in controller.inventory)

    mob_cmds.mob_interpret(controller, "oload 3001 R")
    assert any(getattr(obj.prototype, "vnum", None) == 3001 for obj in origin.contents)

    mob_cmds.mob_interpret(controller, f"goto {target.vnum}")
    assert controller.room is target

    hero = Character(name="Hero", is_npc=False)
    origin.add_character(hero)
    character_registry.append(hero)

    mob_cmds.mob_interpret(controller, "transfer Hero")
    assert hero.room is controller.room

    forced: list[tuple[str, str]] = []

    def fake_process(char: Character, command: str) -> str:
        forced.append((char.name, command))
        return ""

    monkeypatch.setattr("mud.commands.dispatcher.process_command", fake_process)

    mob_cmds.mob_interpret(controller, "force Hero say hello")
    assert forced == [("Hero", "say hello")]


def test_combat_cleanup_commands_handle_inventory_damage_and_escape(monkeypatch):
    _, start, escape = _setup_area()

    obj_proto_a = ObjIndex(vnum=6000, short_descr="a practice token", name="token")
    obj_proto_b = ObjIndex(vnum=6001, short_descr="a bronze sword", name="sword")
    obj_registry[obj_proto_a.vnum] = obj_proto_a
    obj_registry[obj_proto_b.vnum] = obj_proto_b

    mob = Character(name="Enforcer", is_npc=True)
    start.add_character(mob)
    character_registry.append(mob)

    hero = Character(name="Hero", is_npc=False, hit=20, max_hit=20)
    start.add_character(hero)
    character_registry.append(hero)

    calls: list[tuple[Character, Character]] = []

    def fake_multi_hit(attacker: Character, target: Character) -> None:
        calls.append((attacker, target))

    monkeypatch.setattr("mud.combat.multi_hit", fake_multi_hit)

    mob_cmds.mob_interpret(mob, "kill Hero")
    assert calls[-1] == (mob, hero)

    ally = Character(name="Ally", is_npc=True)
    ally.fighting = hero
    start.add_character(ally)
    mob_cmds.mob_interpret(mob, "assist Ally")
    assert calls[-1] == (mob, hero)

    token = Object(instance_id=None, prototype=obj_proto_a)
    sword = Object(instance_id=None, prototype=obj_proto_b)
    mob.inventory = [token, sword]
    mob.equipment = {"wield": sword}

    mob_cmds.mob_interpret(mob, "junk token")
    assert all(getattr(obj.prototype, "vnum", None) != 6000 for obj in mob.inventory)

    mob_cmds.mob_interpret(mob, "junk all")
    assert mob.inventory == []
    assert mob.equipment == {}

    monkeypatch.setattr("mud.mob_cmds.rng_mm.number_range", lambda low, high: high)

    mob_cmds.mob_interpret(mob, "damage Hero 3 5")
    assert hero.hit == 15

    mob_cmds.mob_interpret(mob, "damage Hero 3 5 kill")
    assert hero.hit == 10

    quest_item = Object(instance_id=None, prototype=ObjIndex(vnum=6100, short_descr="a relic"))
    spare_item = Object(instance_id=None, prototype=ObjIndex(vnum=6101, short_descr="a spare"))
    hero.inventory = [quest_item, spare_item]

    mob_cmds.mob_interpret(mob, "remove Hero 6100")
    assert all(getattr(obj.prototype, "vnum", None) != 6100 for obj in hero.inventory)

    mob_cmds.mob_interpret(mob, "remove Hero all")
    assert hero.inventory == []

    mob_cmds.mob_interpret(mob, "flee")
    assert mob.room is escape
