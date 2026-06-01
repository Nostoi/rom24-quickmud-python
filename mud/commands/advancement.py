from __future__ import annotations

from mud.math.c_compat import c_div
from mud.models.character import Character
from mud.models.constants import LEVEL_IMMORTAL, ActFlag, convert_flags_from_letters
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
        if not occupant.is_awake():
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
    # mirrors ROM src/act_info.c:2772-2774 — raw `int_app[INT].learn / rating`
    # with NO UMAX(1,...) guard. When learn < rating the integer division
    # rounds to 0 and learned[sn] does not change, even though practice is
    # still decremented. The `rating > 0` check above (act_info.c:2752-2755)
    # guarantees the divisor is positive. (Closes ARITH-010.)
    increment = c_div(gain_rate, rating)

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
        # mirroring ROM src/act_move.c:1648 — IS_NPC(mob) && IS_SET(mob->act,
        # ACT_TRAIN). The NPC guard matters because PC `act` holds PlayerFlag
        # bits that can alias ACT_TRAIN (0x200).
        if not getattr(occupant, "is_npc", False):
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

    # Check for trainer (ROM C lines 1643-1656) — an ACT_TRAIN NPC must be
    # present in the room, else "You can't do that here." This gate precedes
    # both the no-arg session display and any stat/resource handling. TRAIN-003.
    if _find_trainer(char) is None:
        return "You can't do that here."

    # No argument: show training sessions (ROM C lines 1658-1663). ROM prints
    # the session count, then sets `argument = "foo"` and FALLS THROUGH — "foo"
    # matches no stat/hp/mana, so control reaches the listing branch (`:1713`)
    # and the player also sees "You can train: ...". We mirror that by emitting
    # the session-count line as a prefix and continuing with args = "foo".
    # TRAIN-005.
    session_prefix = ""
    if not args:
        session_prefix = f"You have {char.train} training sessions.\n"
        args = "foo"

    args_lower = args.lower()
    # mirroring ROM src/act_move.c do_train — `cost = 1;` is set once before
    # the stat dispatch and never changed: every `if (attr_prime == STAT_X)
    # cost = 1;` branch is a no-op and there is NO `else cost = 2;`. So
    # training ANY stat (prime or not) and hp/mana always costs exactly 1
    # training session. (Earlier QuickMUD invented a cost=2 for non-prime
    # stats; that was a misread of the no-op branches — see TRAIN-002.)
    cost = 1
    stat_index = -1
    stat_name = None

    # Parse stat argument (ROM C lines 1667-1705)
    if args_lower == "str":
        stat_index = 0  # STAT_STR
        stat_name = "strength"
    elif args_lower == "int":
        stat_index = 1  # STAT_INT
        stat_name = "intelligence"
    elif args_lower == "wis":
        stat_index = 2  # STAT_WIS
        stat_name = "wisdom"
    elif args_lower == "dex":
        stat_index = 3  # STAT_DEX
        stat_name = "dexterity"
    elif args_lower == "con":
        stat_index = 4  # STAT_CON
        stat_name = "constitution"
    elif args_lower == "hp":
        cost = 1
    elif args_lower == "mana":
        cost = 1
    else:
        # Show available training options (ROM C lines 1713-1745)
        options = ["You can train:"]

        # Check which stats can be trained (ROM C src/act_move.c:1716-1725).
        # ROM reads `ch->perm_stat[STAT_*]`; QuickMUD stores the same list at
        # `char.perm_stat`. There are no `perm_str`/`perm_int`/… attributes.
        # TRAIN-004: the ceiling is race/class-specific via get_max_train
        # (ROM src/handler.c:876), not a hardcoded 22.
        from mud.handler import get_max_train

        perm_stat = getattr(char, "perm_stat", []) or []

        def _stat(idx: int) -> int:
            return perm_stat[idx] if idx < len(perm_stat) else 0

        if _stat(0) < get_max_train(char, 0):  # STAT_STR
            options.append(" str")
        if _stat(1) < get_max_train(char, 1):  # STAT_INT
            options.append(" int")
        if _stat(2) < get_max_train(char, 2):  # STAT_WIS
            options.append(" wis")
        if _stat(3) < get_max_train(char, 3):  # STAT_DEX
            options.append(" dex")
        if _stat(4) < get_max_train(char, 4):  # STAT_CON
            options.append(" con")
        options.append(" hp mana")

        # Easter egg if nothing to train (ROM C lines 1733-1742)
        if len(options) == 1:  # Only "You can train:"
            # Jordan's easter egg message
            sex = getattr(char, "sex", 0)
            if sex == 1:  # SEX_MALE
                return session_prefix + "You have nothing left to train, you big stud!"
            elif sex == 2:  # SEX_FEMALE
                return session_prefix + "You have nothing left to train, you hot babe!"
            else:
                return session_prefix + "You have nothing left to train, you wild thing!"

        return session_prefix + "".join(options) + "."

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

        # TRAIN-004: ROM src/act_move.c:1781 gates on get_max_train(ch, stat)
        # (race/class-specific, ROM src/handler.c:876), not a hardcoded 22.
        from mud.handler import get_max_train

        if current_value >= get_max_train(char, stat_index):
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
