"""
Consider command - assess mob difficulty relative to player level.

ROM Reference: src/act_info.c do_consider (lines 2469-2510)
"""

from __future__ import annotations

from mud.commands.combat import _kill_safety_message
from mud.models.character import Character
from mud.utils.act import capitalize_act_line
from mud.world.char_find import get_char_room


def do_consider(char: Character, args: str) -> str:
    """
    Assess the difficulty of fighting a mob.

    ROM Reference: src/act_info.c lines 2469-2510

    Usage: consider <target>

    Shows relative difficulty based on level difference:
    - 10+ levels below: "You can kill $N naked and weaponless."
    - 5-9 levels below: "$N is no match for you."
    - 2-4 levels below: "$N looks like an easy kill."
    - -1 to +1 levels: "The perfect match!"
    - 2-4 levels above: "$N says 'Do you feel lucky, punk?'."
    - 5-9 levels above: "$N laughs at you mercilessly."
    - 10+ levels above: "Death will thank you for your gift."
    """
    args = args.strip()

    if not args:
        return "Consider killing whom?"

    # Find target in room
    victim = get_char_room(char, args)
    if not victim:
        return "They're not here."

    # INV-050: route through the faithful ROM is_safe() mirror
    # (combat._kill_safety_message, src/fight.c:1018-1124) rather than the silent
    # bool combat.safety.is_safe. ROM is_safe writes its OWN context line via
    # send_to_char/act BEFORE returning TRUE (e.g. "The shopkeeper wouldn't like
    # that."), then do_consider appends "Don't even think about it."
    # (src/act_info.c:2490-2493). The silent bool dropped that context line; a
    # non-None return from the mirror == ROM is_safe returning TRUE.
    safety_message = _kill_safety_message(char, victim)
    if safety_message is not None:
        return f"{safety_message}\nDon't even think about it."

    # Calculate level difference - ROM src/act_info.c line 2492
    char_level = getattr(char, "level", 1)
    victim_level = getattr(victim, "level", 1)
    diff = victim_level - char_level

    # Get victim's name for message
    victim_name = getattr(victim, "short_descr", None) or getattr(victim, "name", "someone")

    # ROM exact messages based on level difference - src/act_info.c lines 2494-2507
    if diff <= -10:
        msg = f"You can kill {victim_name} naked and weaponless."
    elif diff <= -5:
        msg = f"{victim_name} is no match for you."
    elif diff <= -2:
        msg = f"{victim_name} looks like an easy kill."
    elif diff <= 1:
        msg = "The perfect match!"
    elif diff <= 4:
        msg = f"{victim_name} says 'Do you feel lucky, punk?'."
    elif diff <= 9:
        msg = f"{victim_name} laughs at you mercilessly."
    else:
        msg = "Death will thank you for your gift."

    # CONSIDER-001: ROM renders the line via act(msg, ch, NULL, victim, TO_CHAR)
    # and act_new upper-cases buf[0] (src/comm.c:2379). For the messages that
    # begin with $N, that capitalizes the (lowercase) victim short_descr's first
    # letter; the baked render above otherwise leaves it lowercase. The caster
    # provably can see the victim (get_char_room succeeded), so the baked name
    # equals ROM's PERS(victim, ch); only the buf[0] cap was missing.
    return capitalize_act_line(msg)
