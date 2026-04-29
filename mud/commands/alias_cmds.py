from __future__ import annotations

from mud.models.character import Character
from mud.utils.text import smash_tilde

MAX_ALIAS = 5


def _one_argument(argument: str) -> tuple[str, str]:
    """Parse one ROM-style lowercased argument token."""
    stripped = argument.lstrip()
    if not stripped:
        return "", ""

    sentinel = " "
    index = 0
    if stripped[index] in ("'", '"'):
        sentinel = stripped[index]
        index += 1

    head_chars: list[str] = []
    length = len(stripped)
    while index < length:
        char = stripped[index]
        if (sentinel == " " and char.isspace()) or char == sentinel:
            index += 1
            break
        head_chars.append(char.lower())
        index += 1

    while index < length and stripped[index].isspace():
        index += 1

    return "".join(head_chars), stripped[index:]


def _get_alias_owner(char: Character) -> Character:
    desc = getattr(char, "desc", None)
    if desc is None:
        return char
    original = getattr(desc, "original", None)
    return original if original is not None else char


def _is_rom_prefix(argument: str, target: str) -> bool:
    return bool(argument) and target.lower().startswith(argument.lower())


def _format_alias_listing(aliases: dict[str, str]) -> str:
    if not aliases:
        return "You have no aliases defined.\n\r"

    lines = ["Your current aliases are:\n\r"]
    for name, expansion in aliases.items():
        lines.append(f"    {name}:  {expansion}\n\r")
    return "".join(lines)


def do_alias(char: Character, args: str = "") -> str:
    """Create, inspect, or list aliases.

    Mirrors ROM `src/alias.c:102-220`.
    """
    owner = _get_alias_owner(char)
    if getattr(owner, "is_npc", False):
        return ""

    argument = smash_tilde(args)
    name, expansion = _one_argument(argument)

    if not name:
        return _format_alias_listing(owner.aliases)

    if name.startswith("una") or name == "alias":
        return "Sorry, that word is reserved.\n\r"

    if " " in name or '"' in name or "'" in name:
        return "The word to be aliased should not contain a space, a tick or a double-quote.\n\r"

    if not expansion:
        if name in owner.aliases:
            return f"{name} aliases to '{owner.aliases[name]}'.\n\r"
        return "That alias is not defined.\n\r"

    expansion_head, _ = _one_argument(expansion)
    if _is_rom_prefix(expansion_head, "delete") or _is_rom_prefix(expansion_head, "prefix"):
        return "That shall not be done!\n\r"

    if name in owner.aliases:
        owner.aliases[name] = expansion
        return f"{name} is now realiased to '{expansion}'.\n\r"

    if len(owner.aliases) >= MAX_ALIAS:
        return "Sorry, you have reached the alias limit.\n\r"

    owner.aliases[name] = expansion
    return f"{name} is now aliased to '{expansion}'.\n\r"


def do_unalias(char: Character, args: str = "") -> str:
    """Remove an alias by name.

    Mirrors ROM `src/alias.c:224-274`.
    """
    owner = _get_alias_owner(char)
    if getattr(owner, "is_npc", False):
        return ""

    name, _ = _one_argument(args)
    if not name:
        return "Unalias what?\n\r"

    if name not in owner.aliases:
        return "No alias of that name to remove.\n\r"

    del owner.aliases[name]
    return "Alias removed.\n\r"


def do_prefi(char: Character, args: str = "") -> str:
    """ROM compatibility helper to forbid prefix abbreviations."""

    return "You cannot abbreviate the prefix command."


def do_prefix(char: Character, args: str = "") -> str:
    """Set, change, or clear the per-character command prefix."""

    existing = (char.prefix or "").strip()
    text = args.strip()
    if not text:
        if not existing:
            return "You have no prefix to clear."
        char.prefix = ""
        return "Prefix removed."

    char.prefix = text
    if existing:
        return f"Prefix changed to {text}."
    return f"Prefix set to {text}."
