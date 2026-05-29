"""Regression for MAGIC-002 / FINDING-015 (differential `affect_armor` scenario, 2026-05-29).

ROM `spell_armor` (`src/magic.c:753-777`) sends "You feel someone protecting you."
to the victim on a successful cast (and `act("$N is protected by your magic.")` to
the caster for a cross-target cast); the already-affected branch is
"You are already armored." / `act("$N is already armored.")`. The Python `armor`
handler applied the -20 AC affect but was *silent* on success, and since `do_cast`
is silent on a successful cast (FINDING-013 — all output comes from the spell
function), the line was dropped entirely.

Surfaced by the `affect_armor` differential scenario, step 3 (`cast armor`):
  C : ['You feel someone protecting you.']
  py: []
(affects/eff_ac/mana all converged — only `output` diverged.)

ROM C: src/magic.c:753-777 (spell_armor).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mud.commands.combat import do_cast
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.skills.registry import load_skills, skill_registry
from mud.utils import rng_mm


@pytest.fixture(autouse=True)
def _load_skills():
    skill_registry.skills.clear()
    skill_registry.handlers.clear()
    load_skills(Path("data/skills.json"))
    yield
    skill_registry.skills.clear()
    skill_registry.handlers.clear()


def _mage(name: str, room: Room) -> Character:
    # Level 10 clears armor's mage skill_level (7); -20 AC is level-independent.
    char = Character(
        name=name,
        level=10,
        ch_class=0,
        is_npc=False,
        perm_stat=[0, 18, 0, 0, 0],
        mana=200,
        position=int(Position.STANDING),
        skills={"armor": 100},
        armor=[100, 100, 100, 100],
    )
    char.room = room
    room.people.append(char)
    char.messages = []
    return char


def test_armor_self_cast_sends_rom_success_message():
    """Self-cast armor must deliver ROM's "You feel someone protecting you." line
    (the exact divergence the affect_armor differential scenario surfaced)."""
    room = Room(vnum=99101, name="Arena")
    caster = _mage("Tester", room)

    rng_mm.seed_mm(42)
    result = do_cast(caster, "armor")

    # do_cast itself is silent on success (FINDING-013); the message comes from
    # the spell function, exactly as ROM spell_armor's send_to_char does.
    assert result == ""
    assert any("You feel someone protecting you." in m for m in caster.messages), caster.messages
    # The affect still applies: ROM spell_armor APPLY_AC -20 (src/magic.c:771).
    assert caster.armor == [80, 80, 80, 80]
    assert caster.has_spell_effect("armor")


def test_armor_cross_target_messages_caster_and_victim():
    """A cross-target cast sends the victim "You feel someone protecting you." and
    the caster "$N is protected by your magic." (ROM src/magic.c:773-775)."""
    room = Room(vnum=99102, name="Arena")
    caster = _mage("Caster", room)
    victim = _mage("Bob", room)  # victim need not cast; only receives the affect

    rng_mm.seed_mm(42)
    result = do_cast(caster, "armor Bob")

    assert result == ""
    assert any("You feel someone protecting you." in m for m in victim.messages), victim.messages
    assert any("Bob is protected by your magic." in m for m in caster.messages), caster.messages
    assert victim.armor == [80, 80, 80, 80]


def test_armor_already_affected_uses_rom_message():
    """The already-affected branch is ROM's "You are already armored." for a
    self-cast (src/magic.c:758-763), not the legacy "They are already protected.\""""
    room = Room(vnum=99103, name="Arena")
    caster = _mage("Tester", room)

    rng_mm.seed_mm(42)
    do_cast(caster, "armor")
    caster.messages.clear()
    # Reset wait so the second cast is not gated (handler-level wait, FINDING-014).
    caster.wait = 0
    result = do_cast(caster, "armor")

    assert result == ""
    assert any("You are already armored." in m for m in caster.messages), caster.messages
    # No second affect / no further AC change.
    assert caster.armor == [80, 80, 80, 80]


def test_armor_already_affected_cross_target_uses_rom_act_message():
    """The cross-target already-affected branch is ROM's `act("$N is already
    armored.")` to the caster (src/magic.c:761), not the self "You are already
    armored." line."""
    room = Room(vnum=99104, name="Arena")
    caster = _mage("Caster", room)
    victim = _mage("Bob", room)

    rng_mm.seed_mm(42)
    do_cast(caster, "armor Bob")
    caster.messages.clear()
    victim.messages.clear()
    caster.wait = 0
    result = do_cast(caster, "armor Bob")

    assert result == ""
    assert any("Bob is already armored." in m for m in caster.messages), caster.messages
    assert victim.armor == [80, 80, 80, 80]
