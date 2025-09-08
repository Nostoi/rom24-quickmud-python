from __future__ import annotations
from dataclasses import dataclass
import shlex
from typing import Callable, Dict, List, Optional

from mud.models.character import Character
from .movement import do_north, do_south, do_east, do_west, do_up, do_down
from .inspection import do_look
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

CommandFunc = Callable[[Character, str], str]


@dataclass(frozen=True)
class Command:
    name: str
    func: CommandFunc
    aliases: tuple[str, ...] = ()
    admin_only: bool = False


COMMANDS: List[Command] = [
    Command("look", do_look, aliases=("l",)),
    Command("north", do_north, aliases=("n",)),
    Command("south", do_south, aliases=("s",)),
    Command("east", do_east, aliases=("e",)),
    Command("west", do_west, aliases=("w",)),
    Command("up", do_up, aliases=("u",)),
    Command("down", do_down, aliases=("d",)),
    Command("get", do_get, aliases=("g",)),
    Command("drop", do_drop),
    Command("inventory", do_inventory, aliases=("inv",)),
    Command("equipment", do_equipment, aliases=("eq",)),
    Command("say", do_say),
    Command("tell", do_tell),
    Command("shout", do_shout),
    Command("kill", do_kill, aliases=("attack",)),
    Command("list", do_list),
    Command("buy", do_buy),
    Command("sell", do_sell),
    Command("practice", do_practice),
    Command("train", do_train),
    Command("board", do_board),
    Command("note", do_note),
    Command("help", do_help),
    Command("imc", do_imc),
    Command("alias", do_alias),
    Command("unalias", do_unalias),
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
    matches = [cmd for cmd in COMMANDS if cmd.name.startswith(name)]
    if len(matches) == 1:
        return matches[0]
    return None


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
    sword = spawn_object(3022)
    if sword:
        char.room.add_object(sword)
    commands = ["look", "get sword", "north", "say hello"]
    outputs = []
    for line in commands:
        outputs.append(process_command(char, line))
    return outputs
