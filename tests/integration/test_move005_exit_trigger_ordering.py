"""MOVE-005 — TRIG_EXIT fires before the exit-existence / encumbrance gates.

ROM ``src/act_move.c:move_char`` fires ``mp_exit_trigger(ch, door)`` as the
**first** action after the door-bounds check — before the exit-existence /
``can_see_room`` check (``Alas, you cannot go that way.``) and before the
movement-cost gate.  The exit trigger keys on the *attempted direction* alone
(``dir == atoi(prg->trig_phrase)``); it never consults whether an exit exists
in that direction or whether the mover can pay the move cost.

The per-file audit (ACT_MOVE_C_AUDIT.md) marked this ✅ PARITY by verifying the
trigger is *called* — but Python invoked it AFTER an ``exit is None`` early
return and AFTER the (non-ROM) encumbrance gate, so a PC walking into a wall
never fired the mob's exit program.  These tests pin the ordering.
"""

from __future__ import annotations

from mud import mobprog
from mud.models.character import Character
from mud.models.room import Room
from mud.world.movement import move_character


def _spy_exit_trigger(monkeypatch) -> list[int]:
    """Replace mp_exit_trigger with a spy that records the attempted dir.

    Returns True (trigger fired → ROM bails out of move_char) so we can also
    assert the move is aborted by the trigger rather than by a later gate.
    """

    seen: list[int] = []

    def fake_exit_trigger(_ch: Character, direction: int) -> bool:
        seen.append(int(getattr(direction, "value", direction)))
        return True

    monkeypatch.setattr(mobprog, "mp_exit_trigger", fake_exit_trigger)
    return seen


def test_exit_trigger_fires_when_no_exit_exists(monkeypatch) -> None:
    """A PC walking into a wall still fires the room's exit trigger (ROM order)."""

    room = Room(vnum=6000, name="Walled Room")  # no exits in any direction
    pc = Character(name="Wanderer", is_npc=False, move=100)
    room.add_character(pc)

    seen = _spy_exit_trigger(monkeypatch)

    result = move_character(pc, "north")

    # ROM fires the exit trigger before the exit-existence check, so the spy
    # must have been reached for the (non-existent) north exit (dir 0).
    assert seen == [0], "mp_exit_trigger must fire before the exit-existence gate"
    # The trigger returning True aborts the move (ROM `return;`), so the PC
    # stays put and the command yields no "cannot go that way" message.
    assert result == ""
    assert pc.room is room


def test_exit_trigger_fires_when_encumbered(monkeypatch) -> None:
    """An over-encumbered PC still fires the exit trigger (ROM has no carry gate)."""

    room = Room(vnum=6001, name="Heavy Room")
    pc = Character(name="Packmule", is_npc=False, move=100)
    room.add_character(pc)

    # Force the encumbrance early-return path: pretend the PC is over weight.
    monkeypatch.setattr("mud.world.movement.get_carry_weight", lambda ch: 10**9)

    seen = _spy_exit_trigger(monkeypatch)

    result = move_character(pc, "north")

    assert seen == [0], "mp_exit_trigger must fire before the encumbrance gate"
    assert result == ""
    assert pc.room is room
