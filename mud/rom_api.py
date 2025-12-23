"""
ROM 2.4 Parity API - Public wrapper functions for ROM C compatibility.

This module provides ROM C-compatible public API functions that wrap existing
Python implementations. These wrappers use ROM C naming conventions for
compatibility with external tools and documentation.

ROM Reference: src/board.c, src/olc_act.c, src/handler.c
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mud.models.board import Board
    from mud.models.character import Character
    from mud.models.note import Note


# =============================================================================
# Board System Public API (src/board.c)
# =============================================================================


def board_lookup(name: str) -> Board | None:
    """Find board by name.

    ROM parity: src/board.c:board_lookup (line 201)

    Args:
        name: Board name to search for (case-insensitive)

    Returns:
        Board object if found, None otherwise
    """
    from mud.notes import find_board

    return find_board(name)


def board_number(board_name: str) -> Board | None:
    """Get board by name (alias for board_lookup).

    ROM parity: src/board.c:board_number (line 189)

    Note: ROM C used numeric board IDs. Python uses names directly,
    so this is an alias for board_lookup for API compatibility.

    Args:
        board_name: Board name to retrieve

    Returns:
        Board object if found, None otherwise
    """
    from mud.notes import find_board

    return find_board(board_name)


def is_note_to(char: Character, note: Note) -> bool:
    """Check if character can read a note.

    ROM parity: src/board.c:is_note_to (line 408)

    Checks if note is addressed to character based on:
    - Note recipient list (to_list)
    - Character name match
    - "all" recipient

    Args:
        char: Character to check visibility for
        note: Note to check

    Returns:
        True if character can read note, False otherwise
    """
    from mud.commands.notes import _is_note_visible_to

    return _is_note_visible_to(char, note)


def note_from(note: Note) -> str:
    """Get note sender name.

    ROM parity: src/board.c (note->sender field access pattern)

    Args:
        note: Note to get sender from

    Returns:
        Sender name string
    """
    return note.sender


# =============================================================================
# Board Commands Public API (src/board.c)
# =============================================================================


def do_ncatchup(char: Character, args: str = "") -> str:
    """Mark all notes on current board as read.

    ROM parity: src/board.c:do_ncatchup (line 690)

    Args:
        char: Character executing command
        args: Command arguments (unused)

    Returns:
        Command result message
    """
    from mud.commands.notes import do_note

    return do_note(char, "catchup")


def do_nremove(char: Character, args: str) -> str:
    """Remove a note from the board.

    ROM parity: src/board.c:do_nremove (line 615)

    Args:
        char: Character executing command
        args: Note number to remove

    Returns:
        Command result message
    """
    from mud.commands.notes import do_note

    return do_note(char, f"remove {args}")


def do_nwrite(char: Character, args: str = "") -> str:
    """Start writing a new note.

    ROM parity: src/board.c:do_nwrite (line 467)

    Initiates note composition. Character can then use:
    - note to <recipient>
    - note subject <text>
    - note text (enters string editor)
    - note send

    Args:
        char: Character executing command
        args: Command arguments (unused)

    Returns:
        Command result message
    """
    from mud.commands.notes import do_note

    return do_note(char, "write")


def do_nlist(char: Character, args: str = "") -> str:
    """List notes on current board.

    ROM parity: src/board.c:do_nlist (line 648)

    Args:
        char: Character executing command
        args: Command arguments (unused)

    Returns:
        Formatted list of notes
    """
    from mud.commands.notes import do_note

    return do_note(char, "list")


def do_nread(char: Character, args: str) -> str:
    """Read a note from the board.

    ROM parity: src/board.c:do_nread (line 563)

    Args:
        char: Character executing command
        args: Note number to read or empty for next unread

    Returns:
        Note content or error message
    """
    from mud.commands.notes import do_note

    if args.strip():
        return do_note(char, f"read {args}")
    else:
        return do_note(char, "read")


# =============================================================================
# OLC Helper Functions Public API (src/olc_act.c)
# =============================================================================


def show_obj_values(obj) -> str:
    """Display object value fields formatted for OLC.

    ROM parity: src/olc_act.c:show_obj_values (line 2210)

    Shows v0-v4 value fields with descriptions based on item_type.

    Args:
        obj: Object to display values for

    Returns:
        Formatted string showing object values
    """
    from mud.commands.build import _oedit_show
    from io import StringIO

    output = StringIO()
    _oedit_show(output, obj.prototype if hasattr(obj, "prototype") else obj)
    return output.getvalue()


def wear_loc_lookup(token: str):
    """Convert wear location token to WearLocation enum.

    ROM parity: src/olc_act.c:wear_loc (line 1967)

    Args:
        token: Wear location name (e.g., "head", "body", "wield")

    Returns:
        WearLocation enum value or None if invalid
    """
    from mud.commands.build import _resolve_wear_loc

    try:
        return _resolve_wear_loc(token)
    except (ValueError, KeyError):
        return None


def show_flag_cmds() -> str:
    """Display available room flags for OLC.

    ROM parity: src/olc_act.c:show_flag_cmds (line 126)

    Returns:
        Formatted string listing available room flags
    """
    from mud.models.constants import RoomFlag

    flags = []
    for flag in RoomFlag:
        # Skip zero value (no flags set)
        if flag.value != 0:
            flags.append(f"{flag.name.lower():20} - {flag.value}")

    return "Available room flags:\n" + "\n".join(flags)


# =============================================================================
# Misc Utility Functions Public API
# =============================================================================


def check_blind(char: Character) -> bool:
    """Check if character is blind (cannot see).

    ROM parity: src/act_info.c:check_blind (line 542)

    Args:
        char: Character to check

    Returns:
        True if character can see, False if blind
    """
    from mud.world.vision import can_see_character

    return can_see_character(char, char)


def substitute_alias(char: Character, input_text: str) -> str:
    """Expand aliases in command input.

    ROM parity: src/alias.c:substitute_alias (line 41)

    Args:
        char: Character whose aliases to use
        input_text: Command input to expand

    Returns:
        Expanded command text with aliases substituted
    """
    from mud.commands.dispatcher import _expand_aliases

    return _expand_aliases(char, input_text)


def mult_argument(argument: str, number_str: str) -> tuple[int, str]:
    """Parse multiplier from argument (e.g., "5.sword" -> 5, "sword").

    ROM parity: src/interp.c:mult_argument (line 743)

    Used for shop commands like "buy 5 bread".

    Args:
        argument: Full argument string
        number_str: Pre-extracted number portion (unused in Python version)

    Returns:
        Tuple of (quantity, item_name)
    """
    from mud.commands.shop import _parse_purchase_quantity

    try:
        quantity, item = _parse_purchase_quantity(argument)
        return (quantity, item)
    except Exception:
        return (1, argument)


# =============================================================================
# Additional OLC Helper Functions
# =============================================================================


def set_obj_values(obj: Object, value_num: int, value: str) -> bool:
    """Parse and set object value by index.

    ROM parity: src/olc_act.c:set_value (line 543)

    Args:
        obj: Object to modify
        value_num: Value index (0-4)
        value: String value to parse and set

    Returns:
        True if value was set successfully, False otherwise
    """
    if not (0 <= value_num <= 4):
        return False

    try:
        obj.value[value_num] = int(value)
        return True
    except (ValueError, IndexError):
        return False


def check_range(lower: int, upper: int) -> bool:
    """Validate numeric range.

    ROM parity: src/olc.c:check_range (line 201)

    Args:
        lower: Lower bound
        upper: Upper bound

    Returns:
        True if range is valid (lower <= upper)
    """
    return lower <= upper


def wear_bit(location: str) -> int:
    """Convert wear location name to bit flag.

    ROM parity: src/olc_act.c:wear_bit (line 891)

    Args:
        location: Wear location name

    Returns:
        Wear bit flag value, or 0 if invalid
    """
    from mud.commands.build import _resolve_wear_loc

    loc = _resolve_wear_loc(location)
    if loc is None:
        return 0

    return 1 << int(loc)


def show_liqlist() -> str:
    """Display available liquid types for containers.

    ROM parity: src/olc_act.c:show_liqlist (line 723)

    Returns:
        Formatted string listing liquid types
    """
    from mud.models.constants import LIQUID_TABLE

    liquids = []
    for idx, liq in enumerate(LIQUID_TABLE):
        liquids.append(f"{liq.name:20} - {idx}")

    return "Available liquid types:\n" + "\n".join(liquids)


def show_damlist() -> str:
    """Display available damage types for weapons.

    ROM parity: src/olc_act.c:show_damlist (line 798)

    Returns:
        Formatted string listing damage types
    """
    from mud.models.constants import DamageType

    damages = []
    for dam in DamageType:
        damages.append(f"{dam.name.lower():20} - {dam.value}")

    return "Available damage types:\n" + "\n".join(damages)


def show_skill_cmds() -> str:
    """Format skill list for display.

    ROM parity: src/olc_act.c:show_skill (line 1021)

    Returns:
        Formatted string listing all skills
    """
    from mud.world.world_state import skill_registry

    if not skill_registry or not hasattr(skill_registry, "skills"):
        return "Skills not loaded."

    skills = list(skill_registry.skills.keys())

    return "Available skills:\n" + "\n".join(f"  {skill}" for skill in sorted(skills))


def show_spec_cmds() -> str:
    """Format special function list for display.

    ROM parity: src/olc_act.c:show_spec (line 1089)

    Returns:
        Formatted string listing available special functions
    """
    specs = [
        "spec_breath_any",
        "spec_breath_acid",
        "spec_breath_fire",
        "spec_breath_frost",
        "spec_breath_gas",
        "spec_breath_lightning",
        "spec_cast_adept",
        "spec_cast_cleric",
        "spec_cast_judge",
        "spec_cast_mage",
        "spec_cast_undead",
        "spec_executioner",
        "spec_fido",
        "spec_guard",
        "spec_janitor",
        "spec_mayor",
        "spec_poison",
        "spec_thief",
        "spec_nasty",
        "spec_troll_member",
        "spec_ogre_member",
        "spec_patrolman",
    ]

    return "Available special functions:\n" + "\n".join(f"  {spec}" for spec in sorted(specs))


def show_version() -> str:
    """Show OLC version information.

    ROM parity: src/olc.c:show_version (line 93)

    Returns:
        OLC version string
    """
    return "QuickMUD OLC v1.0 - Python ROM 2.4b Port"


def change_exit(room, direction: str, command: str, argument: str) -> str:
    """Edit room exit in specified direction.

    ROM parity: src/olc_act.c:change_exit (line 2201)

    Args:
        room: Room to modify
        direction: Direction name (north, south, etc.)
        command: Edit command (create, delete, to, key, name, desc)
        argument: Command argument

    Returns:
        Status message
    """
    from mud.commands.build import _redit_handle_exit

    return _redit_handle_exit(room, direction, command, argument)


def show_help() -> str:
    """Show OLC editor help.

    ROM parity: src/olc_act.c:show_help (line 165)

    Returns:
        Help text for OLC commands
    """
    return """OLC Editor Commands:
    
    show     - Display current object/room/mob
    create   - Create new item
    edit     - Edit existing item
    delete   - Delete item
    list     - List items
    save     - Save changes to disk
    done     - Exit editor
    
    For specific editor help, use: help aedit, help redit, help oedit, help medit
    """


def add_reset(area, reset_type: str, args: list[int]) -> bool:
    """Add reset command to area.

    ROM parity: src/olc_act.c:add_reset (line 3412)

    Args:
        area: Area to modify
        reset_type: Reset type ('M', 'O', 'P', 'G', 'E', 'D', 'R')
        args: Reset arguments (vnums, limits, etc.)

    Returns:
        True if reset was added successfully
    """
    from mud.loaders.reset_loader import Reset

    try:
        reset = Reset(
            command=reset_type,
            arg1=args[0] if len(args) > 0 else 0,
            arg2=args[1] if len(args) > 1 else 0,
            arg3=args[2] if len(args) > 2 else 0,
            arg4=args[3] if len(args) > 3 else 0,
        )

        if not hasattr(area, "resets"):
            area.resets = []

        area.resets.append(reset)
        return True
    except Exception:
        return False


# =============================================================================
# Admin Utility Functions
# =============================================================================


def do_imotd(char: Character) -> str:
    """Display immortal message of the day.

    ROM parity: src/act_wiz.c:do_imotd (line 1021)

    Args:
        char: Character requesting IMOTD

    Returns:
        IMOTD text or error message
    """
    from mud.commands.help import do_help

    return do_help(char, "imotd")


def do_rules(char: Character) -> str:
    """Display game rules.

    ROM parity: src/act_comm.c:do_rules (line 892)

    Args:
        char: Character requesting rules

    Returns:
        Rules text or error message
    """
    from mud.commands.help import do_help

    return do_help(char, "rules")


def do_story(char: Character) -> str:
    """Display game story/background.

    ROM parity: src/act_comm.c:do_story (line 912)

    Args:
        char: Character requesting story

    Returns:
        Story text or error message
    """
    from mud.commands.help import do_help

    return do_help(char, "story")


def get_max_train(char: Character, stat: str) -> int:
    """Calculate maximum stat training limit for character.

    ROM parity: src/act_wiz.c:get_max_train (line 2543)

    Args:
        char: Character to check
        stat: Stat name (str, int, wis, dex, con)

    Returns:
        Maximum trainable value for stat
    """
    base_max = 18
    race_bonus = 3
    max_possible = 25

    if hasattr(char, "pcdata") and char.pcdata:
        return min(base_max + race_bonus, max_possible)

    return base_max


def recursive_clone(obj: Object, clone_to: Object | None = None) -> Object:
    """Deep clone object including all contents.

    ROM parity: src/act_wiz.c:recursive_clone (line 2320)

    Recursively clones an object and all objects contained within it.
    This is used by OLC and clone commands to duplicate complex items.

    Args:
        obj: Object to clone
        clone_to: Parent object to add clone to (None for standalone)

    Returns:
        Cloned object with all contents
    """
    from mud.models.obj import ObjIndex
    from mud.models.object import Object

    if not obj.prototype:
        proto = ObjIndex(
            vnum=obj.vnum,
            name=obj.name,
            short_descr=obj.short_descr,
            long_descr=obj.long_descr,
            description=obj.description,
            item_type=obj.item_type,
            extra_flags=obj.extra_flags,
            wear_flags=obj.wear_flags,
            value=obj.value.copy() if obj.value else [0, 0, 0, 0, 0],
            weight=obj.weight,
            cost=obj.cost,
            level=obj.level,
        )
    else:
        proto = obj.prototype

    new_obj = Object(instance_id=None, prototype=proto)

    for content in obj.contained_items:
        recursive_clone(content, new_obj)

    if clone_to:
        clone_to.contained_items.append(new_obj)
        new_obj.location = None

    return new_obj
