"""Tests for FIGHT-058: spell/skill damage bypasses drunk/sanctuary/protection reductions.

ROM src/fight.c:775-785 applies all three modifiers inside damage() for every caller.
Python factored apply_damage_reduction into a helper called only from one_hit (melee
weapon path), so every direct apply_damage caller (fireball, flamestrike, etc.) skipped
reductions entirely.  FIGHT-058.
"""

from mud.combat.engine import apply_damage
from mud.models.character import Character, PCData, SpellEffect
from mud.models.constants import AffectFlag, DamageType, Position
from mud.models.room import Room
from mud.utils import rng_mm

_DUMMY_ROOM = Room(vnum=99992, name="X", description="", room_flags=0, sector_type=0)
_DAM_TYPE = int(DamageType.FIRE)


def _pair():
    attacker = Character(name="Attacker", level=10, position=Position.STANDING)
    victim = Character(
        name="Victim",
        level=10,
        hit=500,
        max_hit=500,
        position=Position.STANDING,
        pcdata=PCData(),
    )
    attacker.room = _DUMMY_ROOM
    victim.room = _DUMMY_ROOM
    return attacker, victim


def test_fight058_spell_applies_sanctuary_reduction():
    """Sanctuary halves spell damage — apply_damage must call apply_damage_reduction.

    mirrors ROM src/fight.c:779-780 — if IS_AFFECTED(victim, AFF_SANCTUARY) dam /= 2;
    Before fix: fireball-path apply_damage skipped reductions; victim took 40, not 20.
    """
    rng_mm.seed_mm(12345)
    attacker, victim = _pair()
    victim.apply_spell_effect(SpellEffect(name="sanctuary", duration=10, level=20, affect_flag=AffectFlag.SANCTUARY))
    # dt="fireball" → string → _should_check_weapon_defenses returns False (no parry/dodge)
    apply_damage(attacker, victim, 40, _DAM_TYPE, dt="fireball")
    # ROM: 40 > 35 → first cap: (40-35)/2+35 = 37 (post soft-cap); 37 <= 80 → no second cap
    # Sanctuary: 37 // 2 = 18 (c_div truncates toward zero)
    assert victim.hit == 500 - 18


def test_fight058_spell_applies_drunk_reduction():
    """Drunk condition (PC only) reduces spell damage to 9/10.

    mirrors ROM src/fight.c:775-778 — if !IS_NPC(victim) && condition[COND_DRUNK] > 10: dam = 9*dam/10;
    Before fix: spell damage ignored drunk entirely.
    """
    rng_mm.seed_mm(12345)
    attacker, victim = _pair()
    # COND_DRUNK = index 0, must be > 10
    assert victim.pcdata is not None
    victim.pcdata.condition = [15, 0, 0]
    apply_damage(attacker, victim, 40, _DAM_TYPE, dt="fireball")
    # soft-cap: (40-35)/2+35 = 37; drunk: 9*37/10 = 333/10 = 33 (c_div truncates)
    assert victim.hit == 500 - 33


def test_fight058_spell_applies_protect_evil_reduction():
    """protect_evil reduces damage by 1/4 when attacker is evil (align <= -350).

    mirrors ROM src/fight.c:781-784 — IS_AFFECTED(victim, AFF_PROTECT_EVIL) && IS_EVIL(ch): dam -= dam/4;
    Before fix: spells bypassed the alignment protection entirely.
    """
    rng_mm.seed_mm(12345)
    attacker, victim = _pair()
    attacker.alignment = -500  # IS_EVIL: alignment <= -350
    victim.apply_spell_effect(
        SpellEffect(name="protection evil", duration=10, level=20, affect_flag=AffectFlag.PROTECT_EVIL)
    )
    apply_damage(attacker, victim, 40, _DAM_TYPE, dt="fireball")
    # soft-cap: (40-35)/2+35 = 37; protect_evil: 37 - 37//4 = 37 - 9 = 28
    assert victim.hit == 500 - 28


def test_fight058_melee_does_not_double_reduce_sanctuary():
    """Melee path must not apply sanctuary twice after moving reduction inside apply_damage.

    Before fix: one_hit called apply_damage_reduction then apply_damage — each step halved.
    After fix: one_hit no longer pre-reduces; apply_damage handles it once.
    """
    rng_mm.seed_mm(12345)
    attacker, victim = _pair()
    victim.apply_spell_effect(SpellEffect(name="sanctuary", duration=10, level=20, affect_flag=AffectFlag.SANCTUARY))
    # Bypass the weapon-swing machinery; call apply_damage directly as one_hit would after fix.
    # dt=None → _should_check_weapon_defenses False (no parry/dodge, clean test).
    apply_damage(attacker, victim, 40, _DAM_TYPE, dt=None)
    # Exactly one sanctuary halving: soft-cap 40→37, sanctuary 37→18
    assert victim.hit == 500 - 18
