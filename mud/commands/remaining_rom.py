"""
Remaining ROM commands - wimpy, deaf, quiet, envenom, gain, groups, guild, flag, mob.

ROM Reference: Various source files
"""

from __future__ import annotations

from enum import IntFlag
from typing import TYPE_CHECKING

from mud.commands.imm_commands import MAX_LEVEL, get_char_world, get_trust
from mud.models.character import Character
from mud.models.constants import (
    ActFlag,
    AffectFlag,
    CommFlag,
    FormFlag,
    ImmFlag,
    PartFlag,
    PlayerFlag,
)

if TYPE_CHECKING:
    pass


# Field name → (Character attribute, IntFlag enum, NPC-only?, PC-only?).
# Mirrors ROM src/flags.c:105-187 do_flag dispatcher. Immunity / resist / vuln
# all share imm_flags as the lookup table per ROM 141-151.
_FLAG_FIELDS: dict[str, tuple[str, type[IntFlag], bool, bool]] = {
    # ROM src/flags.c:105-115 — act: NPC act_flags
    "act": ("act", ActFlag, True, False),
    # ROM src/flags.c:117-127 — plr: PC plr_flags (stored in victim->act)
    "plr": ("act", PlayerFlag, False, True),
    # ROM src/flags.c:129-133 — aff: shared affect_flags
    "aff": ("affected_by", AffectFlag, False, False),
    # ROM src/flags.c:135-139 — immunity uses imm_flags table
    "immunity": ("imm_flags", ImmFlag, False, False),
    # ROM src/flags.c:141-145 — resist uses imm_flags table (yes, same table)
    "resist": ("res_flags", ImmFlag, False, False),
    # ROM src/flags.c:147-151 — vuln uses imm_flags table
    "vuln": ("vuln_flags", ImmFlag, False, False),
    # ROM src/flags.c:153-163 — form: NPC form_flags
    "form": ("form", FormFlag, True, False),
    # ROM src/flags.c:165-175 — parts: NPC part_flags
    "parts": ("parts", PartFlag, True, False),
    # ROM src/flags.c:177-187 — comm: PC comm_flags
    "comm": ("comm", CommFlag, False, True),
}


def _lookup_flag_bit(token: str, flag_enum: type[IntFlag]) -> int | None:
    """Case-insensitive prefix-match lookup of a ROM flag name on an IntFlag.

    Mirrors ROM ``flag_lookup(word, flag_table)`` (src/bit.c → src/lookup.c:39-51):
    accepts ``token`` when it is a prefix of any enum member's name. Returns
    the bit value or ``None`` if no member matches (ROM ``NO_FLAG``).
    """
    # mirroring ROM src/lookup.c:39-51 — str_prefix accepts abbreviations.
    from mud.utils.prefix_lookup import prefix_lookup_intflag

    return prefix_lookup_intflag(token, flag_enum)


# Comm flags
COMM_DEAF = 0x00000002
COMM_QUIET = 0x00000004


def do_wimpy(char: Character, args: str) -> str:
    """
    Set wimpy threshold for automatic fleeing.

    ROM Reference: src/act_info.c do_wimpy (lines 2800-2830)

    Usage: wimpy [hp]

    When HP drops below wimpy, you automatically try to flee.
    Default is max_hp / 5, max is max_hp / 2.
    """
    max_hit = getattr(char, "max_hit", 100)

    if not args or not args.strip():
        wimpy = max_hit // 5
    else:
        try:
            wimpy = int(args.strip().split()[0])
        except ValueError:
            return "Wimpy must be a number."

    if wimpy < 0:
        return "Your courage exceeds your wisdom."

    if wimpy > max_hit // 2:
        return "Such cowardice ill becomes you."

    char.wimpy = wimpy
    return f"Wimpy set to {wimpy} hit points."


def do_deaf(char: Character, args: str) -> str:
    """
    Toggle deaf mode - blocks tells.

    ROM Reference: src/act_comm.c do_deaf (lines 208-222)

    Usage: deaf
    """
    comm_flags = getattr(char, "comm", 0)

    if comm_flags & COMM_DEAF:
        char.comm = comm_flags & ~COMM_DEAF
        return "You can now hear tells again."
    else:
        char.comm = comm_flags | COMM_DEAF
        return "From now on, you won't hear tells."


def do_quiet(char: Character, args: str) -> str:
    """
    Toggle quiet mode - blocks most communication.

    ROM Reference: src/act_comm.c do_quiet (lines 225-240)

    Usage: quiet

    In quiet mode, you only hear says and emotes.
    """
    comm_flags = getattr(char, "comm", 0)

    if comm_flags & COMM_QUIET:
        char.comm = comm_flags & ~COMM_QUIET
        return "Quiet mode removed."
    else:
        char.comm = comm_flags | COMM_QUIET
        return "From now on, you will only hear says and emotes."


def do_envenom(char: Character, args: str) -> str:
    """Dispatcher entry point — delegates to the canonical skill handler.

    ROM Reference: src/act_obj.c:849-963 (do_envenom)
    """
    from mud.skills.handlers import envenom

    item_name = args.strip().split(maxsplit=1)[0] if args and args.strip() else ""
    result = envenom(char, item_name=item_name)
    return str(result.get("message", ""))


def do_gain(char: Character, args: str) -> str:
    """
    Gain new skills/groups from a trainer or convert practices.

    ROM Reference: src/skills.c do_gain (lines 44-200)

    Usage:
    - gain list       - List available skills/groups
    - gain convert    - Convert 10 practices to 1 train
    - gain points     - Convert trains to creation points
    - gain <skill>    - Learn a skill or group
    """
    if getattr(char, "is_npc", False):
        return ""

    # Find trainer in room
    room = getattr(char, "room", None)
    trainer = None
    if room:
        for person in getattr(room, "people", []):
            if getattr(person, "is_npc", False):
                act_flags = getattr(person, "act", 0)
                ACT_GAIN = 0x00100000
                if act_flags & ACT_GAIN:
                    trainer = person
                    break

    if trainer is None:
        return "You can't do that here."

    if not args or not args.strip():
        trainer_name = getattr(trainer, "short_descr", "The trainer")
        return f"{trainer_name} says 'Pardon me?'"

    arg = args.strip().split()[0].lower()

    if arg == "list":
        lines = [f"{'group':<18s} {'cost':>5s} {'group':<18s} {'cost':>5s} {'group':<18s} {'cost':>5s}"]
        # Would list available groups/skills here
        lines.append("(Group listing not fully implemented)")
        lines.append("")
        lines.append(f"{'skill':<18s} {'cost':>5s} {'skill':<18s} {'cost':>5s} {'skill':<18s} {'cost':>5s}")
        lines.append("(Skill listing not fully implemented)")
        return "\n".join(lines)

    if arg == "convert":
        practice = getattr(char, "practice", 0)
        if practice < 10:
            trainer_name = getattr(trainer, "short_descr", "The trainer")
            return f"{trainer_name} tells you 'You are not yet ready.'"

        char.practice = practice - 10
        char.train = getattr(char, "train", 0) + 1
        trainer_name = getattr(trainer, "short_descr", "The trainer")
        return f"{trainer_name} helps you apply your practice to training."

    if arg == "points":
        train = getattr(char, "train", 0)
        if train < 2:
            trainer_name = getattr(trainer, "short_descr", "The trainer")
            return f"{trainer_name} tells you 'You are not yet ready.'"

        char.train = train - 2
        pcdata = getattr(char, "pcdata", None)
        if pcdata:
            pcdata.points = getattr(pcdata, "points", 0) + 1
        trainer_name = getattr(trainer, "short_descr", "The trainer")
        return f"{trainer_name} trains you, and you gain a creation point."

    return "That is not a valid option. Try 'gain list'."


def do_groups(char: Character, args: str) -> str:
    """
    Show known skill groups or list all groups.

    ROM Reference: src/skills.c do_groups (lines 850-920)

    Usage:
    - groups           - Show your known groups
    - groups all       - Show all groups
    - groups <group>   - Show skills in a group
    """
    if getattr(char, "is_npc", False):
        return ""

    pcdata = getattr(char, "pcdata", None)

    if not args or not args.strip():
        # Show known groups
        lines = ["Your known groups:"]

        group_known = getattr(pcdata, "group_known", {}) if pcdata else {}
        if not group_known:
            lines.append("  (none)")
        else:
            col = 0
            row = []
            for name in sorted(group_known.keys()):
                if group_known[name]:
                    row.append(f"{name:<20s}")
                    col += 1
                    if col >= 3:
                        lines.append(" ".join(row))
                        row = []
                        col = 0
            if row:
                lines.append(" ".join(row))

        points = getattr(pcdata, "points", 0) if pcdata else 0
        lines.append(f"\nCreation points: {points}")
        return "\n".join(lines)

    arg = args.strip().lower()

    if arg == "all":
        lines = ["All available groups:"]
        from mud import registry

        groups = getattr(registry, "group_table", {})
        if not groups:
            lines.append("  (no groups defined)")
        else:
            col = 0
            row = []
            for name in sorted(groups.keys()):
                row.append(f"{name:<20s}")
                col += 1
                if col >= 3:
                    lines.append(" ".join(row))
                    row = []
                    col = 0
            if row:
                lines.append(" ".join(row))
        return "\n".join(lines)

    # Show specific group
    from mud import registry

    groups = getattr(registry, "group_table", {})

    if arg not in groups:
        return "No group of that name exists.\nType 'groups all' for a full listing."

    group = groups[arg]
    spells = getattr(group, "spells", [])

    lines = [f"Skills in group '{arg}':"]
    if not spells:
        lines.append("  (none)")
    else:
        col = 0
        row = []
        for spell in spells:
            row.append(f"{spell:<20s}")
            col += 1
            if col >= 3:
                lines.append(" ".join(row))
                row = []
                col = 0
        if row:
            lines.append(" ".join(row))

    return "\n".join(lines)


def do_guild(char: Character, args: str) -> str:
    """
    Set a player's clan/guild membership.

    ROM Reference: src/act_wiz.c do_guild (lines 196-249)

    Usage: guild <player> <clan>
           guild <player> none
    """
    if not args or not args.strip():
        return "Syntax: guild <char> <cln name>\n\r"

    parts = args.strip().split(None, 1)
    if len(parts) < 2:
        return "Syntax: guild <char> <cln name>\n\r"

    target_name, clan_name = parts[0], parts[1]

    victim = get_char_world(char, target_name)
    if victim is None:
        return "They aren't playing.\n\r"

    # mirrors ROM src/act_wiz.c:217 — str_prefix check for "none"
    if clan_name.lower().startswith("none"):
        victim.clan = 0
        _send_to_char(victim, "You are now a member of no clan!\n\r")
        return "They are now clanless.\n\r"

    from mud.models.clans import CLAN_TABLE, lookup_clan_id

    clan = lookup_clan_id(clan_name)
    if clan == 0:
        return "No such clan exists.\n\r"

    clan_entry = CLAN_TABLE[clan]
    victim.clan = clan

    if clan_entry.is_independent:
        _send_to_char(victim, f"You are now a {clan_entry.name}.\n\r")
        return f"They are now a {clan_entry.name}.\n\r"
    else:
        clan_display = clan_entry.name.capitalize()
        _send_to_char(victim, f"You are now a member of clan {clan_display}.\n\r")
        return f"They are now a member of clan {clan_display}.\n\r"


def do_flag(char: Character, args: str) -> str:
    """
    Toggle flags on a character or mobile.

    ROM Reference: src/flags.c do_flag (lines 44-200)

    Usage: flag mob <name> <field> <flags>
           flag char <name> <field> <flags>

    Fields: act, aff, off, imm, res, vuln, form, part (mobs)
            plr, comm, aff, imm, res, vuln (chars)
    """
    if not args or not args.strip():
        return (
            "Syntax:\n"
            "  flag mob  <name> <field> <flags>\n"
            "  flag char <name> <field> <flags>\n"
            "  mob  flags: act,aff,off,imm,res,vuln,form,part\n"
            "  char flags: plr,comm,aff,imm,res,vuln\n"
            "  +: add flag, -: remove flag, = set equal to\n"
            "  otherwise flag toggles the flags listed."
        )

    tokens = args.strip().split()
    if len(tokens) < 4:
        return "Syntax: flag <mob|char> <name> <field> <flags>\n  Example: flag char Bob plr +holylight"

    flag_type = tokens[0].lower()
    target_name = tokens[1]
    field = tokens[2].lower()
    rest = tokens[3:]

    if flag_type not in ("mob", "char"):
        return "First argument must be 'mob' or 'char'."

    victim = get_char_world(char, target_name)
    if victim is None:
        return "You can't find them."

    is_npc = getattr(victim, "is_npc", False)

    # mirroring ROM src/flags.c:107-110, 119-123 — NPC-only / PC-only field guards.
    if field == "act" and not is_npc:
        return "Use 'plr' for PCs."
    if field == "plr" and is_npc:
        return "Use 'act' for NPCs."
    if field == "form" and not is_npc:
        return "Form can't be set on PCs."
    if field == "parts" and not is_npc:
        return "Parts can't be set on PCs."
    if field == "comm" and is_npc:
        return "Comm can't be set on NPCs."

    field_spec = _FLAG_FIELDS.get(field)
    if field_spec is None:
        # mirroring ROM src/flags.c:189-193 — unknown field falls through to error.
        return "That's not an acceptable flag."

    attr_name, flag_enum, _npc_only, _pc_only = field_spec

    # mirroring ROM src/flags.c:58-61 — leading '=', '+', or '-' selects mode;
    # otherwise the operator is implicit toggle.
    op = "toggle"
    if rest and rest[0] in ("=", "+", "-"):
        op = {"=": "set", "+": "add", "-": "remove"}[rest[0]]
        rest = rest[1:]
    elif rest and rest[0][:1] in ("=", "+", "-") and len(rest[0]) > 1:
        # ROM `argument[0]` is the leading byte; `=holylight` is also valid.
        op = {"=": "set", "+": "add", "-": "remove"}[rest[0][0]]
        rest[0] = rest[0][1:]

    if not rest:
        return "Which flags do you wish to change?"

    # mirroring ROM src/flags.c:202-218 — accumulate `marked` mask; bail on
    # any unknown flag name with `That flag doesn't exist!`.
    marked = 0
    for token in rest:
        if not token:
            continue
        bit = _lookup_flag_bit(token, flag_enum)
        if bit is None:
            return "That flag doesn't exist!"
        marked |= bit

    old = int(getattr(victim, attr_name, 0) or 0)
    # mirroring ROM src/flags.c:198-199 — `=` resets baseline to 0; everything
    # else starts from the existing value.
    new = 0 if op == "set" else old

    # mirroring ROM src/flags.c:220-247 — apply marked bits per operator.
    # (FLAG-002 deferred: ROM also preserves non-`settable` bits across `=`;
    # Python IntFlag carries no per-bit settable metadata yet.)
    if op in ("set", "add"):
        new |= marked
    elif op == "remove":
        new &= ~marked
    else:  # toggle
        new ^= marked

    setattr(victim, attr_name, new)
    victim_name = getattr(victim, "name", "someone")
    return f"Flag '{field}' updated on {victim_name}."


def do_mob(char: Character, args: str) -> str:
    """
    Mob command interpreter - executes mob program commands.

    ROM Reference: src/mob_cmds.c do_mob (lines 82-92)

    Usage: mob <command> [args]

    Only usable by NPCs or max-level immortals (for mob programs).
    """
    # Security check
    desc = getattr(char, "desc", None)
    if desc is not None and get_trust(char) < MAX_LEVEL:
        return ""

    if not args or not args.strip():
        return "Mob command requires an argument."

    # Would call mob_interpret here
    return f"Mob command executed: {args}"


# Alias commands - these just call other commands


def do_bs(char: Character, args: str) -> str:
    """
    Alias for backstab.

    ROM Reference: interp.c - bs maps to do_backstab
    """
    from mud.commands.combat import do_backstab

    return do_backstab(char, args)


def do_teleport(char: Character, args: str) -> str:
    """
    Alias for transfer.

    ROM Reference: interp.c - teleport maps to do_transfer
    """
    from mud.commands.imm_commands import do_transfer

    return do_transfer(char, args)


# Helper functions


def _get_skill(char: Character, skill_name: str) -> int:
    """Get character's skill level."""
    pcdata = getattr(char, "pcdata", None)
    if pcdata is None:
        return 0

    learned = getattr(pcdata, "learned", {})

    from mud import registry

    for sn, skill in enumerate(getattr(registry, "skill_table", [])):
        if skill and getattr(skill, "name", "").lower() == skill_name.lower():
            return learned.get(sn, 0)

    return 0


def _check_improve(char: Character, skill_name: str, success: bool) -> None:
    """Check for skill improvement."""
    pass


def _send_to_char(char: Character, message: str) -> None:
    """Send message to character."""
    if not hasattr(char, "output_buffer"):
        char.output_buffer = []
    char.output_buffer.append(message)


def do_qmread(char: Character, args: str) -> str:
    """
    QuickMUD config file read command.

    ROM Reference: src/interp.h declares do_qmread but never implements it.
    This is a stub for ROM command parity.

    Usage: qmread

    Note: In ROM QuickMUD, this was planned to read qmconfig.rc but was
    never fully implemented. The qmconfig command handles config reading.
    """
    trust = get_trust(char)
    if trust < MAX_LEVEL:
        return "Huh?"

    return "QMConfig settings can be viewed with 'qmconfig' command."
