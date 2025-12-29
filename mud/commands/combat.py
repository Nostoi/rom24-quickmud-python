import mud.skills.handlers as skill_handlers
from mud import mobprog
from mud.characters import is_clan_member, is_same_group
from mud.combat import attack_round, multi_hit
from mud.combat.engine import apply_damage, check_killer, get_wielded_weapon, stop_fighting
from mud.config import get_pulse_violence
from mud.math.c_compat import c_div
from mud.models.character import Character
from mud.models.constants import (
    AC_BASH,
    ActFlag,
    AffectFlag,
    DamageType,
    OffFlag,
    PlayerFlag,
    Position,
    RoomFlag,
    Stat,
    LEVEL_IMMORTAL,
    convert_flags_from_letters,
)
from mud.skills import skill_registry
from mud.utils import rng_mm


def _kill_safety_message(attacker: Character, victim: Character) -> str | None:
    victim_room = getattr(victim, "room", None)
    attacker_room = getattr(attacker, "room", None)
    if victim_room is None or attacker_room is None:
        return "They aren't here."

    if getattr(victim, "fighting", None) is attacker or victim is attacker:
        return None

    if (
        hasattr(attacker, "is_immortal")
        and attacker.is_immortal()
        and skill_handlers._coerce_int(getattr(attacker, "level", 0)) > LEVEL_IMMORTAL
    ):
        return None

    if skill_handlers._is_charmed(attacker) and getattr(attacker, "master", None) is victim:
        victim_name = getattr(victim, "name", None) or "Someone"
        return f"{victim_name} is your beloved master."

    victim_is_npc = bool(getattr(victim, "is_npc", True))

    if victim_is_npc:
        room_flags = skill_handlers._get_room_flags(victim_room)
        if room_flags & int(RoomFlag.ROOM_SAFE):
            return "Not in this room."

        if skill_handlers._has_shop(victim):
            return "The shopkeeper wouldn't like that."

        act_flags = skill_handlers._get_act_flags(victim)
        if act_flags & (ActFlag.TRAIN | ActFlag.PRACTICE | ActFlag.IS_HEALER | ActFlag.IS_CHANGER):
            return "I don't think Mota would approve."

        if not getattr(attacker, "is_npc", False):
            if act_flags & ActFlag.PET:
                victim_name = getattr(victim, "name", "they") or "they"
                return f"But {victim_name} looks so cute and cuddly..."
            if skill_handlers._is_charmed(victim) and getattr(victim, "master", None) is not attacker:
                return "You don't own that monster."
    else:
        if getattr(attacker, "is_npc", False):
            if skill_handlers._is_charmed(attacker):
                master = getattr(attacker, "master", None)
                if master is not None and getattr(master, "fighting", None) is not victim:
                    return "Players are your friends!"
            if skill_handlers._get_room_flags(victim_room) & int(RoomFlag.ROOM_SAFE):
                return "Not in this room."
        else:
            if not is_clan_member(attacker):
                return "Join a clan if you want to kill players."

            player_flags = skill_handlers._get_player_flags(victim)
            if player_flags & (PlayerFlag.KILLER | PlayerFlag.THIEF):
                return None

            if not is_clan_member(victim):
                return "They aren't in a clan, leave them alone."

            attacker_level = skill_handlers._coerce_int(getattr(attacker, "level", 0))
            victim_level = skill_handlers._coerce_int(getattr(victim, "level", 0))
            if attacker_level > victim_level + 8:
                return "Pick on someone your own size."

    return None


def do_kill(char: Character, args: str) -> str:
    target_name = (args or "").strip()
    if not target_name:
        return "Kill whom?"
    if not getattr(char, "room", None):
        return "You are nowhere."

    victim = _find_room_target(char, target_name)
    if victim is None:
        return "They aren't here."

    if victim is char:
        char.send_to_char("You hit yourself.  Ouch!")
        multi_hit(char, char)
        return "You hit yourself.  Ouch!"

    safety_message = _kill_safety_message(char, victim)
    if safety_message:
        return safety_message

    if getattr(victim, "fighting", None) is not None and not is_same_group(char, victim.fighting):
        return "Kill stealing is not permitted."

    if getattr(char, "position", Position.STANDING) == Position.FIGHTING:
        return "You do the best you can!"

    skill_registry._apply_wait_state(char, get_pulse_violence())
    check_killer(char, victim)
    return attack_round(char, victim)


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
        if isinstance(levels, list | tuple):
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


def do_rescue(char: Character, args: str) -> str:
    target_name = (args or "").strip()
    if not target_name:
        return "Rescue whom?"

    room = getattr(char, "room", None)
    if room is None:
        return "You are nowhere."

    victim = _find_room_target(char, target_name)
    if victim is None:
        return "They aren't here."

    if victim is char:
        return "What about fleeing instead?"

    if not getattr(char, "is_npc", False) and getattr(victim, "is_npc", False):
        return "Doesn't need your help!"

    if getattr(char, "fighting", None) is victim:
        return "Too late."

    opponent = getattr(victim, "fighting", None)
    if opponent is None:
        return "That person is not fighting right now."

    if getattr(opponent, "is_npc", False) and not is_same_group(char, victim):
        return "Kill stealing is not permitted."

    if int(getattr(char, "wait", 0) or 0) > 0:
        char.messages.append("You are still recovering.")
        return "You are still recovering."

    try:
        skill = skill_registry.get("rescue")
    except KeyError:
        skill = None

    lag = 12
    if skill is not None:
        lag = skill_registry._compute_skill_lag(char, skill)
    skill_registry._apply_wait_state(char, lag)

    cooldowns = getattr(char, "cooldowns", {})
    cooldowns["rescue"] = getattr(skill, "cooldown", 0) if skill is not None else 0
    char.cooldowns = cooldowns

    roll = rng_mm.number_percent()
    learned = _character_skill_percent(char, "rescue")
    success = roll <= learned

    if not success:
        char.messages.append("You fail the rescue.")
        if skill is not None:
            skill_registry._check_improve(char, skill, "rescue", False)
        return "You fail the rescue."

    message = skill_handlers.rescue(char, victim, opponent=opponent)
    if skill is not None:
        skill_registry._check_improve(char, skill, "rescue", True)
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
    if isinstance(armor, list | tuple) and len(armor) > AC_BASH:
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
    char_fast = (getattr(char, "has_affect", None) and char.has_affect(AffectFlag.HASTE)) or bool(
        char_flags & OffFlag.FAST
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
    victim_fast = (getattr(victim, "has_affect", None) and victim.has_affect(AffectFlag.HASTE)) or bool(
        victim_flags & OffFlag.FAST
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
    """
    Surrender to opponent, ending combat.

    ROM Reference: src/fight.c do_surrender (lines 3222-3242)

    Allows a character to yield to their opponent. If surrendering to an NPC,
    the NPC's TRIG_SURR mobprog is triggered if present. By default, NPCs
    ignore surrender and continue attacking.
    """
    # Must be fighting (ROM fight.c:3225-3229)
    opponent = getattr(char, "fighting", None)
    if opponent is None:
        return "But you're not fighting!\n\r"

    # Messages (ROM fight.c:3230-3232)
    opponent_name = getattr(opponent, "name", "someone")
    messages = [f"You surrender to {opponent_name}!"]

    # Stop fighting (ROM fight.c:3233 - stop_fighting(ch, TRUE))
    stop_fighting(char, True)
    if getattr(opponent, "fighting", None) is char:
        opponent.fighting = None

    # Check for TRIG_SURR mobprog if player surrendering to NPC
    # ROM fight.c:3235-3241
    if not getattr(char, "is_npc", False) and getattr(opponent, "is_npc", False):
        # Try to trigger surrender mobprog
        if not mobprog.mp_surr_trigger(opponent, char):
            # No mobprog or mobprog didn't handle it - NPC ignores and attacks
            messages.append(f"{opponent_name} seems to ignore your cowardly act!")
            # ROM: multi_hit(mob, ch, TYPE_UNDEFINED)
            attack_messages = multi_hit(opponent, char)
            if attack_messages:
                messages.extend(attack_messages)

    return "\n".join(messages) if len(messages) > 1 else messages[0]


def do_flee(char: Character, args: str) -> str:
    """
    Flee from combat.

    ROM Reference: src/fight.c lines 800-900 (do_flee)
    """
    opponent = getattr(char, "fighting", None)
    if opponent is None:
        return "You aren't fighting anyone."

    # Can't flee if position too low
    if char.position < Position.FIGHTING:
        return "You can't flee in your current state."

    # Check wait state
    if int(getattr(char, "wait", 0) or 0) > 0:
        char.messages.append("You are still recovering.")
        return "You are still recovering."

    # Set wait state for flee attempt
    skill_registry._apply_wait_state(char, get_pulse_violence())

    # Success chance based on dexterity
    if hasattr(char, "get_curr_stat"):
        dex = char.get_curr_stat(Stat.DEX)
    else:
        dex = 13  # Default dex

    if dex is None:
        dex = 13

    chance = 50 + (dex - 13) * 5  # Base 50%, +/- 5% per dex point

    # Reduce chance if badly hurt
    hp_percent = c_div(int(getattr(char, "hit", 0) or 0) * 100, max(1, int(getattr(char, "max_hit", 1) or 1)))
    if hp_percent < 30:
        chance -= 25

    roll = rng_mm.number_percent()
    if roll > chance:
        return "PANIC! You couldn't escape!"

    # Find a random exit
    room = getattr(char, "room", None)
    if not room:
        return "PANIC! You couldn't escape!"

    exits = getattr(room, "exits", {})
    valid_exits = []

    for direction, exit_data in exits.items():
        if exit_data:
            # Handle both dict-style and Exit object style
            if hasattr(exit_data, "exit_info"):
                # Exit object
                closed = bool(getattr(exit_data, "exit_info", 0) & 1)  # EX_ISDOOR and closed
                to_room = getattr(exit_data, "to_room", None)
            elif isinstance(exit_data, dict):
                # Dict style
                closed = exit_data.get("closed", False)
                to_room = exit_data.get("to_room")
            else:
                continue

            if not closed and to_room:
                valid_exits.append((direction, to_room))

    if not valid_exits:
        return "PANIC! You couldn't escape!"

    # Pick random exit
    direction, to_room = valid_exits[rng_mm.number_range(0, len(valid_exits) - 1)]

    # Move character
    messages = []
    messages.append(f"You flee from combat!")

    # Notify others in room
    for other in getattr(room, "characters", []):
        if other != char:
            try:
                desc = getattr(other, "desc", None)
                if desc and hasattr(desc, "send"):
                    desc.send(f"{char.name} has fled!")
            except Exception:
                pass

    # Stop fighting
    stop_fighting(char, True)

    # Move to new room
    try:
        from mud.registry import room_registry

        new_room = room_registry.get(to_room)

        if new_room:
            if room and hasattr(room, "characters") and char in room.characters:
                room.characters.remove(char)

            char.room = new_room
            new_room.characters.append(char)

            # Show new room
            from mud.commands.inspection import do_look

            room_desc = do_look(char, "")
            messages.append(room_desc)
    except Exception as e:
        messages.append(f"Flee failed: {e}")

    # Lose some movement
    char.move = max(0, char.move - c_div(char.max_move, 10))

    return "\n".join(messages)


def do_cast(char: Character, args: str) -> str:
    """
    Cast a spell.

    ROM Reference: src/magic.c lines 50-150 (do_cast)
    """
    args = args.strip()

    if not args:
        return "Cast which what where?"

    # Parse spell name and target
    parts = args.split(None, 1)
    spell_name = parts[0].lower()
    target_name = parts[1] if len(parts) > 1 else ""

    # Check if character knows the spell
    skills = getattr(char, "skills", {})
    if spell_name not in skills:
        return "You don't know any spells of that name."

    spell_level = skills.get(spell_name, 0)
    if spell_level <= 0:
        return "You don't know that spell well enough."

    # Check position
    if char.position < Position.FIGHTING:
        return "You can't concentrate enough."

    # Check mana
    # Spell mana cost is typically level-based
    char_level = int(getattr(char, "level", 1) or 1)
    mana_cost = max(5, char_level)  # Simple cost formula

    if getattr(char, "mana", 0) < mana_cost:
        return "You don't have enough mana."

    # Check wait state
    if int(getattr(char, "wait", 0) or 0) > 0:
        char.messages.append("You are still recovering.")
        return "You are still recovering."

    # Try to cast
    try:
        from mud.skills import skill_registry

        skill = skill_registry.get(spell_name)
    except (ImportError, KeyError):
        return f"The spell '{spell_name}' is not implemented yet."

    # Determine target
    target = char  # Default to self
    if target_name:
        # Try to find target in room
        room = getattr(char, "room", None)
        if room:
            target_lower = target_name.lower()
            for candidate in getattr(room, "characters", []):
                candidate_name = getattr(candidate, "name", "").lower()
                if target_lower in candidate_name:
                    target = candidate
                    break

    # Deduct mana
    char.mana -= mana_cost

    # Set lag
    skill_registry._apply_wait_state(char, get_pulse_violence())

    # Try to cast the spell
    roll = rng_mm.number_percent()
    success = roll <= spell_level

    if not success:
        char.mana = max(0, char.mana - c_div(mana_cost, 2))  # Lose half mana on failure
        return "You lost your concentration."

    # Execute spell
    try:
        spell_func = getattr(skill, "handler", None)
        if spell_func and callable(spell_func):
            result = spell_func(char, target, spell_level)
            skill_registry._check_improve(char, skill, spell_name, success)
            return result if result else f"You cast {spell_name}."
        else:
            return f"The spell '{spell_name}' is not fully implemented yet."
    except Exception as e:
        return f"Spell cast failed: {e}"


def do_dirt(char: Character, args: str) -> str:
    """
    Kick dirt in opponent's eyes to blind them.

    ROM Reference: src/fight.c do_dirt (lines 2489-2640)
    """
    target_name = (args or "").strip()

    # Check if character has the skill
    skill_level = char.skills.get("dirt kicking", 0)
    if skill_level == 0:
        return "You get your feet dirty."

    # Find target
    if not target_name:
        victim = getattr(char, "fighting", None)
        if victim is None:
            return "But you aren't in combat!"
    else:
        victim = _find_room_target(char, target_name)
        if victim is None:
            return "They aren't here."

    # Check if already blinded
    victim_affected = getattr(victim, "affected_by", 0)
    if victim_affected & AffectFlag.BLIND:
        return "They're already blinded."

    if victim is char:
        return "Very funny."

    # Safety checks
    safety_msg = _kill_safety_message(char, victim)
    if safety_msg:
        return safety_msg

    # Calculate chance
    chance = skill_level
    char_dex = skill_handlers._coerce_int(
        getattr(char, "perm_stat", [13] * 5)[1] if isinstance(getattr(char, "perm_stat", []), list) else 13
    )
    victim_dex = skill_handlers._coerce_int(
        getattr(victim, "perm_stat", [13] * 5)[1] if isinstance(getattr(victim, "perm_stat", []), list) else 13
    )
    chance += char_dex - 2 * victim_dex

    # Level modifier
    char_level = skill_handlers._coerce_int(getattr(char, "level", 1))
    victim_level = skill_handlers._coerce_int(getattr(victim, "level", 1))
    chance += (char_level - victim_level) * 2

    # Roll
    if rng_mm.number_percent() < chance:
        # Success - blind the victim
        victim.affected_by = victim_affected | AffectFlag.BLIND
        skill_registry._apply_wait_state(char, get_pulse_violence())

        # Start combat if not already fighting
        if not getattr(char, "fighting", None):
            char.fighting = victim
        if not getattr(victim, "fighting", None):
            victim.fighting = char

        check_killer(char, victim)
        return f"You kick dirt into {getattr(victim, 'name', 'their')} eyes!"
    else:
        skill_registry._apply_wait_state(char, get_pulse_violence())
        return "You kick dirt but miss their eyes."


def do_trip(char: Character, args: str) -> str:
    """
    Trip opponent to knock them down.

    ROM Reference: src/fight.c do_trip (lines 2641-2760)
    """
    target_name = (args or "").strip()

    # Check if character has the skill
    skill_level = char.skills.get("trip", 0)
    if skill_level == 0:
        return "Tripping? What's that?"

    # Find target
    if not target_name:
        victim = getattr(char, "fighting", None)
        if victim is None:
            return "But you aren't fighting anyone!"
    else:
        victim = _find_room_target(char, target_name)
        if victim is None:
            return "They aren't here."

    # Safety checks
    safety_msg = _kill_safety_message(char, victim)
    if safety_msg:
        return safety_msg

    # Can't trip flying targets
    victim_affected = getattr(victim, "affected_by", 0)
    if victim_affected & AffectFlag.FLYING:
        return "Their feet aren't on the ground."

    # Can't trip someone already down
    victim_pos = getattr(victim, "position", Position.STANDING)
    if victim_pos < Position.FIGHTING:
        return "They are already down."

    if victim is char:
        skill_registry._apply_wait_state(char, get_pulse_violence() * 2)
        return "You fall flat on your face!"

    # Calculate chance
    chance = skill_level

    # Size modifier
    char_size = skill_handlers._coerce_int(getattr(char, "size", 2))
    victim_size = skill_handlers._coerce_int(getattr(victim, "size", 2))
    if char_size < victim_size:
        chance += (char_size - victim_size) * 10

    # Dex modifier
    char_dex = skill_handlers._coerce_int(
        getattr(char, "perm_stat", [13] * 5)[1] if isinstance(getattr(char, "perm_stat", []), list) else 13
    )
    victim_dex = skill_handlers._coerce_int(
        getattr(victim, "perm_stat", [13] * 5)[1] if isinstance(getattr(victim, "perm_stat", []), list) else 13
    )
    chance += char_dex - victim_dex * 3 // 2

    # Level modifier
    char_level = skill_handlers._coerce_int(getattr(char, "level", 1))
    victim_level = skill_handlers._coerce_int(getattr(victim, "level", 1))
    chance += (char_level - victim_level) * 2

    # Roll
    if rng_mm.number_percent() < chance:
        # Success
        victim.position = Position.RESTING
        skill_registry._apply_wait_state(char, get_pulse_violence())
        skill_registry._apply_wait_state(victim, get_pulse_violence() * 2)

        # Damage
        damage_amt = rng_mm.number_range(2, 2 + 2 * victim_size + skill_level // 20)
        apply_damage(char, victim, damage_amt, DamageType.BASH)

        check_killer(char, victim)
        return f"You trip {getattr(victim, 'name', 'them')} and they go down!"
    else:
        skill_registry._apply_wait_state(char, get_pulse_violence())
        return "You try to trip them but miss."


def do_disarm(char: Character, args: str) -> str:
    """
    Attempt to disarm opponent's weapon.

    ROM Reference: src/fight.c do_disarm (lines 3145-3220)
    """
    # Check if character has the skill
    skill_level = char.skills.get("disarm", 0)
    if skill_level == 0:
        return "You don't know how to disarm opponents."

    # Must be fighting
    victim = getattr(char, "fighting", None)
    if victim is None:
        return "You aren't fighting anyone."

    # Victim must be wielding a weapon
    victim_equipped = getattr(victim, "equipped", {})
    victim_weapon = victim_equipped.get("wield") or victim_equipped.get("main_hand")
    if victim_weapon is None:
        return "Your opponent is not wielding a weapon."

    # Attacker should have weapon (or hand-to-hand skill)
    char_equipped = getattr(char, "equipped", {})
    char_weapon = char_equipped.get("wield") or char_equipped.get("main_hand")
    hth_skill = char.skills.get("hand to hand", 0)

    if char_weapon is None and hth_skill == 0:
        return "You must wield a weapon to disarm."

    # Calculate chance
    if char_weapon is None:
        chance = skill_level * hth_skill // 150
    else:
        chance = skill_level

    # Dex vs Str
    char_dex = skill_handlers._coerce_int(
        getattr(char, "perm_stat", [13] * 5)[1] if isinstance(getattr(char, "perm_stat", []), list) else 13
    )
    victim_str = skill_handlers._coerce_int(
        getattr(victim, "perm_stat", [13] * 5)[0] if isinstance(getattr(victim, "perm_stat", []), list) else 13
    )
    chance += char_dex - 2 * victim_str

    # Level modifier
    char_level = skill_handlers._coerce_int(getattr(char, "level", 1))
    victim_level = skill_handlers._coerce_int(getattr(victim, "level", 1))
    chance += (char_level - victim_level) * 2

    skill_registry._apply_wait_state(char, get_pulse_violence())

    # Roll
    if rng_mm.number_percent() < chance:
        # Success - remove weapon from victim
        if "wield" in victim_equipped:
            del victim_equipped["wield"]
        elif "main_hand" in victim_equipped:
            del victim_equipped["main_hand"]

        # Drop to room
        victim_room = getattr(victim, "room", None)
        if victim_room and hasattr(victim_room, "contents"):
            victim_room.contents.append(victim_weapon)
            victim_weapon.in_room = victim_room

        check_killer(char, victim)
        return f"You disarm {getattr(victim, 'name', 'them')}!"
    else:
        return f"You fail to disarm {getattr(victim, 'name', 'them')}."
