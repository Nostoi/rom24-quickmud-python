"""DUPL-004 regression: ``do_peek`` must call canonical ``check_improve``.

ROM ``src/act_info.c:505`` calls ``check_improve (ch, gsn_peek, TRUE, 4)``
on a successful peek roll.  ``mud/commands/misc_player.py:do_peek`` had a
local ``pass``-body ``_check_improve`` stub, so peek improvement never
fired — players using the peek skill in this command path never learned
it.

See ``docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md`` (DUPL-004).
"""

from __future__ import annotations

from unittest.mock import patch

from mud.commands.misc_player import do_peek
from mud.models.character import Character
from mud.models.room import Room


def _peek_target() -> Character:
    target = Character(name="Mark", is_npc=True)
    target.inventory = []
    return target


def test_do_peek_invokes_canonical_check_improve_with_rom_args() -> None:
    """Successful peek must call the canonical ``check_improve``.

    ROM ``src/act_info.c:502-505``:
        if (... && number_percent() < get_skill(ch, gsn_peek))
            check_improve(ch, gsn_peek, TRUE, 4);
    """

    peeker = Character(name="Eddol", is_npc=False)
    target = _peek_target()
    room = Room(vnum=1)
    room.people = [peeker, target]
    peeker.room = room
    target.room = room

    # Patch at the *call site* in misc_player so the test catches the
    # canonical-import wiring (the fix).  Before the fix, the local stub
    # was a no-op; this patched mock would never be invoked.
    with patch("mud.commands.misc_player._get_skill", return_value=100):
        with patch("mud.commands.misc_player.number_percent", return_value=1):
            with patch("mud.commands.misc_player.check_improve") as improve_mock:
                result = do_peek(peeker, "Mark")

    assert improve_mock.called, (
        "do_peek did not call check_improve — DUPL-004 stub bypass. "
        "ROM src/act_info.c:505 calls check_improve(ch, gsn_peek, TRUE, 4)."
    )
    args, kwargs = improve_mock.call_args
    # Accept either positional or keyword multiplier for forwards-compat.
    multiplier = kwargs.get("multiplier", args[3] if len(args) > 3 else None)
    assert args[0] is peeker
    assert args[1] == "peek"
    assert args[2] is True
    assert multiplier == 4, (
        f"ROM passes multiplier=4 (src/act_info.c:505); got {multiplier!r}"
    )
    # Sanity: peek succeeded (target's empty-inventory branch reached).
    assert "Mark is not carrying anything." in result


def test_do_peek_failure_does_not_call_check_improve() -> None:
    """A failed peek roll must NOT trigger improvement.

    ROM only improves on the success branch (src/act_info.c:505 is inside
    the ``number_percent() < get_skill(...)`` guard).
    """

    peeker = Character(name="Eddol", is_npc=False)
    target = _peek_target()
    room = Room(vnum=1)
    room.people = [peeker, target]
    peeker.room = room
    target.room = room

    # Force the skill roll to fail: peek_skill=10 < rolled 50.
    with patch("mud.commands.misc_player._get_skill", return_value=10):
        with patch("mud.commands.misc_player.number_percent", return_value=50):
            with patch("mud.commands.misc_player.check_improve") as improve_mock:
                result = do_peek(peeker, "Mark")

    assert "fail to get a good look" in result
    assert not improve_mock.called
