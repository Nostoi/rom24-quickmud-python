from __future__ import annotations

from pathlib import Path

import pytest

from mud import mob_cmds
from mud.commands.dispatcher import process_command
from mud.models.area import Area
from mud.models.character import Character, character_registry
from mud.models.constants import LEVEL_HERO, ItemType
from mud.models.mob import MobIndex, MobProgram
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Exit, Room
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.skills import handlers as skill_handlers
from mud.skills.registry import load_skills
from mud.mobprog import Trigger
from mud.utils import rng_mm


ROM_NEWLINE = "\n\r"


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
        occupant for occupant in origin.people if occupant is not controller and getattr(occupant, "prototype", None)
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


def test_mpforce_numbered_target_selects_second_match(monkeypatch):
    _, room, _ = _setup_area()

    enforcer = Character(name="Enforcer", is_npc=True)
    room.add_character(enforcer)
    character_registry.append(enforcer)

    first_guard = Character(name="Guard One", is_npc=False)
    second_guard = Character(name="Guard Two", is_npc=False)
    for guard in (first_guard, second_guard):
        room.add_character(guard)
        character_registry.append(guard)

    forced: list[tuple[str, str]] = []

    def fake_process(target: Character, command: str) -> None:
        forced.append((target.name, command))

    monkeypatch.setattr("mud.commands.dispatcher.process_command", fake_process)

    mob_cmds.mob_interpret(enforcer, "force 2.guard say halt")

    assert forced == [("Guard Two", "say halt")]


def test_mpremember_sets_target():
    _, room, _ = _setup_area()

    mob = Character(name="Oracle", is_npc=True)
    room.add_character(mob)
    character_registry.append(mob)

    hero = Character(name="Hero", is_npc=False)
    room.add_character(hero)
    character_registry.append(hero)

    mob_cmds.mob_interpret(mob, "remember Hero")

    assert mob.mprog_target is hero


def test_mpforget_clears_target():
    _, room, _ = _setup_area()

    mob = Character(name="Oracle", is_npc=True)
    room.add_character(mob)
    character_registry.append(mob)

    hero = Character(name="Hero", is_npc=False)
    room.add_character(hero)
    character_registry.append(hero)

    mob_cmds.mob_interpret(mob, "remember Hero")
    assert mob.mprog_target is hero

    mob_cmds.mob_interpret(mob, "forget")

    assert mob.mprog_target is None


def test_mpcast_offensive_spell_hits_target(monkeypatch):
    load_skills(Path("data/skills.json"))
    _, room, _ = _setup_area()

    caster = Character(name="Invoker", is_npc=True, level=45)
    victim = Character(name="Adventurer", is_npc=False, hit=120)

    for char in (caster, victim):
        room.add_character(char)
        character_registry.append(char)

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, target, damage_type: False)
    monkeypatch.setattr(rng_mm, "dice", lambda level, size: 30)

    mob_cmds.mob_interpret(caster, "cast 'acid blast' Adventurer")

    assert victim.hit == 90


def test_mpcast_defensive_defaults_to_self():
    load_skills(Path("data/skills.json"))
    _, room, _ = _setup_area()

    cleric = Character(name="Cleric", is_npc=True, level=30)
    room.add_character(cleric)
    character_registry.append(cleric)

    assert not cleric.has_spell_effect("armor")

    mob_cmds.mob_interpret(cleric, "cast 'armor'")

    assert cleric.has_spell_effect("armor")


def test_mpstat_lists_mob_programs():
    _, room, _ = _setup_area()

    mob_proto = MobIndex(vnum=2100, short_descr="scripted sentinel")
    mob_program = MobProgram(trig_type=int(Trigger.GREET), trig_phrase="hello", vnum=5100)
    mob_proto.mprogs.append(mob_program)
    mob_registry[mob_proto.vnum] = mob_proto

    guardian = Character(name="Guardian", is_npc=True)
    guardian.prototype = mob_proto
    guardian.mprog_delay = 3
    room.add_character(guardian)
    character_registry.append(guardian)

    target = Character(name="Traveler", is_npc=False)
    guardian.mprog_target = target
    room.add_character(target)
    character_registry.append(target)

    immortal = Character(name="Aria", is_npc=False, level=LEVEL_HERO)
    immortal.is_admin = True

    output = process_command(immortal, "mpstat Guardian")

    lines = [line for line in output.split(ROM_NEWLINE) if line]
    assert lines
    assert lines[0].startswith("Mobile #2100")
    assert "[scripted sentinel]" in lines[0]
    assert any("Delay   3" in line and "Traveler" in line for line in lines)
    assert any("Trigger [GREET" in line and "Program [5100]" in line for line in lines)
    assert any("Phrase [hello]" in line for line in lines)


def test_mpdump_returns_program_code():
    _, room, _ = _setup_area()

    mob_proto = MobIndex(vnum=2200, short_descr="scripted sentinel")
    mob_program = MobProgram(
        trig_type=int(Trigger.GREET),
        trig_phrase="hello",
        vnum=5200,
        code="say hello\nmob echo hi",
    )
    mob_proto.mprogs.append(mob_program)
    mob_registry[mob_proto.vnum] = mob_proto

    guardian = Character(name="Guardian", is_npc=True)
    guardian.prototype = mob_proto
    room.add_character(guardian)
    character_registry.append(guardian)

    immortal = Character(name="Aria", is_npc=False, level=LEVEL_HERO)
    immortal.is_admin = True

    output = process_command(immortal, "mpdump 5200")

    assert "say hello" in output
    assert "mob echo hi" in output


def test_mpdump_reports_missing_program():
    immortal = Character(name="Aria", is_npc=False, level=LEVEL_HERO)
    immortal.is_admin = True

    output = process_command(immortal, "mpdump 9999")

    assert output == "No such MOBprogram." + ROM_NEWLINE


def test_mpgforce_forces_room_members(monkeypatch):
    _, room, _ = _setup_area()

    controller = Character(name="Controller", is_npc=True)
    room.add_character(controller)
    character_registry.append(controller)

    leader = Character(name="Leader", is_npc=False)
    follower = Character(name="Ally", is_npc=False)
    outsider = Character(name="Outsider", is_npc=False)

    leader.leader = leader
    follower.leader = leader

    for occupant in (leader, follower, outsider):
        room.add_character(occupant)
        character_registry.append(occupant)

    forced: list[tuple[str, str]] = []

    def fake_process(char: Character, command: str) -> str:
        forced.append((char.name or "", command))
        return ""

    monkeypatch.setattr("mud.commands.dispatcher.process_command", fake_process)

    mob_cmds.mob_interpret(controller, "gforce Leader say rally")

    assert ("Leader", "say rally") in forced
    assert ("Ally", "say rally") in forced
    assert all(entry[0] != "Outsider" for entry in forced)
    assert all(entry[0] != "Controller" for entry in forced)


def test_mpvforce_forces_matching_mobs(monkeypatch):
    _, room, _ = _setup_area()

    controller = Character(name="Controller", is_npc=True)
    room.add_character(controller)
    character_registry.append(controller)

    enforcer_proto = MobIndex(vnum=7100, short_descr="an enforcer")
    mob_registry[enforcer_proto.vnum] = enforcer_proto

    idle_a = Character(name="EnforcerA", is_npc=True)
    idle_a.prototype = enforcer_proto
    idle_b = Character(name="EnforcerB", is_npc=True)
    idle_b.prototype = enforcer_proto
    busy = Character(name="EnforcerBusy", is_npc=True)
    busy.prototype = enforcer_proto
    busy.fighting = controller
    other_proto = MobIndex(vnum=7200, short_descr="a watcher")
    mob_registry[other_proto.vnum] = other_proto
    other = Character(name="Watcher", is_npc=True)
    other.prototype = other_proto

    for occupant in (idle_a, idle_b, busy, other):
        room.add_character(occupant)
        character_registry.append(occupant)

    forced: list[tuple[str, str]] = []

    def fake_process(char: Character, command: str) -> str:
        forced.append((char.name or "", command))
        return ""

    monkeypatch.setattr("mud.commands.dispatcher.process_command", fake_process)

    mob_cmds.mob_interpret(controller, "vforce 7100 say obey")

    assert ("EnforcerA", "say obey") in forced
    assert ("EnforcerB", "say obey") in forced
    assert all(entry[0] != "EnforcerBusy" for entry in forced)
    assert all(entry[0] != "Watcher" for entry in forced)


def test_mpotransfer_moves_room_and_inventory_objects():
    _, origin, destination = _setup_area()

    controller = Character(name="Controller", is_npc=True)
    origin.add_character(controller)
    character_registry.append(controller)

    room_proto = ObjIndex(vnum=7300, short_descr="a silver coin", name="coin")
    room_obj = Object(instance_id=None, prototype=room_proto)
    origin.add_object(room_obj)

    inv_proto = ObjIndex(vnum=7301, short_descr="a bronze charm", name="charm")
    inv_obj = Object(instance_id=None, prototype=inv_proto)
    controller.inventory = [inv_obj]
    controller.carry_number = 1

    mob_cmds.mob_interpret(controller, f"otransfer coin {destination.vnum}")
    assert room_obj in destination.contents
    assert room_obj not in origin.contents

    mob_cmds.mob_interpret(controller, f"otransfer charm {destination.vnum}")
    assert inv_obj in destination.contents
    assert inv_obj not in controller.inventory
    assert controller.carry_number == 0


def test_mpgtransfer_moves_group_members():
    _, origin, destination = _setup_area()

    caller = Character(name="Caller", is_npc=True)
    origin.add_character(caller)
    character_registry.append(caller)

    leader = Character(name="Leader", is_npc=False)
    follower = Character(name="Ally", is_npc=False)
    follower.leader = leader
    outsider = Character(name="Stranger", is_npc=False)

    origin.add_character(leader)
    origin.add_character(follower)
    origin.add_character(outsider)
    character_registry.extend([leader, follower, outsider])

    mob_cmds.mob_interpret(caller, f"gtransfer Leader {destination.vnum}")

    assert leader.room is destination
    assert follower.room is destination
    assert outsider.room is origin


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


def test_mpjunk_removes_equipped_items_and_nested_contents():
    mob = Character(name="Janitor", is_npc=True)
    container_proto = ObjIndex(
        vnum=7400,
        short_descr="a battered bin",
        name="bin",
        item_type=int(ItemType.CONTAINER),
    )
    scrap_proto = ObjIndex(
        vnum=7401,
        short_descr="a scrap",
        name="scrap",
        item_type=int(ItemType.TRASH),
    )
    container = Object(instance_id=None, prototype=container_proto)
    nested = Object(instance_id=None, prototype=scrap_proto)
    container.contained_items.append(nested)

    mob.add_object(container)
    mob.equip_object(container, "hold")

    assert mob.carry_number == 1
    assert mob.equipment.get("hold") is container
    assert container.contained_items == [nested]

    mob_cmds.mob_interpret(mob, "junk bin")

    assert mob.equipment == {}
    assert container not in mob.inventory
    assert mob.carry_number == 0
    assert mob.carry_weight == 0
    assert container.contained_items == []


def test_mpjunk_all_suffix_removes_matching_inventory_objects():
    mob = Character(name="Collector", is_npc=True)
    coin_proto = ObjIndex(vnum=7402, short_descr="a silver coin", name="coin")
    torch_proto = ObjIndex(vnum=7403, short_descr="a travel torch", name="torch")
    coin = Object(instance_id=None, prototype=coin_proto)
    torch = Object(instance_id=None, prototype=torch_proto)

    mob.add_object(coin)
    mob.add_object(torch)

    assert mob.carry_number == 2

    mob_cmds.mob_interpret(mob, "junk all.coin")

    assert coin not in mob.inventory
    assert torch in mob.inventory
    assert mob.carry_number == 1

    mob_cmds.mob_interpret(mob, "junk all")

    assert mob.inventory == []
    assert mob.carry_number == 0


def test_mpjunk_numbered_token_discards_correct_object():
    _, room, _ = _setup_area()

    proto = ObjIndex(vnum=7600, short_descr="a bronze sword", name="sword bronze")
    obj_registry[proto.vnum] = proto

    first = Object(instance_id=1, prototype=proto)
    second = Object(instance_id=2, prototype=proto)

    collector = Character(name="Collector", is_npc=True)
    collector.inventory = [first, second]
    collector.messages = []
    room.add_character(collector)
    character_registry.append(collector)

    mob_cmds.mob_interpret(collector, "junk 2.sword")

    assert first in collector.inventory
    assert second not in collector.inventory


def test_mpat_runs_command_in_target_room(monkeypatch):
    _, origin, destination = _setup_area()

    caster = Character(name="Caster", is_npc=True)
    origin.add_character(caster)
    character_registry.append(caster)

    observed: list[tuple[int | None, str]] = []

    def fake_process(char: Character, command: str) -> str:
        observed.append((getattr(char.room, "vnum", None), command))
        return ""

    monkeypatch.setattr("mud.commands.dispatcher.process_command", fake_process)

    mob_cmds.mob_interpret(caster, f"at {destination.vnum} say Greetings")

    assert observed == [(destination.vnum, "say Greetings")]
    assert caster.room is origin


def test_mppurge_removes_target(monkeypatch):
    _, room, _ = _setup_area()

    controller = Character(name="Controller", is_npc=True)
    room.add_character(controller)
    character_registry.append(controller)

    minion_proto = MobIndex(vnum=7000, short_descr="a minion")
    minion = Character(name="Minion", is_npc=True)
    minion.prototype = minion_proto
    room.add_character(minion)
    character_registry.append(minion)

    hero = Character(name="Hero", is_npc=False)
    room.add_character(hero)
    character_registry.append(hero)

    token_proto = ObjIndex(vnum=7100, short_descr="a dusty token", name="token")
    carried = Object(instance_id=None, prototype=token_proto)
    controller.inventory = [carried]

    dropped_proto = ObjIndex(vnum=7101, short_descr="a broken shard", name="shard")
    dropped = Object(instance_id=None, prototype=dropped_proto)
    room.add_object(dropped)

    mob_cmds.mob_interpret(controller, "purge Minion")

    assert minion not in room.people
    assert hero in room.people
    assert controller in room.people
    assert minion not in character_registry

    mob_cmds.mob_interpret(controller, "purge token")

    assert carried not in getattr(controller, "inventory", [])

    mob_cmds.mob_interpret(controller, "purge shard")

    assert dropped not in room.contents


def test_mppurge_all_cleans_room(monkeypatch):
    _, room, _ = _setup_area()

    controller = Character(name="Controller", is_npc=True)
    room.add_character(controller)
    character_registry.append(controller)

    ally = Character(name="Ally", is_npc=True)
    room.add_character(ally)
    character_registry.append(ally)

    extra = Character(name="Extra", is_npc=True)
    room.add_character(extra)
    character_registry.append(extra)

    hero = Character(name="Hero", is_npc=False)
    room.add_character(hero)
    character_registry.append(hero)

    junk_proto = ObjIndex(vnum=7200, short_descr="a rusted nail", name="nail")
    junk_room = Object(instance_id=None, prototype=junk_proto)
    room.add_object(junk_room)

    junk_inv = Object(instance_id=None, prototype=ObjIndex(vnum=7201, short_descr="a bronze coin", name="coin"))
    controller.inventory = [junk_inv]

    mob_cmds.mob_interpret(controller, "purge all")

    assert controller in room.people
    assert hero in room.people  # players are preserved
    assert ally not in room.people and ally not in character_registry
    assert extra not in room.people and extra not in character_registry
    assert not room.contents
    assert getattr(controller, "inventory", []) == [junk_inv]
