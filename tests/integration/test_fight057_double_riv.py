"""Tests for double-RIV bug: attack_round applied RIV then apply_damage applied it again.

ROM src/fight.c:804-816 applies resistance/vulnerability exactly once inside damage().
Python split the combat pipeline across attack_round + apply_damage, and RIV ended up
being applied in both halves for weapon attacks.  FIGHT-057.
"""

import mud.combat.engine as eng
import mud.utils.rng_mm as _rng
from mud.combat.engine import attack_round
from mud.models.character import Character, PCData
from mud.models.constants import Position
from mud.models.room import Room
from mud.utils import rng_mm

_DUMMY_ROOM = Room(vnum=99991, name="X", description="", room_flags=0, sector_type=0)

# BASH resistant bit confirmed by probe: bit 3 → IS_RESISTANT in _riv_check
_BASH_RESISTANT_BIT = 1 << 3


def _pair():
    attacker = Character(name="Attacker", level=10, hitroll=100, damroll=0, position=Position.STANDING)
    victim = Character(name="Victim", level=10, hit=500, max_hit=500, position=Position.STANDING, pcdata=PCData())
    attacker.room = _DUMMY_ROOM
    victim.room = _DUMMY_ROOM
    return attacker, victim


def test_fight057_resistant_damage_reduced_once_not_twice(monkeypatch):
    """A BASH-resistant victim should take dam - dam/3, not (dam - dam/3) - (dam - dam/3)/3.

    ROM src/fight.c:809 — IS_RESISTANT: dam -= dam/3  (exactly once in damage()).
    Before fix: attack_round applied RIV then apply_damage applied it again.
    """
    # Pin hit roll to guaranteed-hit nat-19 (FIGHT-019 model)
    monkeypatch.setattr(_rng, "number_bits", lambda bits: 19)
    # Fix weapon damage to a known value so the expected cap + RIV are deterministic
    monkeypatch.setattr(eng, "calculate_weapon_damage", lambda *a, **kw: 50)

    # Baseline: no resistance
    rng_mm.seed_mm(12345)
    a_base, v_base = _pair()
    v_base.res_flags = 0
    attack_round(a_base, v_base)
    # soft-cap: (50-35)/2+35 = 42; no RIV
    base_dmg = 500 - v_base.hit

    # BASH-resistant victim: should take base_dmg - base_dmg/3 (single RIV)
    rng_mm.seed_mm(12345)
    a, v = _pair()
    v.res_flags = _BASH_RESISTANT_BIT
    attack_round(a, v)
    actual_dmg = 500 - v.hit

    # mirroring ROM src/fight.c:809 — single RIV: dam -= dam/3
    expected_single_riv = base_dmg - base_dmg // 3
    # Double RIV (pre-fix bug): apply twice
    expected_double_riv = expected_single_riv - expected_single_riv // 3

    assert actual_dmg == expected_single_riv, (
        f"Expected single-RIV damage {expected_single_riv}, got {actual_dmg}. "
        f"Double-RIV would give {expected_double_riv}."
    )


def test_fight057_vulnerable_damage_increased_once_not_twice(monkeypatch):
    """A BASH-vulnerable victim should take dam + dam/2, not (dam + dam/2) + (dam + dam/2)/2.

    ROM src/fight.c:812 — IS_VULNERABLE: dam += dam/2  (exactly once in damage()).
    """
    monkeypatch.setattr(_rng, "number_bits", lambda bits: 19)
    monkeypatch.setattr(eng, "calculate_weapon_damage", lambda *a, **kw: 30)

    # Baseline (no RIV), damage 30 ≤ 35 so no soft-cap
    rng_mm.seed_mm(12345)
    a_base, v_base = _pair()
    v_base.vuln_flags = 0
    attack_round(a_base, v_base)
    base_dmg = 500 - v_base.hit

    # BASH-vulnerable victim: bit 3 in vuln_flags triggers IS_VULNERABLE
    rng_mm.seed_mm(12345)
    a, v = _pair()
    v.vuln_flags = _BASH_RESISTANT_BIT
    attack_round(a, v)
    actual_dmg = 500 - v.hit

    # mirroring ROM src/fight.c:812 — single VULN: dam += dam/2
    expected_single_vuln = base_dmg + base_dmg // 2

    assert actual_dmg == expected_single_vuln, f"Expected single-VULN damage {expected_single_vuln}, got {actual_dmg}."
