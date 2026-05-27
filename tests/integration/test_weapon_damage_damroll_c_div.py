"""MATH-001 regression: damroll math must use C truncation, not Python floor.

ROM ``src/fight.c`` ``one_hit``:

    dam += GET_DAMROLL(ch) * UMIN(100, skill) / 100;

C ``/`` truncates toward zero. Python ``//`` floors toward negative infinity.
With cursed gear or debuffs, ``GET_DAMROLL(ch)`` can be negative; the product
``GET_DAMROLL(ch) * UMIN(100, skill)`` is then negative, and any product not
evenly divisible by 100 falls on the diverging side of the two operators.

Pin the contract: ``mud/combat/engine.py:calculate_weapon_damage`` must use
``c_div`` so cursed-damroll Players take ROM damage, not 1-point-over-debited
Python damage.
"""

from __future__ import annotations

import pytest

from mud.combat.engine import calculate_weapon_damage
from mud.models.constants import DamageType, Position
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world


def test_damroll_uses_c_truncation_not_python_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    """With skill=99 and damroll=-1 the damroll contribution must be 0, not -1.

    Computation: ``GET_DAMROLL(ch) * UMIN(100, skill) = -1 * 99 = -99``.

    - Python ``-99 // 100 == -1`` (floor toward negative infinity)
    - C    ``-99 / 100 ==  0`` (truncate toward zero) — what ROM does.

    The fix is to replace ``//`` with ``c_div`` from ``mud.math.c_compat``.
    """
    initialize_world()
    room_vnum = 3001

    attacker = create_test_character("Cursed", room_vnum)
    attacker.level = 20
    attacker.enhanced_damage_skill = 0

    victim = create_test_character("Dummy", room_vnum)
    victim.hit = 100
    victim.position = Position.FIGHTING

    # Neutralize STR_APP[].todam so get_damroll returns ch.damroll verbatim.
    monkeypatch.setattr("mud.combat.engine.get_damroll", lambda ch: int(getattr(ch, "damroll", 0) or 0))

    # Control: damroll = 0. No contribution from the damroll line either way.
    attacker.damroll = 0
    rng_mm.seed_mm(12345)
    dam_control = calculate_weapon_damage(attacker, victim, DamageType.BASH, skill=99)

    # Test: damroll = -1. ROM contribution = c_div(-99, 100) = 0. Python // gives -1.
    attacker.damroll = -1
    rng_mm.seed_mm(12345)
    dam_negative = calculate_weapon_damage(attacker, victim, DamageType.BASH, skill=99)

    # Damroll contribution must be 0 under ROM C-truncation semantics; Python // would give -1.
    assert dam_negative == dam_control, (
        f"MATH-001: cursed-damroll math diverges from ROM. "
        f"damroll=0 → {dam_control}; damroll=-1 → {dam_negative}; "
        f"diff = {dam_control - dam_negative} (ROM `c_div(-99, 100)` = 0; Python `-99 // 100` = -1)."
    )
