from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.social import expand_placeholders, social_registry


def perform_social(char: Character, name: str, arg: str) -> str:
    social = social_registry.get(name.lower())
    if social is None or char.room is None:
        return "Huh?"
    # mirroring ROM src/interp.c:603-616 — position gates from check_social.
    # POS_SLEEPING (with the snore exception) is INTERP-019 and handled there.
    position = getattr(char, "position", Position.STANDING)
    if position == Position.DEAD:
        return "Lie still; you are DEAD."
    if position in (Position.MORTAL, Position.INCAP):
        return "You are hurt far too bad for that."
    if position == Position.STUNNED:
        return "You are too stunned to do that."
    # mirroring ROM src/interp.c:618-626 — POS_SLEEPING blocks every social
    # except "snore" (the canonical Furey exception).
    if position == Position.SLEEPING and name.lower() != "snore":
        return "In your dreams, or what?"
    victim = None
    if arg:
        arg_lower = arg.lower()
        for person in char.room.people:
            if person is char:
                continue
            if getattr(person, "name", "").lower().startswith(arg_lower):
                victim = person
                break
    if victim and victim is not char:
        char.messages.append(expand_placeholders(social.char_found, char, victim))
        char.room.broadcast(expand_placeholders(social.others_found, char, victim), exclude=char)
        victim.messages.append(expand_placeholders(social.vict_found, char, victim))
    elif arg and victim is char:
        char.messages.append(expand_placeholders(social.char_auto, char))
        char.room.broadcast(expand_placeholders(social.others_auto, char), exclude=char)
    elif arg and not victim:
        # ROM semantics: if an argument was provided but no victim is found,
        # emit the "not found" message instead of the no-arg variant.
        char.messages.append(expand_placeholders(social.not_found, char))
    else:
        char.messages.append(expand_placeholders(social.char_no_arg, char))
        char.room.broadcast(expand_placeholders(social.others_no_arg, char), exclude=char)
    return ""
