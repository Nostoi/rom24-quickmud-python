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
from mud.math.c_compat import c_div
from mud.affects.saves import _check_immune as _riv_check
from mud.math.c_compat import urange
from mud.models.constants import AffectFlag
from mud.config import COMBAT_USE_THAC0


def attack_round(attacker: Character, victim: Character) -> str:
    """Resolve a single attack round.

    The attacker attempts to hit the victim.  Hit chance is derived from a
    base 50% modified by the attacker's ``hitroll``.  Successful hits apply
    ``damroll`` damage.  Living combatants are placed into FIGHTING position.
    If the victim dies, they are removed from the room and their position set
    to ``DEAD``.
    """

    attacker.position = Position.FIGHTING
    # Capture victim's pre-attack position for ROM-like modifiers
    _victim_pos_before = victim.position
    victim.position = Position.FIGHTING

    dam_type = attacker.dam_type or int(DamageType.BASH)
    ac_idx = ac_index_for_dam_type(dam_type)
    victim_ac = 0
    if hasattr(victim, "armor") and 0 <= ac_idx < len(victim.armor):
        victim_ac = victim.armor[ac_idx]
    # Visibility and position modifiers (ROM-inspired)
    if getattr(victim, "has_affect", None) and victim.has_affect(AffectFlag.INVISIBLE):
        victim_ac -= 4
    if _victim_pos_before < Position.FIGHTING:
        victim_ac += 4
    if _victim_pos_before < Position.RESTING:
        victim_ac += 6

    if COMBAT_USE_THAC0:
        # ROM diceroll using number_bits(5) until < 20
        while True:
            diceroll = rng_mm.number_bits(5)
            if diceroll < 20:
                break
        # Compute class-based thac0 with hitroll/skill contributions
        th = compute_thac0(attacker.level, attacker.ch_class, hitroll=attacker.hitroll, skill=100)
        vac = c_div(victim_ac, 10)
        # Miss if nat 0 or (not 19 and diceroll < thac0 - victim_ac)
        if diceroll == 0 or (diceroll != 19 and diceroll < (th - vac)):
            return f"You miss {victim.name}."
    else:
        # Percent model kept for parity stability outside feature flag
        to_hit = 50 + attacker.hitroll
        # Use C-style division for negative AC to match ROM semantics
        to_hit += c_div(victim_ac, 2)
        to_hit = urange(5, to_hit, 100)
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
    # Apply RIV (IMMUNE/RESIST/VULN) scaling before any side-effects.
    dam_type = attacker.dam_type or int(DamageType.BASH)
    riv = _riv_check(victim, dam_type)
    if riv == 1:  # IS_IMMUNE
        damage = 0
    elif riv == 2:  # IS_RESISTANT: dam -= dam/3 (ROM)
        damage = damage - c_div(damage, 3)
    elif riv == 3:  # IS_VULNERABLE: dam += dam/2 (ROM)
        damage = damage + c_div(damage, 2)

    # Invoke any on-hit effects with scaled damage (can be monkeypatched in tests).
    on_hit_effects(attacker, victim, damage)
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


def on_hit_effects(attacker: Character, victim: Character, damage: int) -> None:  # pragma: no cover - default no-op
    """Hook for on-hit side-effects; receives RIV-scaled damage."""
    return None


# --- Defense checks (override in tests as needed) ---
def check_shield_block(attacker: Character, victim: Character) -> bool:
    """Basic shield block chance using victim.shield_block_chance (percent).

    Defaults to 0 if not set. Uses rng_mm.number_percent() ≤ chance.
    """
    chance = getattr(victim, "shield_block_chance", 0) or 0
    if chance <= 0:
        return False
    return rng_mm.number_percent() <= chance


def check_parry(attacker: Character, victim: Character) -> bool:
    """Basic parry chance using victim.parry_chance (percent)."""
    chance = getattr(victim, "parry_chance", 0) or 0
    if chance <= 0:
        return False
    return rng_mm.number_percent() <= chance


def check_dodge(attacker: Character, victim: Character) -> bool:
    """Basic dodge chance using victim.dodge_chance (percent)."""
    chance = getattr(victim, "dodge_chance", 0) or 0
    if chance <= 0:
        return False
    return rng_mm.number_percent() <= chance


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


# --- THAC0 interpolation (ROM-inspired) ---
# Class ids align with FMANA mapping used elsewhere: 0:mage, 1:cleric, 2:thief, 3:warrior
THAC0_TABLE: dict[int, tuple[int, int]] = {
    0: (20, 6),    # mage
    1: (20, 2),    # cleric
    2: (20, -4),   # thief
    3: (20, -10),  # warrior
}


def interpolate(level: int, v00: int, v32: int) -> int:
    """ROM-like integer interpolate between level 0 and 32 using C division."""
    return v00 + c_div((v32 - v00) * level, 32)


def compute_thac0(level: int, ch_class: int, *, hitroll: int = 0, skill: int = 100) -> int:
    """Compute THAC0 following ROM fight.c adjustments.

    - interpolate(level, thac0_00, thac0_32)
    - if thac0 < 0: thac0 = thac0 / 2 (C div)
    - if thac0 < -5: thac0 = -5 + (thac0 + 5)/2 (C div)
    - thac0 -= hitroll * skill / 100
    - thac0 += 5 * (100 - skill) / 100
    """
    t00, t32 = THAC0_TABLE.get(ch_class, (20, 6))
    th = interpolate(level, t00, t32)
    if th < 0:
        th = c_div(th, 2)
    if th < -5:
        th = -5 + c_div(th + 5, 2)
    th -= c_div(hitroll * skill, 100)
    th += c_div(5 * (100 - skill), 100)
    return th
