from __future__ import annotations
from typing import Callable, Dict

from mud.models.character import Character
from .movement import do_north, do_south, do_east, do_west, do_up, do_down
from .inspection import do_look
from .inventory import do_get, do_drop, do_inventory, do_equipment
from .communication import do_say
from .combat import do_kill
from .admin_commands import cmd_who, cmd_teleport, cmd_spawn

CommandFunc = Callable[[Character, str], str]

COMMANDS: Dict[str, CommandFunc] = {
    "look": do_look,
    "north": do_north,
    "south": do_south,
    "east": do_east,
    "west": do_west,
    "up": do_up,
    "down": do_down,
    "get": do_get,
    "drop": do_drop,
    "inventory": do_inventory,
    "equipment": do_equipment,
    "say": do_say,
    "kill": do_kill,
    "attack": do_kill,
    "@who": cmd_who,
    "@teleport": cmd_teleport,
    "@spawn": cmd_spawn,
}


def process_command(char: Character, input_str: str) -> str:
    if not input_str.strip():
        return "What?"
    cmd, *rest = input_str.strip().split(maxsplit=1)
    cmd = cmd.lower()
    args = rest[0] if rest else ""
    func = COMMANDS.get(cmd)
    if not func:
        return "Huh?"
    return func(char, args)


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
