from mud.world.movement import move_character
from mud.models.character import Character


def do_north(char: Character, args: str = "") -> str:
    return move_character(char, "north")


def do_south(char: Character, args: str = "") -> str:
    return move_character(char, "south")


def do_east(char: Character, args: str = "") -> str:
    return move_character(char, "east")


def do_west(char: Character, args: str = "") -> str:
    return move_character(char, "west")


def do_up(char: Character, args: str = "") -> str:
    return move_character(char, "up")


def do_down(char: Character, args: str = "") -> str:
    return move_character(char, "down")
