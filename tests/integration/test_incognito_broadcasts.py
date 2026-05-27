"""BCAST-011 — ``do_incognito`` must emit all three ROM TO_ROOM broadcasts.

ROM contract (``src/act_wiz.c:4375-4418``)::

    if (arg[0] == '\\0') {
        if (ch->incog_level) {
            ch->incog_level = 0;
            act ("$n is no longer cloaked.", ch, NULL, NULL, TO_ROOM);
            ...
        } else {
            ch->incog_level = get_trust (ch);
            act ("$n cloaks $s presence.", ch, NULL, NULL, TO_ROOM);
            ...
        }
    } else {
        ...
        ch->incog_level = level;
        act ("$n cloaks $s presence.", ch, NULL, NULL, TO_ROOM);
    }

Three TO_ROOM acts total. Python pre-fix:

- Toggle-off (uncloak) — no broadcast at all.
- Toggle-on (cloak) — broadcast exists.
- Level-set-with-arg — no broadcast at all.

Audit: BROADCAST_COVERAGE.md row 11, R=3 non-TO_CHAR acts, Py=0.
"""

from __future__ import annotations

import pytest

from mud.commands.imm_display import do_incognito
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


def _setup():
    room = Room(vnum=99965, name="Incognito probe")
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


def test_incognito_toggle_on_broadcasts_cloaks_presence() -> None:
    """ROM line 4395 — toggle-on TO_ROOM 'cloaks $s presence.'"""
    _, immortal, witness = _setup()
    immortal.incog_level = 0

    do_incognito(immortal, "")

    msg = " ".join(witness.messages)
    assert "cloaks" in msg and "presence" in msg, witness.messages


def test_incognito_toggle_off_broadcasts_no_longer_cloaked() -> None:
    """ROM line 4389 — toggle-off TO_ROOM 'is no longer cloaked.'"""
    _, immortal, witness = _setup()
    immortal.incog_level = immortal.trust

    do_incognito(immortal, "")

    msg = " ".join(witness.messages)
    assert "no longer cloaked" in msg, (
        "ROM src/act_wiz.c:4389 emits TO_ROOM 'is no longer cloaked.' "
        f"on uncloak. Got: {witness.messages!r}"
    )


def test_incognito_level_set_branch_broadcasts() -> None:
    """ROM line 4412 — setting an incog level with arg also broadcasts TO_ROOM."""
    _, immortal, witness = _setup()
    immortal.incog_level = 0

    do_incognito(immortal, "10")

    msg = " ".join(witness.messages)
    assert "cloaks" in msg and "presence" in msg, (
        "ROM src/act_wiz.c:4412 emits TO_ROOM 'cloaks $s presence.' "
        f"in the level-set-with-arg branch. Got: {witness.messages!r}"
    )
