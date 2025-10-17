from __future__ import annotations

import shlex
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto

from mud.admin_logging.admin import is_log_all_enabled, log_admin_command
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.social import social_registry
from mud.net.session import Session
from mud.wiznet import cmd_wiznet

from .admin_commands import (
    cmd_allow,
    cmd_ban,
    cmd_banlist,
    cmd_deny,
    cmd_holylight,
    cmd_incognito,
    cmd_log,
    cmd_newlock,
    cmd_qmconfig,
    cmd_telnetga,
    cmd_permban,
    cmd_spawn,
    cmd_teleport,
    cmd_unban,
    cmd_who,
    cmd_wizlock,
)
from .advancement import do_practice, do_train
from .alias_cmds import do_alias, do_prefi, do_prefix, do_unalias
from .build import cmd_redit, handle_redit_command
from .combat import do_kick, do_kill, do_rescue
from .communication import (
    do_auction,
    do_answer,
    do_clantalk,
    do_gossip,
    do_grats,
    do_immtalk,
    do_music,
    do_question,
    do_quote,
    do_reply,
    do_say,
    do_shout,
    do_tell,
)
from .healer import do_heal
from .help import do_help
from .imc import do_imc
from .inspection import do_exits, do_look, do_scan
from .inventory import do_drop, do_equipment, do_get, do_inventory
from .movement import do_down, do_east, do_enter, do_north, do_south, do_up, do_west
from .notes import do_board, do_note
from .shop import do_buy, do_list, do_sell, do_value
from .socials import perform_social

CommandFunc = Callable[[Character, str], str]


class LogLevel(Enum):
    """Mirror ROM command log levels."""

    NORMAL = auto()
    ALWAYS = auto()
    NEVER = auto()


@dataclass(frozen=True)
class Command:
    name: str
    func: CommandFunc
    aliases: tuple[str, ...] = ()
    admin_only: bool = False
    min_position: Position = Position.DEAD
    log_level: LogLevel = LogLevel.NORMAL


COMMANDS: list[Command] = [
    # Movement (require standing per ROM)
    Command(
        "north",
        do_north,
        aliases=("n",),
        min_position=Position.STANDING,
        log_level=LogLevel.NEVER,
    ),
    Command(
        "east",
        do_east,
        aliases=("e",),
        min_position=Position.STANDING,
        log_level=LogLevel.NEVER,
    ),
    Command(
        "south",
        do_south,
        aliases=("s",),
        min_position=Position.STANDING,
        log_level=LogLevel.NEVER,
    ),
    Command(
        "west",
        do_west,
        aliases=("w",),
        min_position=Position.STANDING,
        log_level=LogLevel.NEVER,
    ),
    Command(
        "up",
        do_up,
        aliases=("u",),
        min_position=Position.STANDING,
        log_level=LogLevel.NEVER,
    ),
    Command(
        "down",
        do_down,
        aliases=("d",),
        min_position=Position.STANDING,
        log_level=LogLevel.NEVER,
    ),
    Command("enter", do_enter, min_position=Position.STANDING),
    # Common actions
    Command("look", do_look, aliases=("l",), min_position=Position.RESTING),
    Command("exits", do_exits, aliases=("ex",), min_position=Position.RESTING),
    Command("get", do_get, aliases=("g",), min_position=Position.RESTING),
    Command("drop", do_drop, min_position=Position.RESTING),
    Command("inventory", do_inventory, aliases=("inv",), min_position=Position.DEAD),
    Command("equipment", do_equipment, aliases=("eq",), min_position=Position.DEAD),
    # Communication
    Command("say", do_say, aliases=("'",), min_position=Position.RESTING),
    Command("tell", do_tell, min_position=Position.RESTING),
    Command("reply", do_reply, min_position=Position.RESTING),
    Command("shout", do_shout, min_position=Position.RESTING),
    Command("auction", do_auction, min_position=Position.RESTING),
    Command("gossip", do_gossip, min_position=Position.RESTING),
    Command("grats", do_grats, min_position=Position.RESTING),
    Command("quote", do_quote, min_position=Position.RESTING),
    Command("question", do_question, min_position=Position.RESTING),
    Command("answer", do_answer, min_position=Position.RESTING),
    Command("music", do_music, min_position=Position.RESTING),
    Command("clan", do_clantalk, min_position=Position.SLEEPING),
    Command("immtalk", do_immtalk, aliases=(":",), min_position=Position.DEAD),
    # Combat
    Command("kill", do_kill, aliases=("attack",), min_position=Position.FIGHTING),
    Command("kick", do_kick, min_position=Position.FIGHTING),
    Command("rescue", do_rescue, min_position=Position.FIGHTING),
    # Info
    Command("scan", do_scan, min_position=Position.SLEEPING),
    # Shops
    Command("list", do_list, min_position=Position.RESTING),
    Command("buy", do_buy, min_position=Position.RESTING),
    Command("sell", do_sell, min_position=Position.RESTING),
    Command("value", do_value, min_position=Position.RESTING),
    Command("heal", do_heal, min_position=Position.RESTING),
    # Advancement
    Command("practice", do_practice, min_position=Position.SLEEPING),
    Command("train", do_train, min_position=Position.RESTING),
    # Boards/Notes/Help
    Command("board", do_board, min_position=Position.SLEEPING),
    Command("note", do_note, min_position=Position.DEAD),
    Command("help", do_help, min_position=Position.DEAD),
    Command("telnetga", cmd_telnetga, min_position=Position.DEAD),
    # IMC and aliasing
    Command("imc", do_imc, min_position=Position.DEAD),
    Command("alias", do_alias, min_position=Position.DEAD),
    Command("unalias", do_unalias, min_position=Position.DEAD),
    Command("prefix", do_prefix, min_position=Position.DEAD),
    Command("prefi", do_prefi, min_position=Position.DEAD),
    # Admin (leave position as DEAD; admin-only gating applies separately)
    Command("@who", cmd_who, admin_only=True),
    Command("@teleport", cmd_teleport, admin_only=True, log_level=LogLevel.ALWAYS),
    Command("@spawn", cmd_spawn, admin_only=True, log_level=LogLevel.ALWAYS),
    Command("ban", cmd_ban, admin_only=True, log_level=LogLevel.ALWAYS),
    Command("permban", cmd_permban, admin_only=True, log_level=LogLevel.ALWAYS),
    Command("deny", cmd_deny, admin_only=True, log_level=LogLevel.ALWAYS),
    Command("allow", cmd_allow, admin_only=True, log_level=LogLevel.ALWAYS),
    Command("unban", cmd_unban, admin_only=True, log_level=LogLevel.ALWAYS),
    Command("banlist", cmd_banlist, admin_only=True),
    Command("log", cmd_log, admin_only=True, log_level=LogLevel.ALWAYS),
    Command("incognito", cmd_incognito, admin_only=True),
    Command("holylight", cmd_holylight, admin_only=True),
    Command("qmconfig", cmd_qmconfig, admin_only=True, log_level=LogLevel.ALWAYS),
    Command("@redit", cmd_redit, admin_only=True),
    Command("wizlock", cmd_wizlock, admin_only=True, log_level=LogLevel.ALWAYS),
    Command("newlock", cmd_newlock, admin_only=True, log_level=LogLevel.ALWAYS),
    Command("wiznet", cmd_wiznet, admin_only=True),
]


COMMAND_INDEX: dict[str, Command] = {}
for cmd in COMMANDS:
    COMMAND_INDEX[cmd.name] = cmd
    for alias in cmd.aliases:
        COMMAND_INDEX[alias] = cmd


def resolve_command(name: str) -> Command | None:
    name = name.lower()
    if name in COMMAND_INDEX:
        return COMMAND_INDEX[name]
    # ROM str_prefix behavior: choose the first command in table order
    # whose name starts with the provided prefix. If none match, return None.
    matches = [cmd for cmd in COMMANDS if cmd.name.startswith(name)]
    return matches[0] if matches else None


def _split_command_and_args(input_str: str) -> tuple[str, str]:
    """Extract the leading command token and its remaining arguments."""

    stripped = input_str.lstrip()
    if not stripped:
        return "", ""

    first = stripped[0]
    # Handle special case for @ commands (admin commands like @teleport, @who, etc.)
    if first == "@":
        # For @ commands, split normally by whitespace to preserve full command names
        try:
            parts = shlex.split(stripped)
            if not parts:
                return "", ""
            head = parts[0]
            tail = " ".join(parts[1:]) if len(parts) > 1 else ""
            return head, tail
        except ValueError:
            fallback = stripped.split(None, 1)
            if not fallback:
                return "", ""
            head = fallback[0]
            tail = fallback[1] if len(fallback) > 1 else ""
            return head, tail
    elif not first.isalnum():
        return first, stripped[1:].lstrip()

    try:
        parts = shlex.split(stripped)
        if not parts:
            return "", ""
        head = parts[0]
        tail = " ".join(parts[1:]) if len(parts) > 1 else ""
        return head, tail
    except ValueError:
        fallback = stripped.split(None, 1)
        if not fallback:
            return "", ""
        head = fallback[0]
        tail = fallback[1] if len(fallback) > 1 else ""
        return head, tail


def _expand_aliases(char: Character, input_str: str, *, max_depth: int = 5) -> tuple[str, bool]:
    """Expand the first token using per-character aliases, up to max_depth.

    Returns the expanded string and whether any alias substitution occurred.
    """

    s = input_str
    alias_used = False
    for _ in range(max_depth):
        head, tail = _split_command_and_args(s)
        if not head:
            return s, alias_used
        expansion = char.aliases.get(head)
        if not expansion:
            return s, alias_used
        alias_used = True
        s = expansion + (" " + tail if tail else "")
    return s, alias_used


def process_command(char: Character, input_str: str) -> str:
    session = getattr(char, "desc", None)
    if isinstance(session, Session) and session.editor == "redit":
        return handle_redit_command(char, session, input_str)

    if not input_str.strip():
        return "What?"
    trimmed = input_str.lstrip()
    core = trimmed.rstrip()
    trailing_ws = trimmed[len(core) :]
    prefix_text = (getattr(char, "prefix", "") or "").strip()
    prefixed_applied = False
    if prefix_text:
        head, _ = _split_command_and_args(core)
        lowered = head.lower()
        blocked_prefixes = ("alias", "una", "pref")
        if lowered and not any(lowered.startswith(block) for block in blocked_prefixes):
            core = f"{prefix_text} {core}" if core else prefix_text
            prefixed_applied = True
    if core:
        raw_parts = core.split(None, 1)
        raw_head = raw_parts[0]
        raw_tail = raw_parts[1] if len(raw_parts) > 1 else ""
    else:
        raw_head = ""
        raw_tail = ""
    expanded, alias_used = _expand_aliases(char, core)
    cmd_name, arg_str = _split_command_and_args(expanded)
    if not cmd_name:
        return "What?"
    command = resolve_command(cmd_name)
    if alias_used:
        log_line = expanded + trailing_ws
    elif prefixed_applied:
        log_line = core + trailing_ws
    else:
        log_line = trimmed
    log_all_enabled = is_log_all_enabled()
    log_allowed = True
    should_log = False
    if command:
        if command.log_level is LogLevel.NEVER and not log_all_enabled:
            log_allowed = False
        if command.log_level is LogLevel.ALWAYS:
            should_log = True
    is_player = not getattr(char, "is_npc", False)
    if is_player and getattr(char, "log_commands", False):
        should_log = True
    if log_all_enabled:
        should_log = True
    if should_log and log_allowed and log_line:
        try:
            log_admin_command(
                getattr(char, "name", "?"),
                log_line,
                character=char,
            )
        except Exception:
            # Logging must never break command execution.
            pass
    if not command:
        social = social_registry.get(cmd_name.lower())
        if social:
            return perform_social(char, cmd_name, arg_str)
        return "Huh?"
    if command.admin_only and not getattr(char, "is_admin", False):
        return "You do not have permission to use this command."
    # Position gating (ROM-compatible messages)
    if char.position < command.min_position:
        pos = char.position
        if pos == Position.DEAD:
            return "Lie still; you are DEAD."
        if pos in (Position.MORTAL, Position.INCAP):
            return "You are hurt far too bad for that."
        if pos == Position.STUNNED:
            return "You are too stunned to do that."
        if pos == Position.SLEEPING:
            return "In your dreams, or what?"
        if pos == Position.RESTING:
            return "Nah... You feel too relaxed..."
        if pos == Position.SITTING:
            return "Better stand up first."
        if pos == Position.FIGHTING:
            return "No way!  You are still fighting!"
        # Fallback (should not happen)
        return "You can't do that right now."
    command_args = arg_str
    if command.name == "prefix":
        command_args = raw_tail
    return command.func(char, command_args)


def run_test_session() -> list[str]:
    from mud.spawning.obj_spawner import spawn_object
    from mud.world import create_test_character, initialize_world

    initialize_world("area/area.lst")
    char = create_test_character("Tester", 3001)
    # Ensure sufficient movement points for the scripted walk
    char.move = char.max_move = 100
    sword = spawn_object(3022)
    if sword:
        char.room.add_object(sword)
    commands = ["look", "get sword", "north", "say hello"]
    outputs = []
    for line in commands:
        outputs.append(process_command(char, line))
    return outputs
