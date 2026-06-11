"""Tests for ROM damage soft-cap: src/fight.c:717-720.

ROM applies two sequential caps inside damage() before any other modifier:
    if (dam > 35) dam = (dam - 35) / 2 + 35;
    if (dam > 80) dam = (dam - 80) / 2 + 80;

Python's apply_damage() was missing both caps entirely.  FIGHT-056.
"""

from mud.combat.engine import apply_damage
from mud.models.character import Character
from mud.models.constants import DamageType, Position
from mud.models.room import Room
from mud.utils import rng_mm

_DUMMY_ROOM = Room(vnum=99990, name="X", description="", room_flags=0, sector_type=0)

# Dam type with no RIV flags set on victim → pure cap test
_DAM_TYPE = int(DamageType.BASH)


def _pair():
    attacker = Character(name="Attacker", level=10, position=Position.STANDING)
    # res_flags=0, imm_flags=0, vuln_flags=0 by default → no RIV scaling
    victim = Character(name="Victim", level=10, hit=500, max_hit=500, position=Position.STANDING)
    attacker.room = _DUMMY_ROOM
    victim.room = _DUMMY_ROOM
    return attacker, victim


def test_fight056_damage_below_35_unchanged():
    """Damage ≤ 35 passes through the cap unchanged."""
    # mirrors ROM src/fight.c:717 — `if (dam > 35)` is strict greater-than
    rng_mm.seed_mm(12345)
    a, v = _pair()
    # dt=None → _should_check_weapon_defenses returns False → defenses skipped
    apply_damage(a, v, 35, _DAM_TYPE)
    assert v.hit == 500 - 35


def test_fight056_first_cap_applied_above_35():
    """Damage 50 → (50-35)/2+35 = 42 after first cap."""
    # mirrors ROM src/fight.c:717-718 — dam = (dam-35)/2 + 35
    rng_mm.seed_mm(12345)
    a, v = _pair()
    apply_damage(a, v, 50, _DAM_TYPE)
    # ROM C integer division: (50-35)/2+35 = 15/2+35 = 7+35 = 42
    assert v.hit == 500 - 42


def test_fight056_both_caps_applied_above_80():
    """Damage 200 triggers both caps: first to 117, second to 98."""
    # mirrors ROM src/fight.c:717-720 — sequential cap application
    rng_mm.seed_mm(12345)
    a, v = _pair()
    apply_damage(a, v, 200, _DAM_TYPE)
    # First cap:  (200-35)/2+35 = 165/2+35 = 82+35 = 117
    # Second cap: (117-80)/2+80 = 37/2+80  = 18+80  = 98
    assert v.hit == 500 - 98


def test_fight056_boundary_exactly_80_no_second_cap():
    """Damage that first-caps to exactly 80 skips the second cap."""
    # mirrors ROM src/fight.c:719 — `if (dam > 80)` strict greater-than
    rng_mm.seed_mm(12345)
    a, v = _pair()
    # (dam-35)/2+35 = 80  →  dam = 125
    apply_damage(a, v, 125, _DAM_TYPE)
    # First cap: (125-35)/2+35 = 90/2+35 = 45+35 = 80; 80 is NOT > 80 → no second cap
    assert v.hit == 500 - 80
