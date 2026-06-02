from __future__ import annotations

from typing import Any

from mud.models.character import Character
from mud.models.constants import AffectFlag, CommFlag, Position
from mud.models.social import find_social
from mud.utils import rng_mm
from mud.utils.act import act_format, act_to_room
from mud.utils.messaging import push_message
from mud.world.char_find import get_char_room


def _act_to_char(recipient: Any, fmt: str, actor: Any, *, arg2: Any | None = None) -> None:
    """Render + deliver one ROM ``act(..., TO_CHAR/TO_VICT)`` line.

    Mirrors the single-recipient slice of ROM ``act_new`` (``src/comm.c:2230-2385``):
    format *fmt* through ``act_format`` so ``$n``/``$N`` are rendered through
    per-recipient ``PERS`` masking (INV-027), deliver via the single-delivery
    ``push_message`` channel, then dispatch ``TRIG_ACT`` to an NPC recipient when
    the global ``MOBtrigger`` flag is enabled (INV-025).
    """
    import mud.mobprog as mobprog

    message = act_format(fmt, recipient=recipient, actor=actor, arg2=arg2)
    push_message(recipient, message)
    if bool(getattr(mobprog, "MOBtrigger", True)) and getattr(recipient, "is_npc", False):
        mobprog.mp_act_trigger(message, recipient, actor, None, arg2, mobprog.Trigger.ACT)


def perform_social(char: Character, name: str, arg: str) -> str:
    # mirroring ROM src/interp.c:584-592 — str_prefix lookup so partial
    # social names ("gigg" → "giggle") resolve in load order.
    social = find_social(name)
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
        # mirroring ROM src/interp.c:637 — do_social resolves the target via
        # get_char_room (src/handler.c:2194-2214): "self"/own-name resolve to ch
        # (HANDLER-001), the in_room->people loop is can_see + is_name gated so an
        # unseen target → NULL → "They aren't here." (INTERP-026, no presence
        # leak), and N.name syntax ("2.guard") is honored. Either self path →
        # victim == ch → char_auto/others_auto (INTERP-025).
        victim = get_char_room(char, arg)
    if victim and victim is not char:
        # mirroring ROM src/interp.c:648-650 — TO_NOTVICT excludes the victim;
        # TO_CHAR/TO_VICT go to the directed recipient. act_to_room / _act_to_char
        # render $n/$N through per-recipient PERS masking and dispatch TRIG_ACT.
        _act_to_char(char, social.char_found, char, arg2=victim)
        act_to_room(char.room, social.others_found, char, arg2=victim, exclude=victim)
        _act_to_char(victim, social.vict_found, char, arg2=victim)
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
                # mirroring ROM src/interp.c:668-673 — actor/victim swapped.
                act_to_room(victim.room, social.others_found, victim, arg2=char, exclude=char)
                _act_to_char(victim, social.char_found, victim, arg2=char)
                _act_to_char(char, social.vict_found, victim, arg2=char)
            elif roll <= 12:
                # mirroring ROM src/interp.c:680-682 — slap.
                act_to_room(victim.room, "$n slaps $N.", victim, arg2=char, exclude=char)
                _act_to_char(victim, "You slap $N.", victim, arg2=char)
                _act_to_char(char, "$n slaps you.", victim, arg2=char)
            # 13..15 falls through silently (ROM has no case for these).
    elif arg and victim is char:
        # mirroring ROM src/interp.c:643-644 — TO_ROOM (excludes only the actor).
        _act_to_char(char, social.char_auto, char, arg2=victim)
        act_to_room(char.room, social.others_auto, char, arg2=victim)
    elif arg and not victim:
        # mirroring ROM src/interp.c:637-640 — get_char_room → NULL emits
        # the literal "They aren't here." There is no `not_found` field in
        # ROM's social_table; the message is hard-coded in check_social.
        push_message(char, "They aren't here.")
    else:
        # mirroring ROM src/interp.c:634-635 — TO_ROOM (excludes only the actor).
        _act_to_char(char, social.char_no_arg, char)
        act_to_room(char.room, social.others_no_arg, char)
    return ""
