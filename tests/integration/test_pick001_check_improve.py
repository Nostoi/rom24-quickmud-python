"""PICK-001 — do_pick (the live ``pick`` command) calls check_improve.

ROM ``do_pick_lock`` (``src/act_move.c``) calls ``check_improve(ch, gsn_pick_lock,
...)`` on the skill-roll failure branch (line 872, FALSE) and on every successful
unlock branch — portal (908), container (946), door (982), all TRUE. The Python
``mud/commands/doors.py:do_pick`` (registered as ``pick`` in dispatcher.py:332)
carried ``# TODO: Implement check_improve`` stubs and never called it, so the
pick-lock skill never improved and the matching ``number_range(1,1000)`` /
``number_percent()`` RNG draws ROM makes were skipped. Same class as RECALL-002.
"""

from __future__ import annotations

import pytest

from mud import registry as global_registry
from mud.models.character import character_registry
from mud.models.constants import EX_CLOSED, EX_ISDOOR, EX_LOCKED, ContainerFlag, ItemType
from mud.models.room import Exit, Room
from mud.registry import room_registry
from mud.utils import rng_mm
from mud.world import create_test_character


@pytest.fixture(autouse=True)
def _clean_state():
    rooms = set(room_registry)
    char_ids = {id(c) for c in character_registry}
    yield
    for vnum in list(room_registry):
        if vnum not in rooms:
            room_registry.pop(vnum, None)
    character_registry[:] = [c for c in character_registry if id(c) in char_ids]
    for attr in ("players", "char_list", "descriptor_list"):
        if hasattr(global_registry, attr):
            delattr(global_registry, attr)


def _room(vnum: int) -> Room:
    room = Room(vnum=vnum, name=f"Room {vnum}", description="")
    room_registry[vnum] = room
    return room


def _picker(name: str, room_vnum: int, *, skill: int = 100):
    char = create_test_character(name, room_vnum)
    char.level = 20
    char.trust = 20
    char.is_npc = False
    char.skills = {"pick lock": skill}
    char.messages = []
    return char


def _spy_check_improve(monkeypatch):
    import mud.commands.doors as doors

    calls: list[tuple[str, bool, int]] = []
    monkeypatch.setattr(
        doors,
        "check_improve",
        lambda ch, name, success, mult: calls.append((name, success, mult)),
        raising=False,
    )
    return calls


def test_pick_container_success_calls_check_improve_true(monkeypatch):
    """ROM src/act_move.c:946 — check_improve(ch, gsn_pick_lock, TRUE, 2) on container unlock."""
    from mud.commands.doors import do_pick
    from mud.models.obj import ObjIndex
    from mud.models.object import Object

    rng_mm.seed_mm(42)
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 1)  # 1 > 100 is False -> success
    calls = _spy_check_improve(monkeypatch)

    room = _room(50300)
    picker = _picker("Thief", 50300, skill=100)
    proto = ObjIndex(vnum=88900, name="chest", short_descr="a wooden chest")
    chest = Object(instance_id=None, prototype=proto)
    chest.item_type = ItemType.CONTAINER
    chest.value = [0, int(ContainerFlag.CLOSED | ContainerFlag.LOCKED), 1, 0, 0]
    chest.in_room = room
    room.contents = [chest]

    result = do_pick(picker, "chest")

    assert "pick the lock" in result.lower(), result
    assert calls == [("pick lock", True, 2)], f"expected one TRUE check_improve, got {calls}"


def test_pick_skill_failure_calls_check_improve_false(monkeypatch):
    """ROM src/act_move.c:872 — check_improve(ch, gsn_pick_lock, FALSE, 2) on a failed roll."""
    from mud.commands.doors import do_pick
    from mud.models.obj import ObjIndex
    from mud.models.object import Object

    rng_mm.seed_mm(42)
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 100)  # 100 > 1 -> failure branch
    calls = _spy_check_improve(monkeypatch)

    room = _room(50301)
    picker = _picker("Thief", 50301, skill=1)
    proto = ObjIndex(vnum=88901, name="chest", short_descr="a wooden chest")
    chest = Object(instance_id=None, prototype=proto)
    chest.item_type = ItemType.CONTAINER
    chest.value = [0, int(ContainerFlag.CLOSED | ContainerFlag.LOCKED), 1, 0, 0]
    chest.in_room = room
    room.contents = [chest]

    result = do_pick(picker, "chest")

    assert "failed" in result.lower(), result
    assert calls == [("pick lock", False, 2)], f"expected one FALSE check_improve, got {calls}"


def test_pick_door_success_calls_check_improve_true(monkeypatch):
    """ROM src/act_move.c:982 — check_improve(ch, gsn_pick_lock, TRUE, 2) on door unlock."""
    from mud.commands.doors import do_pick

    rng_mm.seed_mm(42)
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 1)
    calls = _spy_check_improve(monkeypatch)

    here = _room(50302)
    there = _room(50303)
    picker = _picker("Thief", 50302, skill=100)
    pexit = Exit(to_room=there, keyword="gate iron", exit_info=EX_ISDOOR | EX_CLOSED | EX_LOCKED, key=88802)
    here.exits = [None, pexit, None, None, None, None]  # EAST

    result = do_pick(picker, "gate")

    assert result == "*Click*", result
    assert calls == [("pick lock", True, 2)], f"expected one TRUE check_improve, got {calls}"
