from mud.models.character import Character
from mud.world.look import look


def do_look(char: Character, args: str = "") -> str:
    return look(char)
