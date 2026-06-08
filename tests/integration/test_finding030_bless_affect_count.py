"""FINDING-030 — bless emits 1 AffectData at low levels; ROM C emits 2.

ROM ``spell_bless`` (``src/magic.c:849-860``) always calls ``affect_to_char``
twice unconditionally:

    af.location = APPLY_HITROLL;  af.modifier = level / 8;
    affect_to_char(victim, &af);

    af.location = APPLY_SAVING_SPELL;  af.modifier = 0 - level / 8;
    affect_to_char(victim, &af);

At ``char_level <= 7``, ``c_div(level, 8) == 0`` so both modifiers are zero —
but ROM still inserts two AFFECT_DATA nodes.  Python's
``sync_spell_effect_to_affected`` guarded with ``if effect.hitroll_mod:`` /
``if effect.saving_throw_mod:`` — falsy for 0 — so it skipped both and fell
through to the APPLY_NONE fallback.  Result: 1 entry instead of 2, causing
``char_update`` to consume one fewer ``number_range`` call per tick (RNG drift).

Fix: change ``SpellEffect.hitroll_mod`` / ``saving_throw_mod`` defaults from
``0`` to ``None``; update the guards to ``is not None``.

REGRESSION GUARD: ``armor`` (whose ``hitroll_mod`` is never set, so will be
``None`` after the fix) must still produce exactly 1 APPLY_AC entry — the
``None`` default must *not* trigger the APPLY_HITROLL branch.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.skills.handlers import armor, bless
from mud.skills.registry import load_skills, skill_registry
from mud.utils import rng_mm

# APPLY_* constants (src/merc.h)
APPLY_NONE = 0
APPLY_AC = 17
APPLY_HITROLL = 18
APPLY_SAVES = 20


@pytest.fixture(autouse=True)
def _load_skills():
    skill_registry.skills.clear()
    skill_registry.handlers.clear()
    load_skills(Path("data/skills.json"))
    yield
    skill_registry.skills.clear()
    skill_registry.handlers.clear()


def _cleric(name: str, room: Room, level: int) -> Character:
    return Character(
        name=name,
        level=level,
        ch_class=1,  # cleric — bless skill_level[cleric] = 7
        is_npc=False,
        perm_stat=[18, 18, 18, 18, 18],
        mana=500,
        position=int(Position.STANDING),
        skills={"bless": 100, "armor": 100},
    )


# ---------------------------------------------------------------------------
# FINDING-030 failing test: bless at low level must produce 2 AffectData
# ---------------------------------------------------------------------------


def test_bless_low_level_emits_two_affect_data_entries():
    """bless at level 5 (c_div(5,8)==0) must produce 2 AffectData: APPLY_HITROLL
    and APPLY_SAVES, both modifier=0 — mirroring ROM src/magic.c:849-860.

    Before fix: 1 entry at APPLY_NONE (the FINDING-030 bug).
    """
    room = Room(vnum=99301, name="Chapel")
    ch = _cleric("Pilgrim", room, level=5)
    ch.room = room
    room.people.append(ch)

    rng_mm.seed_mm(12345)
    result = bless(ch)

    assert result is True
    assert ch.has_spell_effect("bless")

    locations = {ad.location for ad in ch.affected if ad.type == "bless"}
    # ROM emits APPLY_HITROLL + APPLY_SAVES unconditionally (magic.c:849-860)
    assert locations == {APPLY_HITROLL, APPLY_SAVES}, (
        f"expected {{APPLY_HITROLL={APPLY_HITROLL}, APPLY_SAVES={APPLY_SAVES}}}, "
        f"got {locations!r} (FINDING-030: falsy guard skips zero-modifier entries)"
    )

    # Both modifiers must be 0 (c_div(5,8) == 0)
    for ad in ch.affected:
        if ad.type == "bless" and ad.location == APPLY_HITROLL:
            assert ad.modifier == 0, f"APPLY_HITROLL modifier: {ad.modifier}"
        if ad.type == "bless" and ad.location == APPLY_SAVES:
            assert ad.modifier == 0, f"APPLY_SAVES modifier: {ad.modifier}"


def test_bless_high_level_still_emits_two_affect_data_entries():
    """bless at level 16 (c_div(16,8)==2) must still produce 2 entries.

    This is the non-zero path that should never have been broken; verifying
    it doesn't regress after the FINDING-030 fix.
    """
    room = Room(vnum=99302, name="Chapel")
    ch = _cleric("Paladin", room, level=16)
    ch.room = room
    room.people.append(ch)

    rng_mm.seed_mm(12345)
    result = bless(ch)

    assert result is True

    bless_entries = [ad for ad in ch.affected if ad.type == "bless"]
    assert len(bless_entries) == 2, f"expected 2 AffectData for bless@level16, got {len(bless_entries)}"

    loc_to_mod = {ad.location: ad.modifier for ad in bless_entries}
    assert loc_to_mod.get(APPLY_HITROLL) == 2, loc_to_mod
    assert loc_to_mod.get(APPLY_SAVES) == -2, loc_to_mod


def test_armor_still_emits_only_one_affect_data_entry():
    """armor must still produce exactly 1 APPLY_AC entry after the fix.

    Regression guard: the None default for hitroll_mod / saving_throw_mod
    must NOT cause a spurious APPLY_HITROLL entry for armor (which never sets
    those fields).  mirrors ROM src/magic.c:spell_armor.
    """
    room = Room(vnum=99303, name="Chapel")
    ch = _cleric("Fighter", room, level=10)
    ch.room = room
    room.people.append(ch)

    rng_mm.seed_mm(12345)
    result = armor(ch)

    assert result is True

    armor_entries = [ad for ad in ch.affected if ad.type == "armor"]
    assert len(armor_entries) == 1, (
        f"expected 1 AffectData for armor, got {len(armor_entries)}: {[ad.location for ad in armor_entries]}"
    )
    assert armor_entries[0].location == APPLY_AC, armor_entries[0].location
