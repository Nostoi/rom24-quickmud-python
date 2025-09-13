from __future__ import annotations
from dataclasses import dataclass
import shlex
from typing import Callable, Dict, List, Optional

from mud.models.character import Character
from .movement import do_north, do_south, do_east, do_west, do_up, do_down, do_enter
from .inspection import do_look, do_scan, do_exits
from .inventory import do_get, do_drop, do_inventory, do_equipment
from .communication import do_say, do_tell, do_shout
from .combat import do_kill
from .admin_commands import (
    cmd_who,
    cmd_teleport,
    cmd_spawn,
    cmd_ban,
    cmd_unban,
    cmd_banlist,
)
from .shop import do_list, do_buy, do_sell
from .healer import do_heal
from .alias_cmds import do_alias, do_unalias
from .advancement import do_practice, do_train
from .notes import do_board, do_note
from .build import cmd_redit
from .socials import perform_social
from .help import do_help
from .imc import do_imc
from mud.wiznet import cmd_wiznet
from mud.logging.admin import log_admin_command
from mud.models.social import social_registry
from mud.models.constants import Position

CommandFunc = Callable[[Character, str], str]


@dataclass(frozen=True)
class Command:
    name: str
    func: CommandFunc
    aliases: tuple[str, ...] = ()
    admin_only: bool = False
    min_position: Position = Position.DEAD


COMMANDS: List[Command] = [
    # Movement (require standing per ROM)
    Command("north", do_north, aliases=("n",), min_position=Position.STANDING),
    Command("east", do_east, aliases=("e",), min_position=Position.STANDING),
    Command("south", do_south, aliases=("s",), min_position=Position.STANDING),
    Command("west", do_west, aliases=("w",), min_position=Position.STANDING),
    Command("up", do_up, aliases=("u",), min_position=Position.STANDING),
    Command("down", do_down, aliases=("d",), min_position=Position.STANDING),
    Command("enter", do_enter, min_position=Position.STANDING),

    # Common actions
    Command("look", do_look, aliases=("l",), min_position=Position.RESTING),
    Command("exits", do_exits, aliases=("ex",), min_position=Position.RESTING),
    Command("get", do_get, aliases=("g",), min_position=Position.RESTING),
    Command("drop", do_drop, min_position=Position.RESTING),
    Command("inventory", do_inventory, aliases=("inv",), min_position=Position.DEAD),
    Command("equipment", do_equipment, aliases=("eq",), min_position=Position.DEAD),

    # Communication
    Command("say", do_say, min_position=Position.RESTING),
    Command("tell", do_tell, min_position=Position.RESTING),
    Command("shout", do_shout, min_position=Position.RESTING),

    # Combat
    Command("kill", do_kill, aliases=("attack",), min_position=Position.FIGHTING),

    # Info
    Command("scan", do_scan, min_position=Position.SLEEPING),

    # Shops
    Command("list", do_list, min_position=Position.RESTING),
    Command("buy", do_buy, min_position=Position.RESTING),
    Command("sell", do_sell, min_position=Position.RESTING),
    Command("heal", do_heal, min_position=Position.RESTING),

    # Advancement
    Command("practice", do_practice, min_position=Position.SLEEPING),
    Command("train", do_train, min_position=Position.RESTING),

    # Boards/Notes/Help
    Command("board", do_board, min_position=Position.SLEEPING),
    Command("note", do_note, min_position=Position.DEAD),
    Command("help", do_help, min_position=Position.DEAD),

    # IMC and aliasing
    Command("imc", do_imc, min_position=Position.DEAD),
    Command("alias", do_alias, min_position=Position.DEAD),
    Command("unalias", do_unalias, min_position=Position.DEAD),

    # Admin (leave position as DEAD; admin-only gating applies separately)
    Command("@who", cmd_who, admin_only=True),
    Command("@teleport", cmd_teleport, admin_only=True),
    Command("@spawn", cmd_spawn, admin_only=True),
    Command("ban", cmd_ban, admin_only=True),
    Command("unban", cmd_unban, admin_only=True),
    Command("banlist", cmd_banlist, admin_only=True),
    Command("@redit", cmd_redit, admin_only=True),
    Command("wiznet", cmd_wiznet, admin_only=True),
]


COMMAND_INDEX: Dict[str, Command] = {}
for cmd in COMMANDS:
    COMMAND_INDEX[cmd.name] = cmd
    for alias in cmd.aliases:
        COMMAND_INDEX[alias] = cmd


def resolve_command(name: str) -> Optional[Command]:
    name = name.lower()
    if name in COMMAND_INDEX:
        return COMMAND_INDEX[name]
    # ROM str_prefix behavior: choose the first command in table order
    # whose name starts with the provided prefix. If none match, return None.
    matches = [cmd for cmd in COMMANDS if cmd.name.startswith(name)]
    return matches[0] if matches else None


def _expand_aliases(char: Character, input_str: str, *, max_depth: int = 5) -> str:
    """Expand the first token using per-character aliases, up to max_depth."""
    s = input_str
    for _ in range(max_depth):
        try:
            parts = shlex.split(s)
        except ValueError:
            return s
        if not parts:
            return s
        head, tail = parts[0], parts[1:]
        expansion = char.aliases.get(head)
        if not expansion:
            return s
        s = (expansion + (" " + " ".join(tail) if tail else "")).strip()
    return s


def process_command(char: Character, input_str: str) -> str:
    if not input_str.strip():
        return "What?"
    expanded = _expand_aliases(char, input_str)
    try:
        parts = shlex.split(expanded)
    except ValueError:
        return "Huh?"
    if not parts:
        return "What?"
    cmd_name, *args = parts
    command = resolve_command(cmd_name)
    if not command:
        social = social_registry.get(cmd_name.lower())
        if social:
            return perform_social(char, cmd_name, " ".join(args))
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
    arg_str = " ".join(args)
    # Log admin commands (accepted) to admin log for auditability.
    if command.admin_only and getattr(char, "is_admin", False):
        try:
            log_admin_command(getattr(char, "name", "?"), command.name, arg_str)
        except Exception:
            # Logging must never break command execution.
            pass
    return command.func(char, arg_str)


def run_test_session() -> list[str]:
    from mud.world import initialize_world, create_test_character
    from mud.spawning.obj_spawner import spawn_object

    initialize_world('area/area.lst')
    char = create_test_character('Tester', 3001)
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
