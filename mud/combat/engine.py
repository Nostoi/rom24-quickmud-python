from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import (
    Position,
    DamageType,
    AC_PIERCE,
    AC_BASH,
    AC_SLASH,
    AC_EXOTIC,
)
from mud.utils import rng_mm


def attack_round(attacker: Character, victim: Character) -> str:
    """Resolve a single attack round.

    The attacker attempts to hit the victim.  Hit chance is derived from a
    base 50% modified by the attacker's ``hitroll``.  Successful hits apply
    ``damroll`` damage.  Living combatants are placed into FIGHTING position.
    If the victim dies, they are removed from the room and their position set
    to ``DEAD``.
    """

    attacker.position = Position.FIGHTING
    victim.position = Position.FIGHTING

    to_hit = 50 + attacker.hitroll
    # Use ROM-compatible RNG percent roll.
    if rng_mm.number_percent() > to_hit:
        return f"You miss {victim.name}."

    # Defense checks in ROM order: shield block → parry → dodge.
    if check_shield_block(attacker, victim):
        return f"{victim.name} blocks your attack with a shield."
    if check_parry(attacker, victim):
        return f"{victim.name} parries your attack."
    if check_dodge(attacker, victim):
        return f"{victim.name} dodges your attack."

    damage = max(1, attacker.damroll)
    victim.hit -= damage
    if victim.hit <= 0:
        victim.hit = 0
        victim.position = Position.DEAD
        attacker.position = Position.STANDING
        if getattr(victim, "room", None):
            victim.room.broadcast(f"{victim.name} is DEAD!!!", exclude=victim)
            victim.room.remove_character(victim)
        return f"You kill {victim.name}."
    return f"You hit {victim.name} for {damage} damage."


# --- Defense checks (override in tests as needed) ---
def check_shield_block(attacker: Character, victim: Character) -> bool:  # pragma: no cover - default stub
    return False


def check_parry(attacker: Character, victim: Character) -> bool:  # pragma: no cover - default stub
    return False


def check_dodge(attacker: Character, victim: Character) -> bool:  # pragma: no cover - default stub
    return False


# --- AC mapping helpers ---
def ac_index_for_dam_type(dam_type: int) -> int:
    """Map a damage type to the correct AC index.

    ROM maps: PIERCE→AC_PIERCE, BASH→AC_BASH, SLASH→AC_SLASH, everything else→AC_EXOTIC.
    Unarmed (NONE) is treated as BASH.
    """
    dt = DamageType(dam_type) if not isinstance(dam_type, DamageType) else dam_type
    if dt == DamageType.PIERCE:
        return AC_PIERCE
    if dt == DamageType.BASH or dt == DamageType.NONE:
        return AC_BASH
    if dt == DamageType.SLASH:
        return AC_SLASH
    return AC_EXOTIC


def is_better_ac(ac_a: int, ac_b: int) -> bool:
    """Return True if ac_a is better protection than ac_b (more negative)."""
    return ac_a < ac_b
