from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import LEVEL_HERO


ROM_NEWLINE = "\n\r"
_COLUMNS_PER_ROW = 6
_COLUMN_WIDTH = 12


def _get_trust(char: Character) -> int:
    trust = int(getattr(char, "trust", 0) or 0)
    level = int(getattr(char, "level", 0) or 0)
    return trust if trust > 0 else level


def _visible_command_names(
    char: Character,
    *,
    min_level: int = 0,
    max_level: int | None = LEVEL_HERO - 1,
) -> list[str]:
    from mud.commands.dispatcher import COMMANDS

    trust = _get_trust(char)
    names: list[str] = []
    for command in COMMANDS:
        if not command.show:
            continue
        level = command.min_trust
        if level < min_level:
            continue
        if level > trust:
            continue
        if max_level is not None and level > max_level:
            continue
        names.append(command.name)
    return names


def _chunk_commands(names: list[str]) -> list[str]:
    if not names:
        return []
    rows: list[str] = []
    current: list[str] = []
    for index, name in enumerate(names, start=1):
        current.append(f"{name:<{_COLUMN_WIDTH}}")
        if index % _COLUMNS_PER_ROW == 0:
            rows.append("".join(current).rstrip())
            current = []
    if current:
        rows.append("".join(current).rstrip())
    return rows


def do_commands(char: Character, args: str) -> str:
    """List mortal-accessible commands in ROM's six-column layout."""

    visible = _visible_command_names(char)
    rows = _chunk_commands(visible)
    if not rows:
        return ""
    return ROM_NEWLINE.join(rows) + ROM_NEWLINE


def do_wizhelp(char: Character, args: str) -> str:
    """List immortal commands available at or above hero level."""

    visible = _visible_command_names(char, min_level=LEVEL_HERO, max_level=None)
    rows = _chunk_commands(visible)
    if not rows:
        return ""
    return ROM_NEWLINE.join(rows) + ROM_NEWLINE

