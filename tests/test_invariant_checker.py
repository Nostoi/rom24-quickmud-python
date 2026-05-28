"""Unit tests for the steady-state world-invariant checker.

The checker walks the live registries after every ``game_tick`` during the suite
and raises ``InvariantViolation`` when a steady-state ROM structural contract is
broken. These tests prove each v1 invariant is actually *caught* (a checker that
never fires is worthless) and that a coherent world passes cleanly.
"""

from __future__ import annotations

import pytest

from mud.diagnostics.invariants import InvariantViolation, check_world_invariants
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture
def clean_registries():
    """Snapshot/restore the global registries the checker reads."""
    chars_before = list(character_registry)
    rooms_before = dict(room_registry)
    character_registry.clear()
    room_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(chars_before)
    room_registry.clear()
    room_registry.update(rooms_before)


def _place(char: Character, room: Room) -> None:
    char.room = room
    room.add_character(char)
    character_registry.append(char)


def _make_room(vnum: int) -> Room:
    room = Room(vnum=vnum, name=f"Room {vnum}", description="")
    room_registry[vnum] = room
    return room


def test_coherent_world_passes(clean_registries):
    room = _make_room(3001)
    char = Character(name="Tester", level=5, position=Position.STANDING)
    _place(char, room)

    # No raise.
    check_world_invariants()


def test_fighting_in_different_rooms_raises(clean_registries):
    room_a = _make_room(3001)
    room_b = _make_room(3054)
    attacker = Character(name="Tester", level=5, position=Position.FIGHTING)
    victim = Character(name="goblin", level=3, position=Position.FIGHTING)
    _place(attacker, room_a)
    _place(victim, room_b)
    attacker.fighting = victim

    with pytest.raises(InvariantViolation, match="FIGHTING-COHERENCE"):
        check_world_invariants()


def test_fighting_dead_target_raises(clean_registries):
    room = _make_room(3001)
    attacker = Character(name="Tester", level=5, position=Position.FIGHTING)
    victim = Character(name="goblin", level=3, position=Position.DEAD)
    _place(attacker, room)
    _place(victim, room)
    attacker.fighting = victim

    with pytest.raises(InvariantViolation, match="FIGHTING-COHERENCE"):
        check_world_invariants()


def test_room_people_mismatch_raises(clean_registries):
    room_a = _make_room(3001)
    room_b = _make_room(3054)
    char = Character(name="Tester", level=5, position=Position.STANDING)
    # char appears in room_a.people but its .room points at room_b
    char.room = room_b
    room_b.add_character(char)
    character_registry.append(char)
    room_a.people.append(char)

    with pytest.raises(InvariantViolation, match="ROOM-PEOPLE-COHERENCE"):
        check_world_invariants()


def test_registered_char_absent_from_room_people_raises(clean_registries):
    room = _make_room(3001)
    char = Character(name="Tester", level=5, position=Position.STANDING)
    char.room = room
    character_registry.append(char)
    # deliberately NOT added to room.people

    with pytest.raises(InvariantViolation, match="ROOM-PEOPLE-COHERENCE"):
        check_world_invariants()


def _incoherent_room_people() -> None:
    """Place a char in one room's people while its .room points elsewhere.

    This incoherence survives a full ``game_tick`` (regen/AI don't touch room
    membership of a healthy STANDING PC), so it exercises the post-tick hook.
    """
    room_a = _make_room(3001)
    room_b = _make_room(3054)
    char = Character(name="Tester", level=5, position=Position.STANDING, is_npc=False)
    char.hit = char.max_hit = 100
    char.room = room_b
    room_b.add_character(char)
    character_registry.append(char)
    room_a.people.append(char)


@pytest.mark.check_invariants
def test_game_tick_enforces_invariants_when_opted_in(clean_registries):
    """A test marked check_invariants runs the checker after game_tick."""
    from mud.game_loop import game_tick

    _incoherent_room_people()

    with pytest.raises(InvariantViolation, match="ROOM-PEOPLE-COHERENCE"):
        game_tick()


def test_game_tick_does_not_check_by_default(clean_registries):
    """Without the check_invariants marker the checker is OFF (opt-in)."""
    from mud.game_loop import game_tick

    _incoherent_room_people()

    # No raise: the post-tick checker is disabled unless explicitly opted in.
    game_tick()
