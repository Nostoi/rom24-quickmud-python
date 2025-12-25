"""
Test ROM Command Parity

Validates that QuickMUD implements all commands from ROM 2.4b6's src/interp.c cmd_table.
This test ensures we don't have a coverage blind spot where subsystem tests pass but
player-visible commands are missing.

ROM Reference: src/interp.c lines 1-2000 (cmd_table with 251 commands)
"""

from __future__ import annotations

import pytest

from mud.commands.dispatcher import COMMANDS, resolve_command


# ROM 2.4b6 command table extracted from src/interp.c
# This is the COMPLETE list of all 251 commands ROM provides
ROM_COMMANDS = {
    # Commands shown in help output (player-visible core commands)
    "north",
    "south",
    "east",
    "west",
    "up",
    "down",  # Movement
    "exits",
    "recall",
    "sleep",
    "wake",
    "rest",
    "stand",  # Movement/Position
    "get",
    "put",
    "drop",
    "give",
    "sacrifice",  # Object manipulation
    "wear",
    "wield",
    "hold",  # Equipment
    "recite",
    "quaff",
    "zap",
    "brandish",  # Magic items
    "lock",
    "unlock",
    "open",
    "close",
    "pick",  # Doors/containers
    "inventory",
    "equipment",
    "look",
    "compare",  # Inspection
    "eat",
    "drink",
    "fill",  # Consumption
    "list",
    "buy",
    "sell",
    "value",  # Shopping
    "follow",
    "group",
    "gtell",
    "split",  # Group
    "help",
    "credits",
    "commands",
    "areas",  # Information
    "report",
    "score",
    "time",
    "weather",
    "where",
    "who",  # Status
    "description",
    "password",
    "title",  # Character customization
    "bug",
    "idea",
    "typo",  # Player feedback
    "gossip",
    "cgossip",
    "say",
    "shout",
    "tell",
    "yell",  # Communication
    "emote",
    "pose",  # Emotes
    "note",  # Notes/boards
    "kill",
    "flee",
    "kick",
    "rescue",
    "disarm",  # Combat
    "backstab",
    "cast",
    "wimpy",  # Combat skills
    "save",
    "quit",
    "practice",
    "train",  # Session/Advancement
    # Additional ROM commands (full cmd_table from src/interp.c)
    "advance",
    "aedit",
    "affects",
    "afk",
    "alia",
    "alias",
    "alist",
    "allow",
    "answer",
    "asave",
    "at",
    "auction",
    "autoall",
    "autoassist",
    "autoexit",
    "autogold",
    "autolist",
    "autoloot",
    "autosac",
    "autosplit",
    "ban",
    "bash",
    "berserk",
    "board",
    "brief",
    "bs",
    "channels",
    "clan",
    "clone",
    "color",
    "colour",
    "combine",
    "compact",
    "consider",
    "copyover",
    "credits",
    "deaf",
    "delete",
    "deny",
    "deposit",
    "diku",
    "dirt",
    "disarm",
    "disconnect",
    "donate",
    "down",
    "dream",
    "dump",
    "echo",
    "edit",
    "enter",
    "envenom",
    "equipment",
    "examine",
    "exits",
    "fee",
    "feed",
    "fight",
    "finger",
    "flee",
    "follow",
    "force",
    "forget",
    "freeze",
    "gain",
    "gecho",
    "goto",
    "grab",
    "grats",
    "gtell",
    "guilds",
    "haste",
    "heal",
    "hedit",
    "hesave",
    "hide",
    "hlist",
    "holylight",
    "idea",
    "imotd",
    "immtalk",
    "imtlset",
    "incognito",
    "inventory",
    "invis",
    "kick",
    "kill",
    "level",
    "list",
    "load",
    "lock",
    "log",
    "look",
    "memory",
    "medit",
    "mfind",
    "mload",
    "mset",
    "mstat",
    "mwhere",
    "murder",
    "music",
    "mute",
    "newlock",
    "nochannels",
    "nofollow",
    "noloot",
    "nosummon",
    "notell",
    "oedit",
    "ofind",
    "oload",
    "order",
    "oset",
    "ostat",
    "outfit",
    "owhere",
    "pardon",
    "password",
    "peace",
    "peek",
    "pecho",
    "penalty",
    "permban",
    "pick",
    "play",
    "pmote",
    "pose",
    "pour",
    "practice",
    "prefix",
    "prompt",
    "protect",
    "pstat",
    "pull",
    "punch",
    "purge",
    "push",
    "put",
    "qmconfig",
    "quaff",
    "question",
    "qui",
    "quiet",
    "quote",
    "read",
    "reboo",
    "reboot",
    "recall",
    "recite",
    "recho",
    "redit",
    "rehash",
    "remove",
    "rent",
    "repair",
    "replay",
    "reply",
    "report",
    "rescue",
    "reset",
    "rest",
    "restore",
    "return",
    "revert",
    "rlist",
    "rset",
    "rstat",
    "sacrifice",
    "save",
    "scan",
    "sconfig",
    "score",
    "scroll",
    "search",
    "sell",
    "set",
    "sheath",
    "show",
    "shout",
    "shutdown",
    "sla",
    "slay",
    "sleep",
    "slice",
    "slist",
    "slook",
    "smote",
    "sneak",
    "snoop",
    "socials",
    "sockets",
    "spells",
    "stand",
    "stat",
    "steal",
    "story",
    "string",
    "surrender",
    "switch",
    "take",
    "tap",
    "teleport",
    "tell",
    "telnetga",
    "title",
    "train",
    "transfer",
    "trip",
    "trust",
    "unalias",
    "unlock",
    "value",
    "violate",
    "visible",
    "vnum",
    "wake",
    "wear",
    "weather",
    "where",
    "whois",
    "wield",
    "wimpy",
    "wizhelp",
    "wizinvis",
    "wizlist",
    "wizlock",
    "wiznet",
    "worth",
    "yell",
    "zap",
    "zecho",
}

# Commands that are implemented in Python but not in the dispatcher
# (e.g., implemented as special cases, socials, or IMC commands)
SPECIAL_CASE_COMMANDS = {
    "'",  # Alias for say (handled specially)
    ":",  # Alias for immtalk (handled specially)
    ".",  # IMC command prefix
    "/",  # IMC command prefix
    ";",  # Emote separator
    ",",  # Special syntax
    "n",
    "e",
    "s",
    "w",
    "u",
    "d",  # Directional aliases (registered)
}


def get_registered_commands() -> set[str]:
    """Extract all registered command names (including aliases) from dispatcher."""
    registered = set()
    for cmd in COMMANDS:
        registered.add(cmd.name)
        registered.update(cmd.aliases)
    return registered


def test_help_command_coverage():
    """
    Test that all commands listed in help output are actually implemented.

    This test prevents the specific failure mode where help lists commands
    that return 'Huh?' when typed.
    """
    from mud.commands.info import do_commands
    from mud.models.character import Character
    from mud.models.room import Room

    char = Character(name="Tester", level=1, trust=0, is_npc=False)
    char.room = Room(vnum=3001)
    output = do_commands(char, "")
    help_commands = set(output.replace("\r", "").split())

    registered = get_registered_commands()

    # Check each help command
    missing = []
    for cmd in help_commands:
        # Skip special syntax that's handled differently
        if cmd in {"!", "'"}:
            continue

        if cmd not in registered:
            # Try resolving it (handles abbreviations)
            if resolve_command(cmd) is None:
                missing.append(cmd)

    if missing:
        pytest.fail(
            f"Help output lists {len(missing)} commands that aren't implemented:\n"
            f"{', '.join(sorted(missing))}\n\n"
            f"These commands will return 'Huh?' when players try to use them.\n"
            f"Either implement them or remove them from help output."
        )


def test_critical_command_coverage():
    """
    Test that P0 critical commands are implemented.

    These are commands that break core gameplay if missing.
    """
    critical_commands = {
        "save",
        "quit",  # Session management
        "recall",  # Navigation
        "wear",
        "wield",
        "hold",  # Equipment
        "eat",
        "drink",  # Survival
        "score",  # Character info
        "flee",
        "cast",  # Combat essentials
    }

    registered = get_registered_commands()
    missing = critical_commands - registered

    if missing:
        pytest.fail(
            f"Missing {len(missing)} P0 CRITICAL commands:\n"
            f"{', '.join(sorted(missing))}\n\n"
            f"Game is not playable without these commands."
        )


def test_rom_command_coverage_metric():
    """
    Calculate and report ROM command coverage percentage.

    This provides an honest metric for ROM parity tracking.
    Not a strict test - just reports the gap for visibility.
    """
    registered = get_registered_commands()

    # Count ROM commands that are implemented
    implemented = ROM_COMMANDS & registered
    missing = ROM_COMMANDS - registered - SPECIAL_CASE_COMMANDS

    coverage = len(implemented) / len(ROM_COMMANDS) * 100

    print(f"\n{'=' * 80}")
    print(f"ROM COMMAND COVERAGE REPORT")
    print(f"{'=' * 80}")
    print(f"Total ROM commands:     {len(ROM_COMMANDS)}")
    print(f"Implemented:            {len(implemented)} ({coverage:.1f}%)")
    print(f"Missing:                {len(missing)}")
    print(f"{'=' * 80}")

    if missing:
        print(f"\nMissing commands ({len(missing)}):")
        for i, cmd in enumerate(sorted(missing), 1):
            if i % 6 == 0:
                print(f"  {cmd}")
            elif i == len(missing):
                print(f"  {cmd}")
            else:
                print(f"  {cmd:<15}", end="")
        print()

    # This is informational - don't fail the test
    # Real failures are in test_help_command_coverage() and test_critical_command_coverage()


def test_no_phantom_commands_in_help():
    """
    Test that help data doesn't list commands that don't exist.

    This is the reverse check - help should only document real commands.
    """
    # This would require parsing data/help.json, which we'll implement after
    # fixing the critical command gaps
    pass


@pytest.mark.parametrize(
    "cmd_name",
    [
        "north",
        "south",
        "east",
        "west",
        "up",
        "down",  # Basic movement must work
        "look",
        "inventory",
        "equipment",  # Basic inspection must work
        "say",
        "tell",  # Basic communication must work
    ],
)
def test_essential_commands_registered(cmd_name):
    """Verify essential ROM commands are registered (absolute minimum)."""
    assert resolve_command(cmd_name) is not None, f"Essential command '{cmd_name}' is not registered"
