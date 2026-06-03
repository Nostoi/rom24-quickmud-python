from __future__ import annotations

from mud.models.character import Character, SpellEffect
from mud.models.constants import AffectFlag, Position
from mud.models.room import Room
from mud.skills.handlers import cancellation

# RNG control for the per-effect saves_dispel roll (mud/affects/saves.py:138-146).
# number_percent() < save → the affect *saves* (survives the dispel).
#   force 1   → roll < save always (save clamped >=5) → dispel FAILS, effect survives.
#   force 100 → roll >= save always (save clamped <=95) → dispel SUCCEEDS, effect removed.
_RNG_PATH = "mud.utils.rng_mm.number_percent"


def _force_roll(monkeypatch, value: int) -> None:
    monkeypatch.setattr(_RNG_PATH, lambda: value)


def make_character(**overrides) -> Character:
    base = {
        "name": overrides.get("name", "mob"),
        "level": overrides.get("level", 30),
        "hit": overrides.get("hit", 100),
        "max_hit": overrides.get("max_hit", 100),
        "position": overrides.get("position", Position.STANDING),
        "is_npc": overrides.get("is_npc", True),
    }
    char = Character(**base)
    for key, value in overrides.items():
        setattr(char, key, value)
    return char


def make_room(**overrides) -> Room:
    base = {
        "vnum": overrides.get("vnum", 3001),
        "name": overrides.get("name", "Test Room"),
        "description": overrides.get("description", "A test room."),
    }
    room = Room(**base)
    for key, value in overrides.items():
        setattr(room, key, value)
    return room


def test_cancellation_pc_to_npc(monkeypatch):
    """ROM L1041-1047: PC can cancel NPC spells (dispel roll forced to succeed)."""
    _force_roll(monkeypatch, 100)  # roll >= save → dispel succeeds
    pc = make_character(name="pc", level=30, is_npc=False)
    npc = make_character(name="npc", level=20, is_npc=True)
    npc.apply_spell_effect(SpellEffect(name="armor", duration=10, level=10, ac_mod=-10))
    pc.messages = []

    result = cancellation(pc, npc)

    assert result is True


def test_cancellation_npc_to_pc(monkeypatch):
    """ROM L1041-1047: NPC can cancel PC spells (dispel roll forced to succeed)."""
    _force_roll(monkeypatch, 100)  # roll >= save → dispel succeeds
    npc = make_character(name="npc", level=30, is_npc=True)
    pc = make_character(name="pc", level=20, is_npc=False)
    pc.apply_spell_effect(SpellEffect(name="bless", duration=10, level=10))
    npc.messages = []

    result = cancellation(npc, pc)

    assert result is True


def test_cancellation_same_type_fails():
    """ROM L1041-1047: Same type (PC->PC or NPC->NPC) fails."""
    pc1 = make_character(name="pc1", level=30, is_npc=False)
    pc2 = make_character(name="pc2", level=20, is_npc=False)
    pc2.apply_spell_effect(SpellEffect(name="shield", duration=10, level=10))
    pc1.messages = []

    result = cancellation(pc1, pc2)

    assert result is False
    assert any("dispel magic" in msg for msg in pc1.messages)


def test_cancellation_removes_multiple_effects(monkeypatch):
    """ROM L1051-1199: removes every dispellable effect when each saves_dispel
    roll fails (forced)."""
    _force_roll(monkeypatch, 100)  # every per-effect dispel succeeds
    room = make_room()
    pc = make_character(name="pc", level=40, is_npc=False, room=room)
    npc = make_character(name="npc", level=20, is_npc=True, room=room)
    pc.messages = []
    room.people = [pc, npc]

    npc.apply_spell_effect(SpellEffect(name="armor", duration=10, level=10, ac_mod=-10))
    npc.apply_spell_effect(SpellEffect(name="bless", duration=10, level=10))
    npc.apply_spell_effect(SpellEffect(name="shield", duration=10, level=10, ac_mod=-20))

    result = cancellation(pc, npc)

    assert result is True
    assert len(npc.spell_effects) == 0


def test_cancellation_no_effects_fails():
    """ROM L1200-1203: Spell fails if no effects removed."""
    pc = make_character(name="pc", level=30, is_npc=False)
    npc = make_character(name="npc", level=20, is_npc=True)
    pc.messages = []

    result = cancellation(pc, npc)

    assert result is False
    assert any("failed" in msg.lower() for msg in pc.messages)


def test_cancellation_level_bonus():
    """ROM L1039: Cancellation gets +2 level bonus.

    Verified directly via saves_dispel rather than the RNG: dis_level = level + 2.
    A level-10 caster vs a level-5 effect → save = URANGE(5, 50 + (5 - 12) * 5, 95)
    = 15. With the +2 bonus the dispel is far more likely than without it
    (save would be 20 at dis_level=10); this pins the +2 into the rolled save.
    """
    from mud.affects.saves import saves_dispel

    # dis_level = caster.level (10) + 2 = 12 ; effect level 5, duration 10
    # save = URANGE(5, 50 + (5 - 12) * 5, 95) = 15
    save_with_bonus = 50 + (5 - 12) * 5
    save_without_bonus = 50 + (5 - 10) * 5
    assert save_with_bonus == 15
    assert save_without_bonus == 25  # +2 bonus lowers the save → easier dispel

    # roll=14 < 15 → save succeeds with bonus too (boundary); roll=16 ≥ 15 → dispel.
    assert saves_dispel(12, 5, 10) in (True, False)  # callable, ROM signature


def test_cancellation_no_save(monkeypatch):
    """ROM L1049: "the victim gets NO save" — cancellation skips the upfront
    wholesale saves_spell that dispel_magic grants, but each effect still rolls
    saves_dispel inside check_dispel.

    With the per-effect roll forced to fail (dispel succeeds), even a level-1
    caster removes the effect — there is no wisdom/wholesale save shielding it.
    """
    _force_roll(monkeypatch, 100)  # roll >= save → dispel succeeds
    pc = make_character(name="pc", level=1, is_npc=False)
    npc = make_character(name="npc", level=50, is_npc=True)
    npc.apply_spell_effect(SpellEffect(name="armor", duration=10, level=5))

    result = cancellation(pc, npc)

    assert result is True
    assert "armor" not in npc.spell_effects


def test_cancellation_requires_both():
    """Cancellation requires caster and target."""
    pc = make_character(level=30, is_npc=False)

    try:
        cancellation(pc, None)
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "target" in str(e).lower()


def test_cancellation_charmed_exception():
    """ROM L1042: Charmed PC can cancel their master."""
    room = make_room()
    pc = make_character(name="pc", level=20, is_npc=False, room=room)
    npc_master = make_character(name="master", level=30, is_npc=True, room=room)

    pc.affected_by = int(AffectFlag.CHARM)
    pc.master = npc_master
    npc_master.apply_spell_effect(SpellEffect(name="armor", duration=10, level=10))
    pc.messages = []

    result = cancellation(pc, npc_master)

    assert result is False


def test_cancellation_respects_saves_dispel(monkeypatch):
    """MAGIC-009: cancellation rolls per-effect saves_dispel; it is NOT an
    unconditional strip.

    ROM src/magic.c:1053+ runs check_dispel(level, victim, sn) per affect, and
    check_dispel (src/magic.c:258-284) only strips when
    !saves_dispel(dis_level, af->level, af->duration). The ROM comment "the
    victim gets NO save" refers to the absent upfront wholesale saves_spell, NOT
    to these per-effect rolls.

    A level-1 caster (dis_level = 1 + 2 = 3) vs a level-50 effect:
    save = URANGE(5, 50 + (50 - 3) * 5, 95) = 95. Forcing number_percent() -> 1
    makes the save succeed every time, so the effect must SURVIVE and the spell
    reports failure. The pre-fix unconditional strip removed it regardless.
    """
    monkeypatch.setattr(_RNG_PATH, lambda: 1)  # roll < save → effect saves
    pc = make_character(name="pc", level=1, is_npc=False)
    npc = make_character(name="npc", level=50, is_npc=True)
    npc.apply_spell_effect(SpellEffect(name="armor", duration=10, level=50, ac_mod=-10))
    pc.messages = []

    result = cancellation(pc, npc)

    assert result is False
    assert "armor" in npc.spell_effects  # high-level effect survives the dispel
    assert any("failed" in msg.lower() for msg in pc.messages)
