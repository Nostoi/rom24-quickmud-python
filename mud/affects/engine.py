from __future__ import annotations

from mud.handler import affect_remove
from mud.models.character import Character
from mud.utils import rng_mm

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
                level = int(getattr(affect, "level", 0) or 0)
                if level > 0 and rng_mm.number_range(0, 4) == 0:
                    affect.level = level - 1  # mirroring ROM src/update.c:765-768
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

            # ROM src/handler.c:1317 affect_remove — affect_modify(FALSE)
            # subtracts the stat mod and clears the bitvector; affect_check
            # re-sets the bit only if another affect still provides it.
            # INV-015 fix (2.9.7): was a bare `affected.remove(affect)`,
            # which leaked stat mods and bitvectors for any AffectData
            # whose `type` is an integer SN (the ROM-canonical form).
            #
            # Python has a parallel apply path: `Character.apply_spell_effect`
            # already calls `_apply_stat_modifier(+mod)`, mirrors a shadow
            # AffectData into `ch.affected`, and on expiry the
            # `remove_spell_effect` branch below unwinds via
            # `_apply_stat_modifier(-mod)`. For those entries the shadow
            # AffectData's modifier was NEVER applied via `affect_modify(True)`,
            # so calling `affect_modify(False)` on it would double-unwind.
            # Split: spell_effects-managed entries get bare list removal;
            # raw ROM-canonical AffectData routes through affect_remove.
            spell_effects_managed = isinstance(spell_name, str) and spell_name in effects
            if affect in affected:
                if spell_effects_managed:
                    affected.remove(affect)
                else:
                    affect_remove(character, affect)

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
