"""BCAST-012 — ``do_invis`` must emit all three ROM TO_ROOM broadcasts.

ROM contract (``src/act_wiz.c:4329-4372``)::

    if (arg[0] == '\\0') {
        if (ch->invis_level) {
            ch->invis_level = 0;
            act ("$n slowly fades into existence.", ch, NULL, NULL, TO_ROOM);
            ...
        } else {
            ch->invis_level = get_trust (ch);
            act ("$n slowly fades into thin air.", ch, NULL, NULL, TO_ROOM);
            ...
        }
    } else {
        ...
        ch->invis_level = level;
        act ("$n slowly fades into thin air.", ch, NULL, NULL, TO_ROOM);
    }

Three TO_ROOM acts total. Python pre-fix:

- Toggle-off broadcast existed but said "fades **back** into
  existence" (ROM is canonical — no "back").
- Toggle-on broadcast: correct.
- Level-set-with-arg branch: missing the broadcast entirely.

Audit: BROADCAST_COVERAGE.md row 12, R=3 non-TO_CHAR acts.
"""

from __future__ import annotations

import pytest

from mud.commands.imm_display import do_invis
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)


def _setup_room_with_actor_and_witness():
    room = Room(vnum=99964, name="Invis probe")
    immortal = Character(name="Wizard", is_npc=False, position=Position.STANDING)
    immortal.level = 60
    immortal.trust = 60
    immortal.messages = []
    witness = Character(name="Witness", is_npc=False, position=Position.STANDING)
    witness.level = 10
    witness.trust = 10
    witness.messages = []
    room.add_character(immortal)
    room.add_character(witness)
    character_registry.extend([immortal, witness])
    return room, immortal, witness


def test_invis_toggle_on_broadcasts_fades_into_thin_air() -> None:
    """ROM line 4349 — toggle-on TO_ROOM 'fades into thin air'."""
    _, immortal, witness = _setup_room_with_actor_and_witness()
    immortal.invis_level = 0

    do_invis(immortal, "")

    msg = " ".join(witness.messages)
    assert "fades into thin air" in msg, witness.messages


def test_invis_toggle_off_matches_rom_wording_no_back() -> None:
    """ROM line 4343 — toggle-off TO_ROOM 'fades into existence.' (no 'back')."""
    _, immortal, witness = _setup_room_with_actor_and_witness()
    immortal.invis_level = immortal.trust

    do_invis(immortal, "")

    msg = " ".join(witness.messages)
    # ROM is canonical; the message must read "fades into existence",
    # NOT "fades back into existence".
    assert "fades into existence" in msg, witness.messages
    assert "fades back into existence" not in msg, (
        f"ROM src/act_wiz.c:4343 — message is 'fades into existence.', with no 'back'. Got: {witness.messages!r}"
    )


def test_invis_level_set_branch_broadcasts() -> None:
    """ROM line 4366 — setting an invis level with arg also broadcasts TO_ROOM."""
    _, immortal, witness = _setup_room_with_actor_and_witness()
    immortal.invis_level = 0

    do_invis(immortal, "10")  # level arg, valid (2 <= 10 <= trust=60)

    msg = " ".join(witness.messages)
    assert "fades into thin air" in msg, (
        "ROM src/act_wiz.c:4366 emits TO_ROOM 'fades into thin air' "
        f"in the level-set-with-arg branch. Got: {witness.messages!r}"
    )
