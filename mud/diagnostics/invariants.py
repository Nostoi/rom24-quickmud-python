"""Steady-state world-invariant checker.

Walks the live registries and asserts ROM structural invariants that must hold
whenever the world is at rest (i.e. after a ``game_tick``). Enabled only during
the test suite via ``mud.game_loop._INVARIANT_CHECK_ENABLED`` (see the autouse
fixture in ``tests/conftest.py``); the production game loop leaves it off, so
this is a no-op cost there.

Read-only: never mutates game state. Raises ``InvariantViolation`` naming the
broken contract and the offending entities.

v1 invariants:
  - FIGHTING-COHERENCE (INV-005/006): a fighting character's target is in the
    same room and not DEAD/extracted.
  - ROOM-PEOPLE-COHERENCE (INV-010): room.people membership and char.room agree
    in both directions.
"""

from __future__ import annotations

from mud.models.character import character_registry
from mud.models.constants import Position
from mud.registry import room_registry


class InvariantViolation(AssertionError):
    """Raised when a steady-state ROM structural invariant is broken."""


def _ident(char: object) -> str:
    return repr(getattr(char, "name", char))


def _check_fighting_coherence() -> None:
    for char in character_registry:
        target = getattr(char, "fighting", None)
        if target is None:
            continue
        char_room = getattr(char, "room", None)
        target_room = getattr(target, "room", None)
        if char_room is not target_room:
            raise InvariantViolation(
                f"FIGHTING-COHERENCE: {_ident(char)} fighting {_ident(target)} but they are "
                f"in different rooms ({getattr(char_room, 'vnum', None)} vs "
                f"{getattr(target_room, 'vnum', None)})"
            )
        if getattr(target, "position", None) == Position.DEAD:
            raise InvariantViolation(f"FIGHTING-COHERENCE: {_ident(char)} fighting {_ident(target)} which is DEAD")


def _check_room_people_coherence() -> None:
    for vnum, room in room_registry.items():
        for occupant in list(getattr(room, "people", []) or []):
            if getattr(occupant, "room", None) is not room:
                raise InvariantViolation(
                    f"ROOM-PEOPLE-COHERENCE: {_ident(occupant)} is in room {vnum}.people but its "
                    f".room points at {getattr(getattr(occupant, 'room', None), 'vnum', None)}"
                )

    for char in character_registry:
        room = getattr(char, "room", None)
        if room is None:
            continue
        people = getattr(room, "people", []) or []
        if char not in people:
            raise InvariantViolation(
                f"ROOM-PEOPLE-COHERENCE: {_ident(char)}.room is {getattr(room, 'vnum', None)} "
                f"but it is absent from that room's people"
            )


def check_world_invariants() -> None:
    """Assert all v1 steady-state invariants; raise on the first violation."""
    _check_fighting_coherence()
    _check_room_people_coherence()
