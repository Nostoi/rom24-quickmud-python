from __future__ import annotations

from mud.models.character import Character
from mud.models.help import help_registry


def do_help(ch: Character, args: str) -> str:
    topic = args.strip().lower()
    if not topic:
        return "Help what?"
    entry = help_registry.get(topic)
    if not entry:
        return "No help on that word."
    return entry.text
