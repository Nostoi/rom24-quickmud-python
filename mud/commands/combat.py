from mud import mobprog
from mud.combat import attack_round, multi_hit
from mud.combat.engine import stop_fighting
from mud.skills import skill_registry
import mud.skills.handlers as skill_handlers
from mud.utils import rng_mm
from mud.models.character import Character
from mud.models.constants import OffFlag, convert_flags_from_letters


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
