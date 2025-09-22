from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import ActFlag, Position, LEVEL_IMMORTAL, convert_flags_from_letters
from mud.skills.registry import skill_registry


def _has_practice_flag(entity) -> bool:
    """Return True if the entity advertises ACT_PRACTICE parity semantics."""

    checker = getattr(entity, "has_act_flag", None)
    if callable(checker):
        try:
            return bool(checker(ActFlag.PRACTICE))
        except TypeError:
            pass

    act_value = getattr(entity, "act", None)
    if act_value is not None:
        try:
            return bool(ActFlag(act_value) & ActFlag.PRACTICE)
        except ValueError:
            pass

    flags = getattr(entity, "act_flags", None)
    if isinstance(flags, ActFlag):
        return bool(flags & ActFlag.PRACTICE)
    if isinstance(flags, int):
        return bool(ActFlag(flags) & ActFlag.PRACTICE)
    if isinstance(flags, str):
        return bool(convert_flags_from_letters(flags, ActFlag) & ActFlag.PRACTICE)
    return False


def _is_awake(entity) -> bool:
    """Mirror ROM Position gating for practice trainers."""

    position = getattr(entity, "position", Position.STANDING)
    try:
        pos_value = Position(position)
    except ValueError:
        pos_value = Position.STANDING
    return pos_value > Position.SLEEPING


def _find_practice_trainer(char: Character):
    """Locate an awake practice trainer in the character's room."""

    room = getattr(char, "room", None)
    if room is None:
        return None

    for occupant in getattr(room, "people", []):
        if occupant is char:
            continue
        if not _has_practice_flag(occupant):
            continue
        if not _is_awake(occupant):
            continue
        return occupant
    return None


def _rating_for_class(skill, ch_class: int) -> int:
    """Return the ROM rating entry for the character's class, defaulting to 1."""

    rating = getattr(skill, "rating", {})
    if isinstance(rating, dict):
        if ch_class in rating:
            return int(rating[ch_class])
        key = str(ch_class)
        if key in rating:
            return int(rating[key])
    return 1


def do_practice(char: Character, args: str) -> str:
    """ROM-aligned practice command with trainer, rating, and INT scaling."""

    args = (args or "").strip()
    if not args:
        return f"You have {char.practice} practice sessions left."
    if char.is_npc:
        return ""
    if not char.is_awake():
        return "In your dreams, or what?"

    if char.practice <= 0:
        return "You have no practice sessions left."

    skill_name = args.lower()
    skill = skill_registry.skills.get(skill_name)
    if skill is None:
        return "You can't practice that."

    current = char.skills.get(skill_name)
    if current is None:
        return "You can't practice that."

    levels = getattr(skill, "levels", None)
    required_level = None
    if isinstance(levels, (list, tuple)) and levels:
        try:
            idx = int(getattr(char, "ch_class", 0) or 0)
        except Exception:
            idx = 0
        try:
            required_level = int(levels[idx])
        except (ValueError, TypeError, IndexError):
            required_level = None
    if required_level is not None:
        if required_level >= LEVEL_IMMORTAL:
            return "You can't practice that."
        if current <= 0 and char.level < required_level:
            return "You can't practice that."

    rating = _rating_for_class(skill, char.ch_class)
    if rating <= 0:
        return "You can't practice that."

    trainer = _find_practice_trainer(char)
    if trainer is None and getattr(char, "room", None) is not None:
        return "You can't do that here."

    adept = char.skill_adept_cap()
    if current >= adept:
        return f"You are already learned at {skill_name}."

    gain_rate = char.get_int_learn_rate()
    increment = max(1, gain_rate // max(1, rating))

    char.practice -= 1
    new_value = min(adept, current + increment)
    char.skills[skill_name] = new_value

    if new_value >= adept:
        return f"You are now learned at {skill_name}."
    return f"You practice {skill_name}."


def do_train(char: Character, args: str) -> str:
    """Simplified ROM train command for stats and resource pools."""

    if not args:
        return f"You have {char.train} training sessions left."
    if char.train <= 0:
        return "You have no training sessions left."

    stat = args.lower()
    if stat not in {"hp", "mana", "move"}:
        return "Train what?"

    if stat == "hp":
        char.max_hit += 10
    elif stat == "mana":
        char.max_mana += 10
    else:
        char.max_move += 10

    char.train -= 1
    return f"You train your {stat}."
