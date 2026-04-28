from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import AffectFlag, CommFlag, Position
from mud.models.social import expand_placeholders, social_registry
from mud.utils import rng_mm


def perform_social(char: Character, name: str, arg: str) -> str:
    social = social_registry.get(name.lower())
    if social is None or char.room is None:
        return "Huh?"
    # mirroring ROM src/interp.c:597-601 — COMM_NOEMOTE silences players
    # with "You are anti-social!"; NPCs are unaffected (IS_NPC bypass).
    if not getattr(char, "is_npc", False):
        comm_value = int(getattr(char, "comm", 0) or 0)
        if comm_value & int(CommFlag.NOEMOTE):
            return "You are anti-social!"
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
        # mirroring ROM src/interp.c:652-685 — NPC auto-react when a player
        # socials at an awake, non-charmed, non-switched NPC. number_bits(4)
        # rolls 0..15: 0..8 echo the social back, 9..12 slap, 13..15 silent.
        # Must use rng_mm.number_bits per AGENTS.md (no random.*).
        if (
            not getattr(char, "is_npc", False)
            and getattr(victim, "is_npc", False)
            and not (int(getattr(victim, "affected_by", 0) or 0) & int(AffectFlag.CHARM))
            and getattr(victim, "position", Position.STANDING) > Position.SLEEPING
            and getattr(victim, "desc", None) is None
        ):
            roll = rng_mm.number_bits(4)
            if roll <= 8:
                victim.room.broadcast(
                    expand_placeholders(social.others_found, victim, char),
                    exclude=victim,
                )
                victim.messages.append(expand_placeholders(social.char_found, victim, char))
                char.messages.append(expand_placeholders(social.vict_found, victim, char))
            elif roll <= 12:
                victim.room.broadcast(
                    expand_placeholders("$n slaps $N.", victim, char),
                    exclude=victim,
                )
                victim.messages.append(expand_placeholders("You slap $N.", victim, char))
                char.messages.append(expand_placeholders("$n slaps you.", victim, char))
            # 13..15 falls through silently (ROM has no case for these).
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
