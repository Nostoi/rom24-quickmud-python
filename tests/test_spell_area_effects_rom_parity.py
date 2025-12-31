"""ROM parity tests for area-effect and invisibility spells.

Spells covered:
- mass_invis: src/magic.c:5685 (group invisibility)
- holy_word: src/magic.c:5042 (area alignment damage)
- invis: src/magic.c:5252 (AFF_INVISIBLE)

These tests focus on room/group mechanics and ROM-style side effects.
"""

from __future__ import annotations

import mud.skills.handlers as skill_handlers
from mud.math.c_compat import c_div
from mud.models.character import Character
from mud.models.constants import ActFlag, AffectFlag, Position
from mud.models.room import Room
from mud.skills.handlers import holy_word, invis, mass_invis
from mud.utils import rng_mm


def make_character(**overrides) -> Character:
    """Helper to create test characters with common defaults."""

    base = {
        "name": overrides.get("name", "TestChar"),
        "level": overrides.get("level", 30),
        "hit": overrides.get("hit", 200),
        "max_hit": overrides.get("max_hit", 200),
        "mana": overrides.get("mana", 100),
        "max_mana": overrides.get("max_mana", 100),
        "move": overrides.get("move", 100),
        "max_move": overrides.get("max_move", 100),
        "position": overrides.get("position", int(Position.STANDING)),
        "is_npc": overrides.get("is_npc", False),
        "alignment": overrides.get("alignment", 0),
    }

    char = Character(**base)
    for key, value in overrides.items():
        setattr(char, key, value)
    return char


def _make_room(vnum: int = 4000) -> Room:
    return Room(vnum=vnum, name=f"Room {vnum}")


# ==========================================================================
# MASS INVIS (ROM src/magic.c:5685)
# ==========================================================================


def test_mass_invis_applies_to_group_members_in_room() -> None:
    rng_mm.seed_mm(42)

    caster = make_character(name="Oracle", level=25)
    caster.leader = caster
    ally = make_character(name="Scout", level=20)
    ally.leader = caster
    outsider = make_character(name="Bystander", level=14)

    room = _make_room(4001)
    for character in (caster, ally, outsider):
        room.add_character(character)
        character.messages.clear()

    assert mass_invis(caster) is True

    assert caster.has_affect(AffectFlag.INVISIBLE)
    assert ally.has_affect(AffectFlag.INVISIBLE)
    assert not outsider.has_affect(AffectFlag.INVISIBLE)

    ally_effect = ally.spell_effects.get("mass invis")
    assert ally_effect is not None
    assert ally_effect.duration == 24
    assert ally_effect.level == c_div(caster.level, 2)

    assert caster.messages[-1] == "Ok."
    assert ally.messages[-1] == "You slowly fade out of existence."
    assert any("slowly fades out of existence." in msg for msg in outsider.messages)


def test_mass_invis_skips_already_invisible_member() -> None:
    rng_mm.seed_mm(42)

    caster = make_character(name="Oracle", level=25)
    caster.leader = caster
    ally = make_character(name="Scout", level=20)
    ally.leader = caster
    already = make_character(name="Shade", level=18)
    already.leader = caster
    already.add_affect(AffectFlag.INVISIBLE)

    room = _make_room(4002)
    for character in (caster, ally, already):
        room.add_character(character)
        character.messages.clear()

    assert mass_invis(caster) is True

    assert ally.has_spell_effect("mass invis")
    assert not already.has_spell_effect("mass invis")
    assert all("You slowly fade out of existence." not in msg for msg in already.messages)


def test_mass_invis_second_cast_returns_false_when_no_new_targets() -> None:
    rng_mm.seed_mm(42)

    caster = make_character(name="Oracle", level=25)
    caster.leader = caster
    ally = make_character(name="Scout", level=20)
    ally.leader = caster

    room = _make_room(4003)
    for character in (caster, ally):
        room.add_character(character)
        character.messages.clear()

    assert mass_invis(caster) is True

    # Re-seed to keep the test deterministic even if internals change.
    rng_mm.seed_mm(42)
    for character in (caster, ally):
        character.messages.clear()

    assert mass_invis(caster) is False
    assert caster.messages[-1] == "Ok."


def test_mass_invis_requires_room_returns_false() -> None:
    rng_mm.seed_mm(42)

    caster = make_character(name="Oracle", level=25)
    caster.messages.clear()

    assert caster.room is None
    assert mass_invis(caster) is False
    assert caster.messages[-1] == "Ok."


# ==========================================================================
# INVIS (ROM src/magic.c:5252)
# ==========================================================================


def test_invis_applies_invisible_affect_to_target_character() -> None:
    rng_mm.seed_mm(42)

    caster = make_character(name="Magus", level=20)
    target = make_character(name="Shade", level=18)
    witness = make_character(name="Watcher", level=15)

    room = _make_room(4010)
    for character in (caster, target, witness):
        room.add_character(character)
        character.messages.clear()

    assert invis(caster, target) is True

    assert target.has_affect(AffectFlag.INVISIBLE)
    assert target.has_spell_effect("invis")

    effect = target.spell_effects.get("invis")
    assert effect is not None
    assert effect.duration == caster.level + 12
    assert effect.level == caster.level
    assert effect.affect_flag == AffectFlag.INVISIBLE

    assert target.messages[-1] == "You fade out of existence."
    assert witness.messages[-1] == "Shade fades out of existence."


def test_invis_defaults_to_self_targeting() -> None:
    rng_mm.seed_mm(42)

    caster = make_character(name="Magus", level=20)
    room = _make_room(4011)
    room.add_character(caster)
    caster.messages.clear()

    assert invis(caster, None) is True
    assert caster.has_affect(AffectFlag.INVISIBLE)
    assert caster.has_spell_effect("invis")


def test_invis_duplicate_cast_returns_false() -> None:
    rng_mm.seed_mm(42)

    caster = make_character(name="Magus", level=20)
    target = make_character(name="Shade", level=18)

    room = _make_room(4012)
    room.add_character(caster)
    room.add_character(target)

    assert invis(caster, target) is True
    assert invis(caster, target) is False


# ==========================================================================
# HOLY WORD (ROM src/magic.c:5042)
# ==========================================================================


def test_holy_word_requires_room_returns_false() -> None:
    rng_mm.seed_mm(42)

    caster = make_character(name="High Cleric", level=40, alignment=500)
    caster.messages.clear()
    assert caster.room is None

    assert holy_word(caster) is False


def test_holy_word_good_buffs_good_harms_evil_not_neutral(monkeypatch) -> None:
    """Alignment targeting: good buffs good, harms evil, ignores neutral."""

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda *args, **kwargs: False)
    monkeypatch.setattr(skill_handlers, "_is_safe_spell", lambda *args, **kwargs: False)
    from mud.combat import engine

    monkeypatch.setattr(engine, "check_parry", lambda *args, **kwargs: False)
    monkeypatch.setattr(engine, "check_dodge", lambda *args, **kwargs: False)
    monkeypatch.setattr(engine, "check_shield_block", lambda *args, **kwargs: False)

    caster = make_character(
        name="High Cleric",
        level=40,
        alignment=500,
        hit=300,
        max_hit=300,
        move=100,
        max_move=100,
    )
    ally_good = make_character(name="Templar", level=35, alignment=450)
    victim_evil = make_character(name="Heretic", level=38, alignment=-500, hit=500, max_hit=500)
    bystander_neutral = make_character(name="Witness", level=20, alignment=0)

    room = _make_room(4020)
    for character in (caster, ally_good, victim_evil, bystander_neutral):
        room.add_character(character)
        character.messages.clear()

    # Holy word should deal dice(level, 6) vs opposite alignment.
    rng_mm.seed_mm(42)
    expected_damage = rng_mm.dice(caster.level, 6)

    rng_mm.seed_mm(42)
    start_hit = victim_evil.hit

    assert holy_word(caster) is True

    assert victim_evil.hit == start_hit - expected_damage
    assert victim_evil.has_spell_effect("curse")
    assert "You are struck down!" in victim_evil.messages

    assert ally_good.has_spell_effect("frenzy")
    assert ally_good.has_spell_effect("bless")

    # Good caster should also buff self (caster is included in room occupants).
    assert caster.has_spell_effect("frenzy")
    assert caster.has_spell_effect("bless")

    # Neutral occupants are unaffected by a good caster.
    assert not bystander_neutral.has_spell_effect("curse")
    assert not bystander_neutral.has_spell_effect("bless")
    assert not bystander_neutral.has_spell_effect("frenzy")

    assert caster.move == 0
    assert caster.hit == c_div(300, 2)


def test_holy_word_respects_safe_spell_and_does_not_damage_trainers(monkeypatch) -> None:
    """ROM safe targets (trainers, healers, etc.) are not hit by area damage."""

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda *args, **kwargs: False)

    caster = make_character(
        name="High Cleric",
        level=40,
        alignment=500,
        hit=300,
        max_hit=300,
        move=100,
        max_move=100,
    )
    evil_trainer = make_character(
        name="Trainer",
        level=30,
        alignment=-500,
        is_npc=True,
        act=int(ActFlag.TRAIN),
        hit=250,
        max_hit=250,
    )

    room = _make_room(4021)
    room.add_character(caster)
    room.add_character(evil_trainer)
    caster.messages.clear()
    evil_trainer.messages.clear()

    start_hit = evil_trainer.hit

    assert holy_word(caster) is True

    assert evil_trainer.hit == start_hit
    assert not evil_trainer.has_spell_effect("curse")
    assert "You are struck down!" not in evil_trainer.messages


def test_holy_word_neutral_caster_harms_non_neutral_with_half_level_curse(monkeypatch) -> None:
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda *args, **kwargs: False)
    monkeypatch.setattr(skill_handlers, "_is_safe_spell", lambda *args, **kwargs: False)
    from mud.combat import engine

    monkeypatch.setattr(engine, "check_parry", lambda *args, **kwargs: False)
    monkeypatch.setattr(engine, "check_dodge", lambda *args, **kwargs: False)
    monkeypatch.setattr(engine, "check_shield_block", lambda *args, **kwargs: False)

    caster = make_character(
        name="Invoker",
        level=30,
        alignment=0,
        hit=200,
        max_hit=200,
        move=100,
        max_move=100,
    )
    victim_good = make_character(name="Paladin", level=25, alignment=500, hit=500, max_hit=500)

    room = _make_room(4022)
    room.add_character(caster)
    room.add_character(victim_good)
    caster.messages.clear()
    victim_good.messages.clear()

    rng_mm.seed_mm(42)
    expected_damage = rng_mm.dice(caster.level, 4)

    rng_mm.seed_mm(42)
    start_hit = victim_good.hit

    assert holy_word(caster) is True

    assert victim_good.hit == start_hit - expected_damage
    assert victim_good.has_spell_effect("curse")

    curse_effect = victim_good.spell_effects.get("curse")
    assert curse_effect is not None
    assert curse_effect.level == c_div(caster.level, 2)

    assert caster.move == 0
    assert caster.hit == c_div(200, 2)
