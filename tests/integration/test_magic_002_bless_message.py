"""Regression for MAGIC-002 (bless instance) — port ROM ``spell_bless`` messaging.

ROM ``spell_bless`` (``src/magic.c:782-866``) for a *character* target:

  * on success sends "You feel righteous." to the victim (TO_VICT), and
    ``act("You grant $N the favor of your god.")`` to the caster (TO_CHAR)
    when ``ch != victim``;
  * the already-affected branch fires when ``victim->position == POS_FIGHTING
    || is_affected(victim, sn)`` — note the ROM quirk that a *fighting* target
    is treated as already-blessed even when it carries no bless affect — and
    sends "You are already blessed." (self) / ``act("$N already has divine
    favor.")`` (cross-target).

The Python ``bless`` handler applied the +hitroll / -saving-throw affect but was
*silent* on success, and since ``do_cast`` is silent on a successful cast
(FINDING-013 — all output comes from the spell function), the line was dropped
entirely. The already-affected branch returned ``False`` with no message at all.

This mirrors the ``armor`` fix (MAGIC-002, 2.11.20); ``bless`` is the remaining
genuinely-*silent* affect spell. ROM C: src/magic.c:782-866 (spell_bless).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mud.commands.combat import do_cast
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.skills.handlers import bless
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


def _cleric(name: str, room: Room) -> Character:
    # bless skill_level[cleric] == 7 (data/skills.json levels [53,7,53,8]);
    # level 20 cleric (ch_class=1) clears it. +hitroll/-save are level-scaled
    # but level-independent of the message path.
    char = Character(
        name=name,
        level=20,
        ch_class=1,
        is_npc=False,
        perm_stat=[18, 18, 18, 18, 18],
        mana=200,
        position=int(Position.STANDING),
        skills={"bless": 100},
    )
    char.room = room
    room.people.append(char)
    char.messages = []
    return char


def test_bless_self_cast_sends_rom_success_message():
    """Self-cast bless must deliver ROM's "You feel righteous." line
    (src/magic.c:861).

    Exercised at the handler level: bless is ROM ``TAR_OBJ_CHAR_DEF``
    (src/const.c:968), so a no-arg cast defaults to self (src/magic.c:514-519).
    The success messaging under test lives inside ``spell_bless`` itself; the
    cross-target tests below cover the full do_cast → handler integration.
    (CAST-002 — do_cast's no-arg self-default for the defensive object/char
    spells — is now fixed; the do_cast → self path is covered by
    tests/test_skills_spells_cast_listing.py::test_do_cast_defensive_obj_char_no_target_defaults_to_self.)
    """
    room = Room(vnum=99201, name="Chapel")
    caster = _cleric("Tester", room)

    rng_mm.seed_mm(42)
    result = bless(caster)

    assert result is True
    assert any("You feel righteous." in m for m in caster.messages), caster.messages
    assert caster.has_spell_effect("bless")


def test_bless_cross_target_messages_caster_and_victim():
    """A cross-target cast sends the victim "You feel righteous." and the caster
    "You grant $N the favor of your god." (ROM src/magic.c:861-864)."""
    room = Room(vnum=99202, name="Chapel")
    caster = _cleric("Caster", room)
    victim = _cleric("Bob", room)

    rng_mm.seed_mm(42)
    result = do_cast(caster, "bless Bob")

    assert result == ""
    assert any("You feel righteous." in m for m in victim.messages), victim.messages
    assert any("You grant Bob the favor of your god." in m for m in caster.messages), caster.messages
    assert victim.has_spell_effect("bless")


def test_bless_already_affected_uses_rom_message():
    """The already-affected branch is ROM's "You are already blessed." for a
    self-cast (src/magic.c:842-843).

    Handler-level for the same CAST-002 reason as the self-cast success test.
    """
    room = Room(vnum=99203, name="Chapel")
    caster = _cleric("Tester", room)

    rng_mm.seed_mm(42)
    assert bless(caster) is True
    caster.messages.clear()
    result = bless(caster)

    assert result is False
    assert any("You are already blessed." in m for m in caster.messages), caster.messages


def test_bless_already_affected_cross_target_uses_rom_act_message():
    """The cross-target already-affected branch is ROM's `act("$N already has
    divine favor.")` to the caster (src/magic.c:845)."""
    room = Room(vnum=99204, name="Chapel")
    caster = _cleric("Caster", room)
    victim = _cleric("Bob", room)

    rng_mm.seed_mm(42)
    do_cast(caster, "bless Bob")
    caster.messages.clear()
    victim.messages.clear()
    caster.wait = 0
    result = do_cast(caster, "bless Bob")

    assert result == ""
    assert any("Bob already has divine favor." in m for m in caster.messages), caster.messages


def test_bless_on_fighting_target_reports_already_blessed():
    """ROM quirk (src/magic.c:840): a target whose position == POS_FIGHTING is
    treated as already-blessed even with no bless affect — self-cast reports
    "You are already blessed." and applies nothing.

    Exercised at the handler level: ``do_cast`` target resolution is orthogonal
    (a FIGHTING caster with no opponent triggers its own "Cast the spell on
    whom?" path); the quirk under test lives inside ``spell_bless`` itself.
    """
    room = Room(vnum=99205, name="Chapel")
    caster = _cleric("Tester", room)
    caster.position = int(Position.FIGHTING)

    rng_mm.seed_mm(42)
    result = bless(caster, caster)

    assert result is False
    assert any("You are already blessed." in m for m in caster.messages), caster.messages
    assert not caster.has_spell_effect("bless")
