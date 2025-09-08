from __future__ import annotations

from typing import Dict

from mud.models.character import Character


def _format_aliases(aliases: Dict[str, str]) -> str:
    if not aliases:
        return "No aliases defined."
    parts = [f"{k} -> {v}" for k, v in sorted(aliases.items())]
    return "Aliases: " + ", ".join(parts)


def do_alias(char: Character, args: str = "") -> str:
    """Create or list aliases.

    Usage:
      alias                 # list
      alias <name> <exp>    # set/replace
    """
    if not args.strip():
        return _format_aliases(char.aliases)
    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        return "Usage: alias <name> <expansion>"
    name, expansion = parts[0].strip(), parts[1].strip()
    # Prevent self-referential aliases by simple guard.
    if name.lower() in ("alias", "unalias"):
        return "You cannot alias that command."
    char.aliases[name] = expansion
    return f"Alias set: {name} -> {expansion}"


def do_unalias(char: Character, args: str = "") -> str:
    """Remove an alias by name."""
    name = args.strip()
    if not name:
        return "Usage: unalias <name>"
    if name in char.aliases:
        del char.aliases[name]
        return f"Removed alias: {name}"
    return "No such alias."

