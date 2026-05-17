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

    affected = getattr(character, "affected", None)
    if isinstance(affected, list) and affected:
        touched_names: set[str] = set()
        ordered_affects = list(affected)

        for index, affect in enumerate(ordered_affects):
            duration = int(getattr(affect, "duration", 0) or 0)
            if duration > 0:
                affect.duration = duration - 1
                spell_name = getattr(affect, "type", None)
                if isinstance(spell_name, str) and spell_name in effects:
                    touched_names.add(spell_name)
                continue
            if duration < 0:
                continue

            spell_name = getattr(affect, "type", None)
            next_affect = ordered_affects[index + 1] if index + 1 < len(ordered_affects) else None
            should_emit = (
                next_affect is None
                or getattr(next_affect, "type", None) != spell_name
                or int(getattr(next_affect, "duration", 0) or 0) > 0
            )

            if affect in affected:
                affected.remove(affect)

            if isinstance(spell_name, str) and spell_name in effects:
                touched_names.add(spell_name)
                wear_off = getattr(effects[spell_name], "wear_off_message", None)
                if should_emit and wear_off:
                    messages.append(f"{wear_off}{ROM_NEWLINE}")

        for spell_name in touched_names:
            remaining = [
                affect
                for affect in getattr(character, "affected", [])
                if getattr(affect, "type", None) == spell_name
            ]
            if remaining:
                primary = remaining[0]
                effect = effects.get(spell_name)
                if effect is not None:
                    effect.duration = int(getattr(primary, "duration", 0) or 0)
                    effect.level = int(getattr(primary, "level", 0) or 0)
                continue
            character.remove_spell_effect(spell_name)

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
