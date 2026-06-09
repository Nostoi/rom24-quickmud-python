import pytest

from mud import mobprog
from mud.models.character import Character
from mud.models.constants import Direction, ItemType
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Exit, Room
from mud.registry import room_registry
from mud.world.movement import move_character, move_character_through_portal


@pytest.fixture(autouse=True)
def _cleanup_room_registry():
    yield
    room_registry.pop(5000, None)
    room_registry.pop(5001, None)


def _build_rooms() -> tuple[Room, Room]:
    start = Room(vnum=5000, name="Start")
    target = Room(vnum=5001, name="Target")
    start.exits[Direction.NORTH.value] = Exit(to_room=target, keyword="archway")
    return start, target


def test_npc_entry_trigger_runs_before_greet(monkeypatch) -> None:
    start, target = _build_rooms()

    npc = Character(name="Watcher", is_npc=True, move=20)
    npc.mprog_flags = int(mobprog.Trigger.ENTRY)
    start.add_character(npc)

    calls: list[tuple[str, Character, mobprog.Trigger]] = []

    def fake_percent(
        mob: Character,
        actor: Character | None = None,
        arg1: object | None = None,
        arg2: object | None = None,
        trigger: mobprog.Trigger = mobprog.Trigger.RANDOM,
    ) -> bool:
        calls.append(("percent", mob, trigger))
        return False

    def fake_greet(ch: Character) -> None:
        calls.append(("greet", ch, mobprog.Trigger.GREET))

    monkeypatch.setattr(mobprog, "mp_percent_trigger", fake_percent)
    monkeypatch.setattr(mobprog, "mp_greet_trigger", fake_greet)

    move_character(npc, "north")

    assert npc.room is target
    assert calls == [("percent", npc, mobprog.Trigger.ENTRY)]


def test_npc_without_entry_trigger_flag_does_not_dispatch_entry(monkeypatch) -> None:
    start, target = _build_rooms()

    npc = Character(name="Watcher", is_npc=True, move=20)
    npc.mprog_flags = 0
    start.add_character(npc)

    calls: list[tuple[str, Character, mobprog.Trigger]] = []

    def fake_percent(
        mob: Character,
        actor: Character | None = None,
        arg1: object | None = None,
        arg2: object | None = None,
        trigger: mobprog.Trigger = mobprog.Trigger.RANDOM,
    ) -> bool:
        calls.append(("percent", mob, trigger))
        return False

    monkeypatch.setattr(mobprog, "mp_percent_trigger", fake_percent)

    move_character(npc, "north")

    assert npc.room is target
    assert calls == []


def test_npc_without_entry_trigger_flag_does_not_dispatch_entry_after_portal(monkeypatch) -> None:
    start, target = _build_rooms()
    room_registry[start.vnum] = start
    room_registry[target.vnum] = target

    npc = Character(name="Watcher", is_npc=True, move=20)
    npc.mprog_flags = 0
    start.add_character(npc)

    proto = ObjIndex(vnum=5002, name="portal", short_descr="a small portal", item_type=int(ItemType.PORTAL))
    portal = Object(instance_id=None, prototype=proto)
    portal.value = [0, 0, 0, target.vnum, 0]
    start.add_object(portal)

    calls: list[tuple[str, Character, mobprog.Trigger]] = []

    def fake_percent(
        mob: Character,
        actor: Character | None = None,
        arg1: object | None = None,
        arg2: object | None = None,
        trigger: mobprog.Trigger = mobprog.Trigger.RANDOM,
    ) -> bool:
        calls.append(("percent", mob, trigger))
        return False

    monkeypatch.setattr(mobprog, "mp_percent_trigger", fake_percent)

    move_character_through_portal(npc, portal)

    assert npc.room is target
    assert calls == []
