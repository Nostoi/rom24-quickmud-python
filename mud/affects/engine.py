from __future__ import annotations

from mud.models.character import Character

ROM_NEWLINE = "\n\r"

__all__ = ["tick_spell_effects"]


def tick_spell_effects(character: Character) -> list[str]:
    """Reduce active spell durations and collect wear-off messages."""

    messages: list[str] = []
    effects = getattr(character, "spell_effects", {})
    if not isinstance(effects, dict):
        return messages

    for name, effect in list(effects.items()):
        duration = int(getattr(effect, "duration", 0) or 0)
        if duration > 0:
            effect.duration = duration - 1
        if getattr(effect, "duration", 0) < 0:
            continue
        if getattr(effect, "duration", 0) > 0:
            continue

        wear_off = getattr(effect, "wear_off_message", None)
        character.remove_spell_effect(name)
        if wear_off:
            messages.append(f"{wear_off}{ROM_NEWLINE}")

    return messages
