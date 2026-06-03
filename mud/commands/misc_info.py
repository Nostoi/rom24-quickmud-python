"""
Misc info commands - motd, rules, story, socials, skills, spells, rent.

ROM Reference: src/act_info.c, src/skills.c, src/act_comm.c
"""

from __future__ import annotations

from mud.models.character import Character


def do_motd(char: Character, args: str) -> str:
    """
    Display the Message of the Day.

    ROM Reference: src/act_info.c do_motd (line 631)

    Just calls help motd.
    """
    from mud.commands.help import do_help

    return do_help(char, "motd")


def do_imotd(char: Character, args: str) -> str:
    """
    Display the Immortal Message of the Day.

    ROM Reference: src/act_info.c do_imotd (line 636)
    """
    from mud.commands.help import do_help

    return do_help(char, "imotd")


def do_rules(char: Character, args: str) -> str:
    """
    Display the game rules.

    ROM Reference: src/act_info.c do_rules (line 641)
    """
    from mud.commands.help import do_help

    return do_help(char, "rules")


def do_story(char: Character, args: str) -> str:
    """
    Display the game backstory.

    ROM Reference: src/act_info.c do_story (line 646)
    """
    from mud.commands.help import do_help

    return do_help(char, "story")


def do_socials(char: Character, args: str) -> str:
    """
    List all available social commands.

    ROM Reference: src/act_info.c do_socials (lines 606-625)
    """
    # Try to import socials from various locations
    socials = []

    try:
        from mud.data.social_data import SOCIALS

        socials = list(SOCIALS.keys())
    except ImportError:
        try:
            from mud import registry

            soc_table = getattr(registry, "social_table", {})
            socials = list(soc_table.keys())
        except (ImportError, AttributeError):
            pass

    if not socials:
        return "No socials found."

    socials = sorted(socials)

    # Format in 6 columns
    lines = []
    row = []
    for i, social in enumerate(socials):
        row.append(f"{social:<12}")
        if len(row) == 6:
            lines.append("".join(row))
            row = []

    if row:
        lines.append("".join(row))

    return "\n".join(lines)


LEVEL_HERO = 51


def _parse_skills_args(args: str) -> tuple[bool, int, int, str | None]:
    """ROM `do_skills`/`do_spells` arg parser (src/skills.c:269-318).

    Returns (fAll, min_lev, max_lev, error). When `error` is non-None the caller
    should return it verbatim. ROM accepts `[all] [max [min]]`: with no args
    only currently-reachable entries show; with `all`, the full table; with one
    numeric arg, entries at exactly that level (1..max); with two, the closed
    range [min..max].
    """

    fAll = False
    min_lev = 1
    max_lev = LEVEL_HERO

    remaining = (args or "").strip()
    if not remaining:
        return fAll, min_lev, max_lev, None

    fAll = True

    # ROM `str_prefix(argument, "all")` returns 0 (match) when argument is a
    # prefix of "all". If matched we consume it; the remainder may then carry
    # numeric range arguments. If the arg isn't "all"-prefixed, ROM falls
    # straight into the numeric branch with the original argument.
    if "all".startswith(remaining.lower().split(None, 1)[0]):
        parts = remaining.split(None, 1)
        remaining = parts[1] if len(parts) > 1 else ""

    if not remaining:
        return fAll, min_lev, max_lev, None

    tokens = remaining.split()
    if not tokens[0].lstrip("-").isdigit():
        return fAll, min_lev, max_lev, "Arguments must be numerical or all."
    max_lev = int(tokens[0])
    if max_lev < 1 or max_lev > LEVEL_HERO:
        return fAll, min_lev, max_lev, f"Levels must be between 1 and {LEVEL_HERO}."

    if len(tokens) > 1:
        if not tokens[1].lstrip("-").isdigit():
            return fAll, min_lev, max_lev, "Arguments must be numerical or all."
        min_lev = max_lev
        max_lev = int(tokens[1])
        if max_lev < 1 or max_lev > LEVEL_HERO:
            return fAll, min_lev, max_lev, f"Levels must be between 1 and {LEVEL_HERO}."
        if min_lev > max_lev:
            return fAll, min_lev, max_lev, "That would be silly."

    return fAll, min_lev, max_lev, None


def _class_level_for_skill(skill, class_idx: int) -> int:
    """Return `skill_table[sn].skill_level[ch->class]` equivalent."""

    levels = getattr(skill, "levels", None)
    if isinstance(levels, list | tuple) and len(levels) > class_idx:
        try:
            return int(levels[class_idx])
        except (TypeError, ValueError):
            return LEVEL_HERO + 1
    return LEVEL_HERO + 1


def _render_skill_list(rows_by_level: dict[int, list[str]]) -> str:
    """ROM page layout: 2-column rows under a `Level NN:` header per group."""

    lines: list[str] = []
    for lvl in sorted(rows_by_level.keys()):
        entries = rows_by_level[lvl]
        header = f"Level {lvl:2d}: {entries[0]}"
        lines.append(header)
        for index in range(1, len(entries), 2):
            chunk = entries[index : index + 2]
            lines.append("          " + "".join(chunk))
    return "\n".join(lines)


def do_skills(char: Character, args: str) -> str:
    """List character's known non-spell skills.

    ROM parity: ``do_skills`` in ``src/skills.c:381-485``.
    """

    if getattr(char, "is_npc", False):
        return ""

    fAll, min_lev, max_lev, error = _parse_skills_args(args)
    if error:
        return error

    from mud.skills.registry import skill_registry

    level = int(getattr(char, "level", 1) or 1)
    try:
        class_idx = int(getattr(char, "ch_class", 0) or 0)
    except (TypeError, ValueError):
        class_idx = 0

    learned: dict[str, int] = getattr(char, "skills", {}) or {}

    rows_by_level: dict[int, list[str]] = {}
    for name, skill in skill_registry.skills.items():
        if getattr(skill, "type", "skill") != "skill":
            continue
        skill_lvl = _class_level_for_skill(skill, class_idx)
        if skill_lvl >= LEVEL_HERO + 1:
            continue
        if not fAll and skill_lvl > level:
            continue
        if skill_lvl < min_lev or skill_lvl > max_lev:
            continue
        pct = int(learned.get(name, 0) or 0)
        if pct <= 0:
            continue
        if level < skill_lvl:
            entry = f"{name:<18} n/a      "
        else:
            entry = f"{name:<18} {pct:3d}%      "
        rows_by_level.setdefault(skill_lvl, []).append(entry)

    if not rows_by_level:
        return "No skills found."
    return _render_skill_list(rows_by_level)


def do_spells(char: Character, args: str) -> str:
    """List character's known spells with mana cost.

    ROM parity: ``do_spells`` in ``src/skills.c:256-378``.
    """

    if getattr(char, "is_npc", False):
        return ""

    fAll, min_lev, max_lev, error = _parse_skills_args(args)
    if error:
        return error

    from mud.skills.registry import skill_registry

    level = int(getattr(char, "level", 1) or 1)
    try:
        class_idx = int(getattr(char, "ch_class", 0) or 0)
    except (TypeError, ValueError):
        class_idx = 0

    learned: dict[str, int] = getattr(char, "skills", {}) or {}

    rows_by_level: dict[int, list[str]] = {}
    for name, skill in skill_registry.skills.items():
        if getattr(skill, "type", "skill") != "spell":
            continue
        spell_lvl = _class_level_for_skill(skill, class_idx)
        if spell_lvl >= LEVEL_HERO + 1:
            continue
        if not fAll and spell_lvl > level:
            continue
        if spell_lvl < min_lev or spell_lvl > max_lev:
            continue
        pct = int(learned.get(name, 0) or 0)
        if pct <= 0:
            continue
        if level < spell_lvl:
            entry = f"{name:<18} n/a      "
        else:
            min_mana = int(getattr(skill, "min_mana", 0) or 0)
            mana = max(min_mana, 100 // (2 + level - spell_lvl))
            entry = f"{name:<18}  {mana:3d} mana  "
        rows_by_level.setdefault(spell_lvl, []).append(entry)

    if not rows_by_level:
        return "No spells found."
    return _render_skill_list(rows_by_level)


def do_rent(char: Character, args: str) -> str:
    """
    Rent message - ROM has no rent system.

    ROM Reference: src/act_comm.c do_rent (line 1447)

    Just tells players there's no rent.
    """
    return "There is no rent here. Just save and quit."
