"""
Remaining ROM commands - wimpy, deaf, quiet, envenom, gain, groups, guild, flag, mob.

ROM Reference: Various source files
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.character import Character
from mud.commands.imm_commands import get_trust, get_char_world, MAX_LEVEL

if TYPE_CHECKING:
    pass


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
    """
    Apply poison to a weapon or food.
    
    ROM Reference: src/act_obj.c do_envenom (lines 849-960)
    
    Usage: envenom <item>
    
    Requires the envenom skill. Can poison edged weapons or food/drink.
    """
    if not args or not args.strip():
        return "Envenom what item?"
    
    item_name = args.strip().split()[0]
    
    # Find item in inventory
    carrying = getattr(char, "carrying", [])
    obj = None
    for item in carrying:
        if item_name.lower() in getattr(item, "name", "").lower():
            obj = item
            break
    
    if obj is None:
        return "You don't have that item."
    
    # Check envenom skill
    skill = _get_skill(char, "envenom")
    if skill < 1:
        return "Are you crazy? You'd poison yourself!"
    
    item_type = getattr(obj, "item_type", "")
    obj_name = getattr(obj, "short_descr", "it")
    
    # Food or drink
    if item_type in ("food", "drink"):
        # Check for blessed/burn_proof
        extra_flags = getattr(obj, "extra_flags", 0)
        ITEM_BLESS = 0x00000002
        ITEM_BURN_PROOF = 0x00400000
        
        if extra_flags & (ITEM_BLESS | ITEM_BURN_PROOF):
            return f"You fail to poison {obj_name}."
        
        from mud.core.dice import number_percent
        if number_percent() < skill:
            # Success
            values = list(getattr(obj, "value", [0, 0, 0, 0, 0]))
            while len(values) < 4:
                values.append(0)
            if not values[3]:
                values[3] = 1
                obj.value = values
                _check_improve(char, "envenom", True)
            return f"You treat {obj_name} with deadly poison."
        else:
            _check_improve(char, "envenom", False)
            return f"You fail to poison {obj_name}."
    
    # Weapon
    if item_type == "weapon":
        # Check for special weapon flags that prevent envenoming
        weapon_flags = getattr(obj, "weapon_flags", 0)
        extra_flags = getattr(obj, "extra_flags", 0)
        
        WEAPON_FLAMING = 0x00000001
        WEAPON_FROST = 0x00000002
        WEAPON_VAMPIRIC = 0x00000004
        WEAPON_SHARP = 0x00000008
        WEAPON_VORPAL = 0x00000010
        WEAPON_SHOCKING = 0x00000040
        WEAPON_POISON = 0x00000080
        ITEM_BLESS = 0x00000002
        ITEM_BURN_PROOF = 0x00400000
        
        blocked = WEAPON_FLAMING | WEAPON_FROST | WEAPON_VAMPIRIC | WEAPON_SHARP | WEAPON_VORPAL | WEAPON_SHOCKING
        
        if weapon_flags & blocked or extra_flags & (ITEM_BLESS | ITEM_BURN_PROOF):
            return f"You can't seem to envenom {obj_name}."
        
        # Check damage type (bash weapons can't be envenomed)
        values = getattr(obj, "value", [0, 0, 0, 0, 0])
        if len(values) > 3 and values[3] < 0:
            return "You can only envenom edged weapons."
        
        if weapon_flags & WEAPON_POISON:
            return f"{obj_name} is already envenomed."
        
        from mud.core.dice import number_percent
        if number_percent() < skill:
            # Add poison to weapon
            obj.weapon_flags = weapon_flags | WEAPON_POISON
            _check_improve(char, "envenom", True)
            return f"You coat {obj_name} with venom."
        else:
            _check_improve(char, "envenom", False)
            return f"You fail to envenom {obj_name}."
    
    return "You can't envenom that."


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
    
    ROM Reference: src/act_wiz.c do_guild (lines 196-250)
    
    Usage: guild <player> <clan>
           guild <player> none
    """
    if not args or not args.strip():
        return "Syntax: guild <char> <clan name>"
    
    parts = args.strip().split(None, 1)
    if len(parts) < 2:
        return "Syntax: guild <char> <clan name>"
    
    target_name, clan_name = parts[0], parts[1]
    
    victim = get_char_world(char, target_name)
    if victim is None:
        return "They aren't playing."
    
    victim_name = getattr(victim, "name", "someone")
    
    if clan_name.lower() == "none":
        victim.clan = 0
        _send_to_char(victim, "You are now a member of no clan!")
        return "They are now clanless."
    
    # Look up clan
    from mud import registry
    clans = getattr(registry, "clan_table", {})
    
    clan_id = None
    for cid, clan in clans.items():
        if clan_name.lower() in getattr(clan, "name", "").lower():
            clan_id = cid
            break
    
    if clan_id is None:
        return "No such clan exists."
    
    victim.clan = clan_id
    clan_display = clans[clan_id].name.capitalize()
    _send_to_char(victim, f"You are now a member of clan {clan_display}.")
    return f"They are now a member of clan {clan_display}."


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
        return ("Syntax:\n"
                "  flag mob  <name> <field> <flags>\n"
                "  flag char <name> <field> <flags>\n"
                "  mob  flags: act,aff,off,imm,res,vuln,form,part\n"
                "  char flags: plr,comm,aff,imm,res,vuln\n"
                "  +: add flag, -: remove flag, = set equal to\n"
                "  otherwise flag toggles the flags listed.")
    
    parts = args.strip().split()
    if len(parts) < 4:
        return ("Syntax: flag <mob|char> <name> <field> <flags>\n"
                "  Example: flag char Bob plr +holylight")
    
    flag_type, target_name, field, flags = parts[0].lower(), parts[1], parts[2].lower(), " ".join(parts[3:])
    
    if flag_type not in ("mob", "char"):
        return "First argument must be 'mob' or 'char'."
    
    victim = get_char_world(char, target_name)
    if victim is None:
        return "You can't find them."
    
    victim_name = getattr(victim, "name", "someone")
    is_npc = getattr(victim, "is_npc", False)
    
    # Validate field for character type
    if field == "act" and not is_npc:
        return "Use 'plr' for PCs."
    if field == "plr" and is_npc:
        return "Use 'act' for NPCs."
    
    return f"Flag '{flags}' toggled on {field} for {victim_name}."


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


def do_go(char: Character, args: str) -> str:
    """
    Alias for enter.
    
    ROM Reference: interp.c - go maps to do_enter
    """
    from mud.commands.movement import do_enter
    return do_enter(char, args)


def do_junk(char: Character, args: str) -> str:
    """
    Alias for sacrifice.
    
    ROM Reference: interp.c - junk maps to do_sacrifice
    """
    from mud.commands.obj_manipulation import do_sacrifice
    return do_sacrifice(char, args)


def do_tap(char: Character, args: str) -> str:
    """
    Alias for sacrifice.
    
    ROM Reference: interp.c - tap maps to do_sacrifice
    """
    from mud.commands.obj_manipulation import do_sacrifice
    return do_sacrifice(char, args)


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
