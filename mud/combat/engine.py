from __future__ import annotations

from mud import mobprog
from mud.affects.saves import _check_immune as _riv_check
from mud.affects.saves import saves_spell
from mud.config import COMBAT_USE_THAC0
from mud.math.c_compat import c_div, urange
from mud.models.character import Character
from mud.models.constants import (
    AC_BASH,
    AC_EXOTIC,
    AC_PIERCE,
    AC_SLASH,
    WEAPON_FLAMING,
    WEAPON_FROST,
    WEAPON_POISON,
    WEAPON_SHOCKING,
    WEAPON_VAMPIRIC,
    AffectFlag,
    DamageType,
    Position,
    WeaponType,
    attack_damage_type,
)
from mud.utils import rng_mm
from mud.skills import check_improve


HAND_TO_HAND_SKILL = "hand to hand"

WEAPON_SKILL_BY_TYPE: dict[WeaponType, str] = {
    WeaponType.SWORD: "sword",
    WeaponType.DAGGER: "dagger",
    WeaponType.SPEAR: "spear",
    WeaponType.MACE: "mace",
    WeaponType.AXE: "axe",
    WeaponType.FLAIL: "flail",
    WeaponType.WHIP: "whip",
    WeaponType.POLEARM: "polearm",
}


def get_wielded_weapon(attacker: Character | None):
    """Return the currently wielded weapon for an attacker."""

    if attacker is None:
        return None

    wield = getattr(attacker, "wielded_weapon", None)
    if wield is not None:
        return wield

    equipment = getattr(attacker, "equipment", None)
    if isinstance(equipment, dict):
        for slot in ("wield", "weapon", "main_hand", "primary"):
            candidate = equipment.get(slot)
            if candidate is not None:
                return candidate
    return None


def _weapon_values(weapon) -> list[int]:
    values = getattr(weapon, "value", None)
    if values is None and hasattr(weapon, "prototype"):
        values = getattr(weapon.prototype, "value", None)
    if isinstance(values, (list, tuple)):
        return [int(v) for v in values]
    return []


def _weapon_type(weapon) -> WeaponType | None:
    values = _weapon_values(weapon)
    if not values:
        return None
    try:
        return WeaponType(int(values[0]))
    except (ValueError, TypeError):
        return None


def _weapon_attack_index(weapon) -> int:
    values = _weapon_values(weapon)
    if len(values) > 3:
        try:
            return int(values[3])
        except (TypeError, ValueError):
            return 0
    return 0


def _weapon_is_new_format(weapon) -> bool:
    if hasattr(weapon, "new_format"):
        return bool(getattr(weapon, "new_format"))
    if hasattr(weapon, "prototype") and hasattr(weapon.prototype, "new_format"):
        return bool(getattr(weapon.prototype, "new_format"))
    return False


def _weapon_level(weapon) -> int:
    if hasattr(weapon, "level"):
        try:
            return int(getattr(weapon, "level"))
        except (TypeError, ValueError):
            return 0
    if hasattr(weapon, "prototype") and hasattr(weapon.prototype, "level"):
        try:
            return int(getattr(weapon.prototype, "level"))
        except (TypeError, ValueError):
            return 0
    return 0


def _is_weapon(weapon) -> bool:
    item_type = getattr(weapon, "item_type", None)
    if isinstance(item_type, str):
        if item_type.lower() == "weapon":
            return True
    if hasattr(weapon, "prototype"):
        proto_type = getattr(weapon.prototype, "item_type", None)
        if isinstance(proto_type, str) and proto_type.lower() == "weapon":
            return True
    return False


def _has_shield_equipped(attacker: Character) -> bool:
    has_attr = getattr(attacker, "has_shield_equipped", None)
    if has_attr is not None:
        return bool(has_attr)
    equipment = getattr(attacker, "equipment", None)
    if isinstance(equipment, dict):
        return equipment.get("shield") is not None
    return False


def get_weapon_sn(attacker: Character, weapon=None) -> str | None:
    """Return the weapon skill name for the attacker's wielded weapon."""

    weapon = weapon if weapon is not None else get_wielded_weapon(attacker)
    if weapon is None or not _is_weapon(weapon):
        return HAND_TO_HAND_SKILL

    wtype = _weapon_type(weapon)
    if wtype is None:
        return None
    if wtype == WeaponType.EXOTIC:
        return None
    return WEAPON_SKILL_BY_TYPE.get(wtype, HAND_TO_HAND_SKILL)


def _lookup_skill_percent(attacker: Character, skill_name: str) -> int:
    skills = getattr(attacker, "skills", {})
    if not isinstance(skills, dict):
        return 0
    lowered = skill_name.lower()
    for key, value in skills.items():
        try:
            if str(key).lower() != lowered:
                continue
            percent = int(value)
        except (TypeError, ValueError):
            continue
        return max(0, min(100, percent))
    return 0


def _get_skill_percent(attacker: Character, skill_name: str, fallback_attr: str | None = None) -> int:
    """Return the learned percentage for a skill with optional attribute fallback."""

    percent = _lookup_skill_percent(attacker, skill_name)
    if percent <= 0 and fallback_attr is not None:
        fallback_val = getattr(attacker, fallback_attr, None)
        if fallback_val is not None:
            try:
                percent = int(fallback_val)
            except (TypeError, ValueError):
                percent = 0
    return max(0, min(100, percent))


def _push_message(character: Character | None, message: str) -> None:
    if character is None:
        return
    mailbox = getattr(character, "messages", None)
    if isinstance(mailbox, list):
        mailbox.append(message)


def get_weapon_skill(attacker: Character, weapon_sn: str | None) -> int:
    """Return the attacker's proficiency for the given weapon skill."""

    level = int(getattr(attacker, "level", 0) or 0)
    if weapon_sn is None:
        return max(0, min(100, 3 * level))

    if getattr(attacker, "is_npc", False):
        if weapon_sn == HAND_TO_HAND_SKILL:
            return max(0, min(100, 40 + 2 * level))
        return max(0, min(100, 40 + (5 * level) // 2))

    return _lookup_skill_percent(attacker, weapon_sn)


def multi_hit(attacker: Character, victim: Character, dt: int = None) -> list[str]:
    """Perform multiple attacks following ROM multi_hit mechanics.

    Returns a list of attack result messages.
    """
    results: list[str] = []

    # ROM wait/daze timer decrements for non-player characters
    # PULSE_VIOLENCE is typically 3 in ROM
    PULSE_VIOLENCE = 3
    if not hasattr(attacker, "desc") or attacker.desc is None:
        attacker.wait = max(0, getattr(attacker, "wait", 0) - PULSE_VIOLENCE)
        attacker.daze = max(0, getattr(attacker, "daze", 0) - PULSE_VIOLENCE)

    # Position check - no attacks if position too low
    if attacker.position < Position.RESTING:
        return results

    # First attack always happens
    result = attack_round(attacker, victim)
    results.append(result)

    # Check if victim died or combat ended
    if victim.position == Position.DEAD or not hasattr(attacker, "fighting") or attacker.fighting != victim:
        return results

    # Haste gives extra attack
    if getattr(attacker, "has_affect", None) and attacker.has_affect(AffectFlag.HASTE):
        result = attack_round(attacker, victim)
        results.append(result)
        if victim.position == Position.DEAD or not hasattr(attacker, "fighting") or attacker.fighting != victim:
            return results

    # Skip extra attacks for backstab
    if dt and getattr(dt, "name", "") == "backstab":
        return results

    # Second attack skill check
    second_attack_skill = getattr(attacker, "second_attack_skill", 0)
    if second_attack_skill > 0:
        chance = second_attack_skill // 2

        # Slow reduces chances
        if getattr(attacker, "has_affect", None) and attacker.has_affect(AffectFlag.SLOW):
            chance //= 2

        if rng_mm.number_percent() < chance:
            result = attack_round(attacker, victim)
            results.append(result)
            # In ROM, would call check_improve here
            if victim.position == Position.DEAD or not hasattr(attacker, "fighting") or attacker.fighting != victim:
                return results

    # Third attack skill check
    third_attack_skill = getattr(attacker, "third_attack_skill", 0)
    if third_attack_skill > 0:
        chance = third_attack_skill // 4

        # Slow prevents third attack entirely
        if getattr(attacker, "has_affect", None) and attacker.has_affect(AffectFlag.SLOW):
            chance = 0

        if rng_mm.number_percent() < chance:
            result = attack_round(attacker, victim)
            results.append(result)
            # In ROM, would call check_improve here

    if getattr(attacker, "is_npc", False):
        mobprog.mp_fight_trigger(attacker, victim)
        mobprog.mp_hprct_trigger(attacker, victim)

    return results


def attack_round(attacker: Character, victim: Character) -> str:
    """Resolve a single attack round.

    The attacker attempts to hit the victim.  Hit chance is derived from a
    base 50% modified by the attacker's ``hitroll``.  Successful hits apply
    ``damroll`` damage.  Living combatants are placed into FIGHTING position.
    If the victim dies, they are removed from the room and their position set
    to ``DEAD``.
    """

    # Capture victim's pre-attack position for ROM-like modifiers
    _victim_pos_before = victim.position

    wield = get_wielded_weapon(attacker)
    weapon_sn = get_weapon_sn(attacker, wield)
    weapon_skill = get_weapon_skill(attacker, weapon_sn)
    skill_total = 20 + weapon_skill
    if skill_total <= 0:
        skill_total = 1

    attack_index = attacker.dam_type or 0
    if wield is not None:
        attack_index = _weapon_attack_index(wield)
    dam_type_lookup = attack_damage_type(attack_index)
    dam_type = int(dam_type_lookup) if dam_type_lookup is not None else int(DamageType.BASH)
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

    # ROM AC clamping for very negative values
    if victim_ac < -15:
        victim_ac = c_div(victim_ac + 15, 5) - 15

    if COMBAT_USE_THAC0:
        # ROM diceroll using number_bits(5) until < 20
        while True:
            diceroll = rng_mm.number_bits(5)
            if diceroll < 20:
                break
        # Compute class-based thac0 with hitroll/skill contributions
        th = compute_thac0(attacker.level, attacker.ch_class, hitroll=attacker.hitroll, skill=skill_total)
        vac = c_div(victim_ac, 10)
        # Miss if nat 0 or (not 19 and diceroll < thac0 - victim_ac)
        if diceroll == 0 or (diceroll != 19 and diceroll < (th - vac)):
            # Handle miss - still set fighting positions
            _handle_miss_fighting_state(attacker, victim)
            return f"You miss {victim.name}."
    else:
        # Percent model kept for parity stability outside feature flag
        to_hit = 50 + attacker.hitroll
        # Use C-style division for negative AC to match ROM semantics
        to_hit += c_div(victim_ac, 2)
        to_hit = urange(5, to_hit, 100)
        if rng_mm.number_percent() > to_hit:
            # Handle miss - still set fighting positions
            _handle_miss_fighting_state(attacker, victim)
            return f"You miss {victim.name}."

    # Hit determined - calculate weapon damage following C src/fight.c:one_hit logic
    damage = calculate_weapon_damage(attacker, victim, dam_type, wield=wield, skill=skill_total)

    # Apply damage reduction modifiers (sanctuary, protection, drunk) following C src/fight.c:damage logic
    damage = apply_damage_reduction(attacker, victim, damage)

    # Apply RIV (IMMUNE/RESIST/VULN) scaling before any side-effects.
    riv = _riv_check(victim, dam_type)
    if riv == 1:  # IS_IMMUNE
        damage = 0
    elif riv == 2:  # IS_RESISTANT: dam -= dam/3 (ROM)
        damage = damage - c_div(damage, 3)
    elif riv == 3:  # IS_VULNERABLE: dam += dam/2 (ROM)
        damage = damage + c_div(damage, 2)

    # Invoke any on-hit effects with scaled damage (can be monkeypatched in tests).
    on_hit_effects(attacker, victim, damage)

    # Process weapon special attacks following C src/fight.c:one_hit L600-680
    weapon_special_messages = process_weapon_special_attacks(attacker, victim)

    # Apply damage and update fighting state (defenses checked inside apply_damage)
    main_message = apply_damage(attacker, victim, damage, dam_type)

    # Combine main attack message with weapon special messages
    if weapon_special_messages:
        return main_message + " " + " ".join(weapon_special_messages)
    return main_message


def apply_damage(attacker: Character, victim: Character, damage: int, dam_type: int = None) -> str:
    """Apply damage and manage fighting state following C src/fight.c:damage logic.

    Handles:
    - Defense checks (parry, dodge, shield_block) - ROM checks these AFTER hit but BEFORE damage
    - Damage application and hit point reduction
    - Position updates based on remaining hit points
    - Fighting state management (set_fighting, stop_fighting)
    - Position change messaging
    - Death handling

    Args:
        attacker: Character dealing damage
        victim: Character receiving damage
        damage: Final damage amount after all reductions
        dam_type: Damage type for defense checks

    Returns:
        Combat message describing the result
    """
    if victim.position == Position.DEAD:
        return "Already dead."

    # Check for parry, dodge, and shield block following C src/fight.c:damage() order
    # These are checked AFTER hit determination but BEFORE damage application
    # Order is critical: shield_block → parry → dodge (per ROM C src/fight.c:one_hit)
    if dam_type is not None and attacker != victim:
        if check_shield_block(attacker, victim):
            return f"{victim.name} blocks your attack with a shield."
        if check_parry(attacker, victim):
            return f"{victim.name} parries your attack."
        if check_dodge(attacker, victim):
            return f"{victim.name} dodges your attack."

    # Set up fighting state if not already fighting
    if victim != attacker:
        # Victim starts fighting back if able
        if victim.position > Position.STUNNED:
            if victim.fighting is None:
                set_fighting(victim, attacker)
                if getattr(victim, "is_npc", False):
                    mobprog.mp_kill_trigger(victim, attacker)
            # Update victim to fighting position if timer allows
            if getattr(victim, "timer", 0) <= 4:
                victim.position = Position.FIGHTING

        # Attacker starts fighting if not already
        if victim.position > Position.STUNNED:
            if attacker.fighting is None:
                set_fighting(attacker, victim)

    # Apply damage
    old_pos = victim.position
    victim.hit -= damage

    # Immortals don't die (ROM IS_IMMORTAL check)
    if not victim.is_npc and victim.is_immortal() and victim.hit < 1:
        victim.hit = 1

    # Update position based on hit points
    update_pos(victim)

    # Handle position change messages
    message = ""
    if victim.position != old_pos:
        message = _position_change_message(victim, old_pos)

    # Stop fighting if unconscious
    if not is_awake(victim):
        stop_fighting(victim, False)

    # Handle death
    if victim.position == Position.DEAD:
        if getattr(victim, "is_npc", False):
            old_pos = victim.position
            victim.position = Position.STANDING
            try:
                mobprog.mp_death_trigger(victim, attacker)
            finally:
                victim.position = old_pos
        message = _handle_death(attacker, victim)
        return message

    # Regular hit messages
    if damage == 0:
        return "Your attack has no effect."
    elif damage > victim.max_hit // 4:
        return f"You hit {victim.name} for {damage} damage. That really did HURT!"
    elif victim.hit < victim.max_hit // 4:
        return f"You hit {victim.name} for {damage} damage. {victim.name} is BLEEDING!"
    else:
        return f"You hit {victim.name} for {damage} damage."


def set_fighting(ch: Character, victim: Character) -> None:
    """Start fighting following C src/fight.c:set_fighting logic.

    Sets ch->fighting = victim and ch->position = POS_FIGHTING.
    Strips sleep affect if present.
    """
    if ch.fighting is not None:
        # In ROM this would be a bug() call, but we'll handle gracefully
        return

    # Strip sleep affect if present
    if ch.has_affect(AffectFlag.SLEEP):
        ch.strip_affect("sleep")  # TODO: implement affect system

    ch.fighting = victim
    ch.position = Position.FIGHTING


def stop_fighting(ch: Character, both: bool = True) -> None:
    """Stop fighting following C src/fight.c:stop_fighting logic.

    Args:
        ch: Character to stop fighting
        both: If True, also stop anyone fighting ch
    """
    # Stop ch from fighting
    ch.fighting = None
    ch.position = getattr(ch, "default_pos", Position.STANDING) if getattr(ch, "is_npc", False) else Position.STANDING
    update_pos(ch)

    # Stop others from fighting ch if both=True
    if both:
        # In a full implementation, this would iterate char_list
        # For now, we'll handle the basic case
        pass


def update_pos(victim: Character) -> None:
    """Update character position based on hit points following C src/fight.c:update_pos logic."""
    if victim.hit > 0:
        if victim.position <= Position.STUNNED:
            victim.position = Position.STANDING
        return

    # NPCs die immediately when hit <= 0
    if getattr(victim, "is_npc", True) and victim.hit < 1:
        victim.position = Position.DEAD
        return

    # PC death thresholds
    if victim.hit <= -11:
        victim.position = Position.DEAD
    elif victim.hit <= -6:
        victim.position = Position.MORTAL
    elif victim.hit <= -3:
        victim.position = Position.INCAP
    else:
        victim.position = Position.STUNNED


def is_awake(character: Character) -> bool:
    """ROM IS_AWAKE macro: position > POS_SLEEPING"""
    return character.position > Position.SLEEPING


def _position_change_message(victim: Character, old_pos: Position) -> str:
    """Generate position change message following ROM logic."""
    if victim.position == Position.MORTAL:
        if hasattr(victim, "room") and victim.room is not None:
            victim.room.broadcast(
                f"{victim.name} is mortally wounded, and will die soon, if not aided.",
                exclude=victim,
            )
        return "You are mortally wounded, and will die soon, if not aided."
    elif victim.position == Position.INCAP:
        if hasattr(victim, "room") and victim.room is not None:
            victim.room.broadcast(
                f"{victim.name} is incapacitated and will slowly die, if not aided.",
                exclude=victim,
            )
        return "You are incapacitated and will slowly die, if not aided."
    elif victim.position == Position.STUNNED:
        if hasattr(victim, "room") and victim.room is not None:
            victim.room.broadcast(f"{victim.name} is stunned, but will probably recover.", exclude=victim)
        return "You are stunned, but will probably recover."
    elif victim.position == Position.DEAD:
        if hasattr(victim, "room") and victim.room is not None:
            victim.room.broadcast(f"{victim.name} is DEAD!!!", exclude=victim)
        return "You have been KILLED!!"
    return ""


def _handle_miss_fighting_state(attacker: Character, victim: Character) -> None:
    """Handle fighting state setup on miss following ROM logic."""
    if victim != attacker:
        # Victim starts fighting back if able
        if victim.position > Position.STUNNED:
            if victim.fighting is None:
                set_fighting(victim, attacker)
            # Update victim to fighting position if timer allows
            if getattr(victim, "timer", 0) <= 4:
                victim.position = Position.FIGHTING

        # Attacker starts fighting if not already
        if victim.position > Position.STUNNED:
            if attacker.fighting is None:
                set_fighting(attacker, victim)


def _handle_death(attacker: Character, victim: Character) -> str:
    """Handle character death following ROM logic."""
    # Clear fighting state
    attacker.fighting = None
    victim.fighting = None
    attacker.position = Position.STANDING

    # Broadcast death message
    if hasattr(victim, "room") and victim.room is not None:
        victim.room.broadcast(f"{victim.name} is DEAD!!!", exclude=victim)
        victim.room.remove_character(victim)

    return f"You kill {victim.name}."


def calculate_weapon_damage(
    attacker: Character,
    victim: Character,
    dam_type: int,
    *,
    wield=None,
    skill: int | None = None,
) -> int:
    """Calculate weapon damage following C src/fight.c:one_hit logic.

    This includes:
    - Weapon dice rolling with skill modifiers
    - Shield bonus (11/10 multiplier when no shield equipped)
    - Sharpness weapon effect
    - Enhanced damage skill
    - Position-based multipliers (sleeping/resting victims)
    - Damroll bonus application
    """
    if wield is None:
        wield = get_wielded_weapon(attacker)

    if skill is None:
        weapon_sn = get_weapon_sn(attacker, wield)
        weapon_skill = get_weapon_skill(attacker, weapon_sn)
        skill_total = 20 + weapon_skill
    else:
        skill_total = int(skill)

    if skill_total <= 0:
        skill_total = 1

    # Base damage calculation
    if wield is not None and _is_weapon(wield):
        # Weapon damage from dice
        values = _weapon_values(wield)
        if _weapon_is_new_format(wield) and len(values) > 2:
            dice_number = max(0, values[1])
            dice_type = max(0, values[2])
            dam = rng_mm.dice(dice_number, dice_type) * skill_total // 100
        else:
            min_val = values[1] if len(values) > 1 else 0
            max_val = values[2] if len(values) > 2 else 0
            min_dam = min_val * skill_total // 100
            max_dam = max_val * skill_total // 100
            dam = rng_mm.number_range(min_dam, max_dam)

        # Shield bonus - no shield equipped gives 11/10 multiplier
        if not _has_shield_equipped(attacker):
            dam = c_div(dam * 11, 10)

        # Sharpness weapon effect
        if hasattr(wield, "weapon_stats") and "sharp" in wield.weapon_stats:
            percent = rng_mm.number_percent()
            if percent <= (skill_total // 8):
                dam = 2 * dam + (dam * 2 * percent // 100)
    else:
        # Unarmed damage from ROM C: number_range(1 + 4*skill/100, 2*ch->level/3*skill/100)
        # This is the exact ROM formula from src/fight.c:556-557
        min_dam = 1 + (4 * skill_total // 100)
        max_dam = (2 * attacker.level // 3) * skill_total // 100
        # ROM allows max_dam to be less than min_dam for very low levels
        dam = rng_mm.number_range(min_dam, max_dam)

    # Enhanced damage skill
    enhanced_damage_skill = getattr(attacker, "enhanced_damage_skill", 0)
    if enhanced_damage_skill > 0:
        diceroll = rng_mm.number_percent()
        if diceroll <= enhanced_damage_skill:
            # check_improve(attacker, gsn_enhanced_damage, True, 6) would go here
            dam += 2 * (dam * diceroll // 300)

    # Position-based damage multipliers
    # IS_AWAKE in ROM means position > POS_SLEEPING
    if victim.position <= Position.SLEEPING:
        dam *= 2
    elif victim.position < Position.FIGHTING:
        dam = dam * 3 // 2

    # Add damroll bonus - ROM: GET_DAMROLL(ch) * UMIN(100, skill) / 100
    dam += attacker.damroll * min(100, skill_total) // 100

    # Ensure minimum damage - ROM: if (dam <= 0) dam = 1
    if dam <= 0:
        dam = 1

    return dam


def apply_damage_reduction(attacker: Character, victim: Character, damage: int) -> int:
    """Apply damage reduction following C src/fight.c:damage logic.

    Order of reductions (all use C integer division):
    1. Drunk condition: 9/10 damage if victim drunk > 10
    2. Sanctuary: halve damage if victim has sanctuary affect
    3. Protection spells: -25% if victim has protect_evil/good vs opposing alignment

    Args:
        attacker: Character dealing damage
        victim: Character receiving damage
        damage: Base damage before reductions

    Returns:
        Reduced damage amount
    """
    # Drunk condition reduces damage (victim only, PC only)
    if (
        damage > 1
        and victim.pcdata is not None
        and len(victim.pcdata.condition) > 0  # COND_DRUNK = 0
        and victim.pcdata.condition[0] > 10
    ):
        damage = c_div(9 * damage, 10)

    # Sanctuary halves damage
    if damage > 1 and victim.has_affect(AffectFlag.SANCTUARY):
        damage = c_div(damage, 2)

    # Protection spells reduce damage by 25% vs opposing alignment
    if damage > 1:
        victim_protect_evil = victim.has_affect(AffectFlag.PROTECT_EVIL)
        victim_protect_good = victim.has_affect(AffectFlag.PROTECT_GOOD)

        # Check attacker alignment and apply reductions
        if (victim_protect_evil and is_evil(attacker)) or (victim_protect_good and is_good(attacker)):
            damage -= c_div(damage, 4)

    return damage


def is_good(character: Character) -> bool:
    """ROM IS_GOOD macro: alignment >= 350"""
    return character.alignment >= 350


def is_evil(character: Character) -> bool:
    """ROM IS_EVIL macro: alignment <= -350"""
    return character.alignment <= -350


def is_neutral(character: Character) -> bool:
    """ROM IS_NEUTRAL macro: !IS_GOOD && !IS_EVIL"""
    return not is_good(character) and not is_evil(character)


def on_hit_effects(attacker: Character, victim: Character, damage: int) -> None:  # pragma: no cover - default no-op
    """Hook for on-hit side-effects; receives RIV-scaled damage."""
    return None


# --- Defense checks following C src/fight.c logic ---
def check_shield_block(attacker: Character, victim: Character) -> bool:
    """Shield block check following C src/fight.c:check_shield_block logic.

    Requirements:
    - Victim must be awake (position > POS_SLEEPING)
    - Victim must have a shield equipped
    - Base chance = get_skill(victim, gsn_shield_block) / 5 + 3
    - Modified by level difference: chance + victim.level - attacker.level
    """
    if not is_awake(victim):
        return False

    if not _has_shield_equipped(victim):
        return False

    shield_skill = _get_skill_percent(victim, "shield block", "shield_block_skill")
    chance = c_div(shield_skill, 5) + 3

    # Level difference modifier
    chance += victim.level - attacker.level

    if rng_mm.number_percent() >= chance:
        return False

    attacker_name = getattr(attacker, "name", "Someone")
    victim_name = getattr(victim, "name", "Someone")
    _push_message(victim, f"You block {attacker_name}'s attack with your shield.")
    _push_message(attacker, f"{victim_name} blocks your attack with a shield.")
    check_improve(victim, "shield block", True, 6)
    return True


def check_parry(attacker: Character, victim: Character) -> bool:
    """Parry check following C src/fight.c:check_parry logic.

    Requirements:
    - Victim must be awake (position > POS_SLEEPING)
    - Victim should have weapon equipped (NPCs can parry unarmed at half chance)
    - Base chance = get_skill(victim, gsn_parry) / 2
    - Halved if victim can't see attacker
    - Modified by level difference: chance + victim.level - attacker.level
    """
    if not is_awake(victim):
        return False

    parry_skill = _get_skill_percent(victim, "parry", "parry_skill")
    chance = c_div(parry_skill, 2)

    has_weapon = getattr(victim, "has_weapon_equipped", False)
    if not has_weapon:
        if getattr(victim, "is_npc", False):
            chance = c_div(chance, 2)  # NPCs can parry unarmed at half chance
        else:
            return False  # PCs need weapons to parry

    # Visibility modifier
    if not getattr(victim, "can_see", lambda x: True)(attacker):
        chance = c_div(chance, 2)

    # Level difference modifier
    chance += victim.level - attacker.level

    if rng_mm.number_percent() >= chance:
        return False

    attacker_name = getattr(attacker, "name", "Someone")
    victim_name = getattr(victim, "name", "Someone")
    _push_message(victim, f"You parry {attacker_name}'s attack.")
    _push_message(attacker, f"{victim_name} parries your attack.")
    check_improve(victim, "parry", True, 6)
    return True


def check_dodge(attacker: Character, victim: Character) -> bool:
    """Dodge check following C src/fight.c:check_dodge logic.

    Requirements:
    - Victim must be awake (position > POS_SLEEPING)
    - Base chance = get_skill(victim, gsn_dodge) / 2
    - Halved if victim can't see attacker
    - Modified by level difference: chance + victim.level - attacker.level
    """
    if not is_awake(victim):
        return False

    dodge_skill = _get_skill_percent(victim, "dodge", "dodge_skill")
    chance = c_div(dodge_skill, 2)

    # Visibility modifier
    if not getattr(victim, "can_see", lambda x: True)(attacker):
        chance = c_div(chance, 2)

    # Level difference modifier
    chance += victim.level - attacker.level

    if rng_mm.number_percent() >= chance:
        return False

    attacker_name = getattr(attacker, "name", "Someone")
    victim_name = getattr(victim, "name", "Someone")
    _push_message(victim, f"You dodge {attacker_name}'s attack.")
    _push_message(attacker, f"{victim_name} dodges your attack.")
    check_improve(victim, "dodge", True, 6)
    return True


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
    0: (20, 6),  # mage
    1: (20, 2),  # cleric
    2: (20, -4),  # thief
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


def process_weapon_special_attacks(attacker: Character, victim: Character) -> list[str]:
    """Process weapon special attacks following C src/fight.c:one_hit L600-680.

    Applies special weapon effects after a successful hit:
    - WEAPON_POISON: Apply poison affect if save fails
    - WEAPON_VAMPIRIC: Drain life and heal attacker
    - WEAPON_FLAMING: Fire damage
    - WEAPON_FROST: Cold damage
    - WEAPON_SHOCKING: Lightning damage

    Returns list of messages describing special attack effects.
    """
    messages = []

    wield = get_wielded_weapon(attacker)
    if wield is None:
        return messages

    # Check that attacker is still fighting victim (ROM condition)
    if getattr(attacker, "fighting", None) != victim:
        return messages

    # Get weapon flags - support both extra_flags (for ObjIndex) and weapon_flags attribute
    weapon_flags = 0
    if hasattr(wield, "weapon_flags"):
        weapon_flags = wield.weapon_flags
    elif hasattr(wield, "extra_flags"):
        weapon_flags = wield.extra_flags

    weapon_level = _weapon_level(wield) or 1

    # WEAPON_POISON - ROM src/fight.c L600-634
    if weapon_flags & WEAPON_POISON:
        level = weapon_level

        if not saves_spell(level // 2, victim, DamageType.POISON):
            messages.append("You feel poison coursing through your veins.")
            # TODO: Apply poison affect when affect system is implemented
            # af.where = TO_AFFECTS; af.type = gsn_poison; af.level = level * 3 / 4
            # af.duration = level / 2; af.location = APPLY_STR; af.modifier = -1
            # af.bitvector = AFF_POISON; affect_join(victim, &af)

    # WEAPON_VAMPIRIC - ROM src/fight.c L640-649
    if weapon_flags & WEAPON_VAMPIRIC:
        dam = rng_mm.number_range(1, weapon_level // 5 + 1)
        messages.append(f"You feel {getattr(wield, 'name', 'the weapon')} drawing your life away.")

        # Apply vampiric damage (additional negative damage)
        apply_damage(attacker, victim, dam, DamageType.NEGATIVE)

        # Heal attacker by half the damage
        attacker.hit += dam // 2
        if hasattr(attacker, "max_hit"):
            attacker.hit = min(attacker.hit, attacker.max_hit)

        # Shift alignment toward evil (ROM: ch->alignment = UMAX(-1000, ch->alignment - 1))
        if hasattr(attacker, "alignment"):
            attacker.alignment = max(-1000, attacker.alignment - 1)

    # WEAPON_FLAMING - ROM src/fight.c L651-659
    if weapon_flags & WEAPON_FLAMING:
        dam = rng_mm.number_range(1, weapon_level // 4 + 1)
        messages.append(f"{getattr(wield, 'name', 'The weapon')} sears your flesh.")

        # Apply fire damage
        apply_damage(attacker, victim, dam, DamageType.FIRE)
        # TODO: fire_effect((void *) victim, wield->level / 2, dam, TARGET_CHAR) when effects exist

    # WEAPON_FROST - ROM src/fight.c L661-670
    if weapon_flags & WEAPON_FROST:
        dam = rng_mm.number_range(1, weapon_level // 6 + 2)
        messages.append("The cold touch surrounds you with ice.")

        # Apply cold damage
        apply_damage(attacker, victim, dam, DamageType.COLD)
        # TODO: cold_effect(victim, wield->level / 2, dam, TARGET_CHAR) when effects exist

    # WEAPON_SHOCKING - ROM src/fight.c L672-681
    if weapon_flags & WEAPON_SHOCKING:
        dam = rng_mm.number_range(1, weapon_level // 5 + 2)
        messages.append("You are shocked by the weapon.")

        # Apply lightning damage
        apply_damage(attacker, victim, dam, DamageType.LIGHTNING)
        # TODO: shock_effect(victim, wield->level / 2, dam, TARGET_CHAR) when effects exist

    return messages
