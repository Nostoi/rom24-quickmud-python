from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Condition, LEVEL_IMMORTAL


__all__ = ["gain_condition"]


def _send_to_char(character: Character, message: str) -> None:
    """Append a message to the character if a buffer is available."""

    messages = getattr(character, "messages", None)
    if isinstance(messages, list):
        messages.append(message)


def gain_condition(character: Character, condition: Condition, delta: int) -> None:
    """Adjust a player's condition slot, mirroring ROM gain_condition."""

    if delta == 0:
        return

    if getattr(character, "is_npc", False):
        return

    level = int(getattr(character, "level", 0) or 0)
    if level >= LEVEL_IMMORTAL:
        return

    pcdata = getattr(character, "pcdata", None)
    if pcdata is None:
        return

    slots = getattr(pcdata, "condition", None)
    if not isinstance(slots, list):
        return

    index = int(condition)
    while len(slots) <= index:
        slots.append(0)

    current = int(slots[index])
    if current == -1:
        return

    updated = max(0, min(48, current + delta))
    slots[index] = updated

    if updated != 0:
        return

    if condition is Condition.HUNGER:
        _send_to_char(character, "You are hungry.")
    elif condition is Condition.THIRST:
        _send_to_char(character, "You are thirsty.")
    elif condition is Condition.DRUNK and current != 0:
        _send_to_char(character, "You are sober.")
