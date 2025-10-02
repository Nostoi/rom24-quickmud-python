from mud import mobprog
from mud.combat import attack_round, multi_hit
from mud.combat.engine import apply_damage, get_wielded_weapon, stop_fighting
from mud.config import get_pulse_violence
from mud.skills import skill_registry
import mud.skills.handlers as skill_handlers
from mud.utils import rng_mm
from mud.models.character import Character
from mud.math.c_compat import c_div
from mud.models.constants import (
    AffectFlag,
    DamageType,
    OffFlag,
    Position,
    Stat,
    convert_flags_from_letters,
)
from mud.models.constants import AC_BASH


def do_kill(char: Character, args: str) -> str:
    if not args:
        return "Kill whom?"
    target_name = args.lower()
    if not getattr(char, "room", None):
        return "You are nowhere."
    for victim in list(char.room.people):
        if victim is char:
            continue
        if victim.name and target_name in victim.name.lower():
            return attack_round(char, victim)
    return "They aren't here."


def do_kick(char: Character, args: str) -> str:
    opponent = getattr(char, "fighting", None)
    if opponent is None:
        return "You aren't fighting anyone."

    try:
        skill = skill_registry.get("kick")
    except KeyError:
        skill = None

    if getattr(char, "is_npc", False):
        off_flags_value = getattr(char, "off_flags", 0) or 0
        if isinstance(off_flags_value, str):
            off_flags = convert_flags_from_letters(off_flags_value, OffFlag)
            char.off_flags = int(off_flags)
        else:
            try:
                off_flags = OffFlag(off_flags_value)
            except ValueError:
                off_flags = OffFlag(0)
        if not off_flags & OffFlag.KICK:
            return ""
    elif skill is not None:
        required_level: int | None = None
        levels = getattr(skill, "levels", ())
        if isinstance(levels, (list, tuple)):
            try:
                class_index = int(getattr(char, "ch_class", 0) or 0)
                required_level = int(levels[class_index])
            except (IndexError, TypeError, ValueError):
                required_level = None
        if required_level is not None and getattr(char, "level", 0) < required_level:
            return "You better leave the martial arts to fighters."

    if skill is not None:
        if int(getattr(char, "wait", 0) or 0) > 0:
            char.messages.append("You are still recovering.")
            return "You are still recovering."

        lag = skill_registry._compute_skill_lag(char, skill)
        skill_registry._apply_wait_state(char, lag)

        cooldowns = getattr(char, "cooldowns", {})
        cooldowns["kick"] = skill.cooldown
        char.cooldowns = cooldowns
    roll = rng_mm.number_percent()
    try:
        learned = getattr(char, "skills", {}).get("kick", 0)
        chance = max(0, min(100, int(learned)))
    except (TypeError, ValueError):
        chance = 0
    success = chance > roll

    message = skill_handlers.kick(char, opponent, success=success, roll=roll)

    if skill is not None:
        skill_registry._check_improve(char, skill, "kick", success)

    return message


def _find_room_target(char: Character, name: str) -> Character | None:
    room = getattr(char, "room", None)
    if room is None or not name:
        return None

    lowered = name.lower()
    for candidate in getattr(room, "people", []) or []:
        if candidate is char:
            continue
        candidate_name = getattr(candidate, "name", "") or ""
        if lowered in candidate_name.lower():
            return candidate
    return None


def _character_skill_percent(char: Character, skill_name: str) -> int:
    skills = getattr(char, "skills", {}) or {}
    try:
        raw = skills.get(skill_name, 0)
        return max(0, min(100, int(raw)))
    except (TypeError, ValueError):
        return 0


def do_backstab(char: Character, args: str) -> str:
    target_name = (args or "").strip()
    if not target_name:
        return "Backstab whom?"

    if getattr(char, "fighting", None) is not None:
        return "You're facing the wrong end."

    victim = _find_room_target(char, target_name)
    if victim is None:
        return "They aren't here."

    if victim is char:
        return "How can you sneak up on yourself?"

    if getattr(victim, "hit", 0) < c_div(getattr(victim, "max_hit", 0), 3):
        return f"{victim.name} is hurt and suspicious ... you can't sneak up."

    try:
        skill = skill_registry.get("backstab")
    except KeyError:
        skill = None

    learned = _character_skill_percent(char, "backstab")
    if not getattr(char, "is_npc", False) and (skill is None or learned <= 0):
        return "You don't know how to backstab."

    if get_wielded_weapon(char) is None:
        return "You need to wield a weapon to backstab."

    if int(getattr(char, "wait", 0) or 0) > 0:
        char.messages.append("You are still recovering.")
        return "You are still recovering."

    roll = rng_mm.number_percent()
    auto_success = learned >= 2 and hasattr(victim, "is_awake") and not victim.is_awake()
    success = learned > roll or auto_success

    if skill is not None:
        lag = skill_registry._compute_skill_lag(char, skill)
        skill_registry._apply_wait_state(char, lag)
        cooldowns = getattr(char, "cooldowns", {})
        cooldowns["backstab"] = skill.cooldown
        char.cooldowns = cooldowns

    if success:
        message = skill_handlers.backstab(char, victim)
    else:
        message = apply_damage(char, victim, 0, int(DamageType.NONE))

    if skill is not None:
        skill_registry._check_improve(char, skill, "backstab", success)

    return message


def do_bash(char: Character, args: str) -> str:
    try:
        skill = skill_registry.get("bash")
    except KeyError:
        skill = None

    learned = _character_skill_percent(char, "bash")
    if not getattr(char, "is_npc", False) and (skill is None or learned <= 0):
        return "Bashing? What's that?"

    target_name = (args or "").strip()
    victim: Character | None
    if target_name:
        victim = _find_room_target(char, target_name)
        if victim is None:
            return "They aren't here."
    else:
        victim = getattr(char, "fighting", None)
        if victim is None:
            return "But you aren't fighting anyone!"

    if victim is char:
        return "You try to bash your brains out, but fail."

    if getattr(victim, "position", Position.STANDING) < Position.FIGHTING:
        return "You'll have to let them get back up first."

    if int(getattr(char, "wait", 0) or 0) > 0:
        char.messages.append("You are still recovering.")
        return "You are still recovering."

    chance = learned
    if getattr(char, "is_npc", False) and chance <= 0:
        chance = 100

    # Carry weight modifiers
    chance += c_div(int(getattr(char, "carry_weight", 0) or 0), 250)
    chance -= c_div(int(getattr(victim, "carry_weight", 0) or 0), 200)

    # Size differentials
    char_size = int(getattr(char, "size", 0) or 0)
    victim_size = int(getattr(victim, "size", 0) or 0)
    if char_size < victim_size:
        chance += (char_size - victim_size) * 15
    else:
        chance += (char_size - victim_size) * 10

    # Strength vs dexterity
    char_str = char.get_curr_stat(Stat.STR) or 0
    victim_dex = victim.get_curr_stat(Stat.DEX) or 0
    chance += char_str
    chance -= c_div(victim_dex * 4, 3)

    # Armor class (bash index)
    victim_ac = 0
    armor = getattr(victim, "armor", None)
    if isinstance(armor, (list, tuple)) and len(armor) > AC_BASH:
        try:
            victim_ac = int(armor[AC_BASH])
        except (TypeError, ValueError):
            victim_ac = 0
    chance -= c_div(victim_ac, 25)

    # Speed modifiers
    off_flags_val = getattr(char, "off_flags", 0)
    if isinstance(off_flags_val, str):
        char_flags = convert_flags_from_letters(off_flags_val, OffFlag)
    else:
        try:
            char_flags = OffFlag(off_flags_val)
        except ValueError:
            char_flags = OffFlag(0)
    char_fast = (
        (getattr(char, "has_affect", None) and char.has_affect(AffectFlag.HASTE))
        or bool(char_flags & OffFlag.FAST)
    )
    if char_fast:
        chance += 10

    victim_off = getattr(victim, "off_flags", 0)
    if isinstance(victim_off, str):
        victim_flags = convert_flags_from_letters(victim_off, OffFlag)
    else:
        try:
            victim_flags = OffFlag(victim_off)
        except ValueError:
            victim_flags = OffFlag(0)
    victim_fast = (
        (getattr(victim, "has_affect", None) and victim.has_affect(AffectFlag.HASTE))
        or bool(victim_flags & OffFlag.FAST)
    )
    if victim_fast:
        chance -= 30

    # Level difference
    chance += int(getattr(char, "level", 0) or 0) - int(getattr(victim, "level", 0) or 0)

    # Defender dodge mitigation for PCs
    if not getattr(victim, "is_npc", False):
        victim_dodge = _character_skill_percent(victim, "dodge")
        if chance < victim_dodge:
            chance -= 3 * (victim_dodge - chance)

    roll = rng_mm.number_percent()
    success = roll < chance

    lag_pulses = 0
    if skill is not None:
        lag_pulses = skill_registry._compute_skill_lag(char, skill)
        cooldowns = getattr(char, "cooldowns", {})
        cooldowns["bash"] = skill.cooldown
        char.cooldowns = cooldowns

    if success:
        if lag_pulses:
            skill_registry._apply_wait_state(char, lag_pulses)
        message = skill_handlers.bash(char, victim, success=True, chance=chance)
    else:
        base = lag_pulses if lag_pulses else int(getattr(skill, "lag", 0) or 0)
        failure_lag = max(1, c_div(base * 3, 2)) if base else 1
        skill_registry._apply_wait_state(char, failure_lag)
        char.position = Position.RESTING
        message = skill_handlers.bash(char, victim, success=False)

    if skill is not None:
        skill_registry._check_improve(char, skill, "bash", success)

    return message


def do_berserk(char: Character, args: str) -> str:
    try:
        skill = skill_registry.get("berserk")
    except KeyError:
        skill = None

    learned = _character_skill_percent(char, "berserk")
    if getattr(char, "is_npc", False):
        off_flags_value = getattr(char, "off_flags", 0) or 0
        if isinstance(off_flags_value, str):
            off_flags = convert_flags_from_letters(off_flags_value, OffFlag)
            char.off_flags = int(off_flags)
        else:
            try:
                off_flags = OffFlag(off_flags_value)
            except ValueError:
                off_flags = OffFlag(0)
        if not off_flags & OffFlag.BERSERK:
            return ""
    elif skill is None or learned <= 0:
        return "You turn red in the face, but nothing happens."

    if getattr(char, "is_npc", False) and learned <= 0:
        learned = 100

    if char.has_spell_effect("berserk") or char.has_affect(AffectFlag.BERSERK):
        return "You get a little madder."

    if char.has_affect(AffectFlag.CALM):
        return "You're feeling too mellow to berserk."

    if getattr(char, "mana", 0) < 50:
        return "You can't get up enough energy."

    if int(getattr(char, "wait", 0) or 0) > 0:
        char.messages.append("You are still recovering.")
        return "You are still recovering."

    roll = rng_mm.number_percent()
    hp_max = max(1, int(getattr(char, "max_hit", 1) or 1))
    hp_percent = c_div(int(getattr(char, "hit", 0) or 0) * 100, hp_max)
    chance = learned
    if getattr(char, "position", Position.STANDING) == Position.FIGHTING:
        chance += 10
    chance += 25 - c_div(hp_percent, 2)
    success = roll < chance

    cooldowns = getattr(char, "cooldowns", {})
    cooldowns["berserk"] = getattr(skill, "cooldown", 0) if skill is not None else 0
    char.cooldowns = cooldowns

    if success:
        wait = get_pulse_violence()
        skill_registry._apply_wait_state(char, wait)
        char.mana -= 50
        char.move = c_div(int(getattr(char, "move", 0) or 0), 2)
        char.hit = min(hp_max, int(getattr(char, "hit", 0) or 0) + 2 * int(getattr(char, "level", 0) or 0))
        applied = skill_handlers.berserk(char)
        if not applied:
            # Already berserk somehow; treat as failure state.
            success = False
        message = "Your pulse races as you are consumed by rage!"
    else:
        wait = max(1, 3 * get_pulse_violence())
        skill_registry._apply_wait_state(char, wait)
        char.mana -= 25
        char.move = c_div(int(getattr(char, "move", 0) or 0), 2)
        message = "Your pulse speeds up, but nothing happens."

    if skill is not None:
        skill_registry._check_improve(char, skill, "berserk", success, multiplier=2)

    return message


def do_surrender(char: Character, args: str) -> str:
    opponent = getattr(char, "fighting", None)
    if opponent is None:
        return "But you're not fighting!"

    stop_fighting(char, True)
    if getattr(opponent, "fighting", None) is char:
        opponent.fighting = None

    if not getattr(char, "is_npc", False) and getattr(opponent, "is_npc", False):
        if not mobprog.mp_surr_trigger(opponent, char):
            multi_hit(opponent, char)

    return "You surrender."
