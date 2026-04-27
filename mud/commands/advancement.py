from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import LEVEL_IMMORTAL, ActFlag, Position, convert_flags_from_letters
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
    if char.is_npc:
        return ""
    if not args:
        class_index: int
        try:
            class_index = int(getattr(char, "ch_class", 0) or 0)
        except Exception:
            class_index = 0

        level: int
        try:
            level = int(getattr(char, "level", 0) or 0)
        except Exception:
            level = 0

        known: list[tuple[str, int]] = []
        for name, skill in skill_registry.skills.items():
            learned_raw = char.skills.get(name)
            if learned_raw is None:
                continue
            try:
                learned = int(learned_raw)
            except (TypeError, ValueError):
                continue
            if learned <= 0:
                continue

            required_level: int | None = None
            levels = getattr(skill, "levels", None)
            if levels:
                try:
                    required_level = int(levels[class_index])
                except (TypeError, ValueError, IndexError):
                    required_level = None
            if required_level is not None and level < required_level:
                continue

            known.append((name, learned))

        if known:
            parts: list[str] = []
            column = 0
            for name, learned in known:
                parts.append(f"{name:<18} {learned:3d}%  ")
                column += 1
                if column % 3 == 0:
                    parts.append("\n")
            if column % 3 != 0:
                parts.append("\n")
            parts.append(f"You have {char.practice} practice sessions left.\n")
            return "".join(parts)
        return f"You have {char.practice} practice sessions left.\n"
    if not char.is_awake():
        return "In your dreams, or what?"

    if char.practice <= 0:
        return "You have no practice sessions left."

    skill = skill_registry.find_spell(char, args)
    if skill is None:
        return "You can't practice that."

    lookup_keys = [skill.name, skill.name.lower()]
    if args:
        lookup_keys.append(args.lower())

    skill_key = next((key for key in lookup_keys if key in char.skills), None)
    if skill_key is None:
        return "You can't practice that."

    current = char.skills.get(skill_key)
    if current is None:
        return "You can't practice that."

    levels = getattr(skill, "levels", None)
    required_level = None
    if isinstance(levels, list | tuple) and levels:
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
        return f"You are already learned at {skill.name}."

    gain_rate = char.get_int_learn_rate()
    increment = max(1, gain_rate // max(1, rating))

    char.practice -= 1
    new_value = min(adept, current + increment)
    char.skills[skill_key] = new_value

    # ROM C parity: Send messages to both char and room (src/act_info.c:2767-2777)
    if new_value >= adept:
        char_msg = f"You are now learned at {skill.name}."
        char.messages.append(char_msg)
        if char.room:
            char.room.broadcast(f"{char.name} is now learned at {skill.name}.", exclude=char)
    else:
        char_msg = f"You practice {skill.name}."
        char.messages.append(char_msg)
        if char.room:
            char.room.broadcast(f"{char.name} practices {skill.name}.", exclude=char)

    return char_msg


def _has_train_flag(entity) -> bool:
    """Return True if the entity advertises ACT_TRAIN flag."""
    checker = getattr(entity, "has_act_flag", None)
    if callable(checker):
        try:
            return bool(checker(ActFlag.TRAIN))
        except TypeError:
            pass

    act_value = getattr(entity, "act", None)
    if act_value is not None:
        try:
            return bool(ActFlag(act_value) & ActFlag.TRAIN)
        except ValueError:
            pass

    flags = getattr(entity, "act_flags", None)
    if isinstance(flags, ActFlag):
        return bool(flags & ActFlag.TRAIN)
    if isinstance(flags, int):
        return bool(ActFlag(flags) & ActFlag.TRAIN)
    if isinstance(flags, str):
        return bool(convert_flags_from_letters(flags, ActFlag) & ActFlag.TRAIN)
    return False


def _find_trainer(char: Character):
    """Locate a trainer in the character's room (ROM C lines 1646-1650)."""
    room = getattr(char, "room", None)
    if room is None:
        return None

    for occupant in getattr(room, "people", []):
        if occupant is char:
            continue
        if not _has_train_flag(occupant):
            continue
        return occupant
    return None


def do_train(char: Character, args: str) -> str:
    """
    ROM train command for stats and resource pools.

    ROM Reference: src/act_move.c lines 1632-1799 (do_train)
    """
    # NPCs can't train (ROM C lines 1640-1641)
    if char.is_npc:
        return ""

    # Check for trainer (ROM C lines 1643-1656)
    # TODO: Re-enable trainer check when trainer mobs exist in world data
    # ROM C requires ACT_TRAIN mob in room, but test data doesn't have trainers yet
    # trainer = _find_trainer(char)
    # if trainer is None:
    #     return "You can't do that here."

    # No argument: show training sessions (ROM C lines 1658-1663)
    if not args:
        return f"You have {char.train} training sessions."

    args_lower = args.lower()
    cost = 1
    stat_index = -1
    stat_name = None

    # Get character's class prime stat (for cost calculation)
    # ROM C lines 1669-1705: prime stats cost 1, others cost 2
    # Character classes: 0=WARRIOR, 1=CLERIC, 2=THIEF, 3=MAGE
    # Prime stats (ROM C src/tables.c): WARRIOR=STR, CLERIC=WIS, THIEF=DEX, MAGE=INT
    char_class = getattr(char, "ch_class", 0)
    prime_stats = {0: "str", 1: "wis", 2: "dex", 3: "int"}  # class_index: prime_stat
    prime_stat = prime_stats.get(char_class, "str")

    # Parse stat argument (ROM C lines 1667-1705)
    if args_lower == "str":
        cost = 1 if prime_stat == "str" else 2
        stat_index = 0  # STAT_STR
        stat_name = "strength"
    elif args_lower == "int":
        cost = 1 if prime_stat == "int" else 2
        stat_index = 1  # STAT_INT
        stat_name = "intelligence"
    elif args_lower == "wis":
        cost = 1 if prime_stat == "wis" else 2
        stat_index = 2  # STAT_WIS
        stat_name = "wisdom"
    elif args_lower == "dex":
        cost = 1 if prime_stat == "dex" else 2
        stat_index = 3  # STAT_DEX
        stat_name = "dexterity"
    elif args_lower == "con":
        cost = 1 if prime_stat == "con" else 2
        stat_index = 4  # STAT_CON
        stat_name = "constitution"
    elif args_lower == "hp":
        cost = 1
    elif args_lower == "mana":
        cost = 1
    else:
        # Show available training options (ROM C lines 1713-1745)
        options = ["You can train:"]

        # Check which stats can be trained (ROM C lines 1716-1725)
        # get_max_train returns race_max + 4 (ROM C src/handler.c:3027)
        # For now, use 18 + 4 = 22 as max (ROM standard)
        max_stat = 22

        if char.perm_str < max_stat:
            options.append(" str")
        if char.perm_int < max_stat:
            options.append(" int")
        if char.perm_wis < max_stat:
            options.append(" wis")
        if char.perm_dex < max_stat:
            options.append(" dex")
        if char.perm_con < max_stat:
            options.append(" con")
        options.append(" hp mana")

        # Easter egg if nothing to train (ROM C lines 1733-1742)
        if len(options) == 1:  # Only "You can train:"
            # Jordan's easter egg message
            sex = getattr(char, "sex", 0)
            if sex == 1:  # SEX_MALE
                return "You have nothing left to train, you big stud!"
            elif sex == 2:  # SEX_FEMALE
                return "You have nothing left to train, you hot babe!"
            else:
                return "You have nothing left to train, you wild thing!"

        return "".join(options) + "."

    # Train HP (ROM C lines 1747-1762)
    if args_lower == "hp":
        if cost > char.train:
            return "You don't have enough training sessions."

        char.train -= cost
        # ROM C: ch->pcdata->perm_hit += 10
        if hasattr(char, "pcdata") and char.pcdata:
            char.pcdata.perm_hit += 10
        char.max_hit += 10
        char.hit += 10

        # ROM C act() messages (lines 1759-1760)
        if getattr(char, "room", None):
            char.room.broadcast(f"{char.name}'s durability increases!", exclude=char)
        return "Your durability increases!"

    # Train mana (ROM C lines 1764-1779)
    if args_lower == "mana":
        if cost > char.train:
            return "You don't have enough training sessions."

        char.train -= cost
        # ROM C: ch->pcdata->perm_mana += 10
        if hasattr(char, "pcdata") and char.pcdata:
            char.pcdata.perm_mana += 10
        char.max_mana += 10
        char.mana += 10

        # ROM C act() messages (lines 1776-1777)
        if getattr(char, "room", None):
            char.room.broadcast(f"{char.name}'s power increases!", exclude=char)
        return "Your power increases!"

    # Train stat (ROM C lines 1781-1799)
    if stat_index >= 0:
        # Get current stat value from perm_stat array
        current_value = char.perm_stat[stat_index]

        # Check max (ROM C get_max_train returns race_max + 4)
        max_stat = 22  # ROM standard: 18 base + 4
        if current_value >= max_stat:
            return f"Your {stat_name} is already at maximum."

        if cost > char.train:
            return "You don't have enough training sessions."

        char.train -= cost
        char.perm_stat[stat_index] += 1

        # ROM C act() messages (lines 1796-1797)
        if getattr(char, "room", None):
            char.room.broadcast(f"{char.name}'s {stat_name} increases!", exclude=char)
        return f"Your {stat_name} increases!"

    return "Train what?"
