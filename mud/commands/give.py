"""
Give command - give items or money to another character.

ROM Reference: src/act_obj.c do_give (lines 678-855)
"""

from __future__ import annotations

from mud.commands.obj_manipulation import _can_drop_obj, _obj_from_char
from mud.models.character import Character, _object_carry_number, _object_carry_weight
from mud.models.constants import ActFlag
from mud.net.protocol import send_to_char
from mud.utils.act import act_format
from mud.world.char_find import get_char_room
from mud.world.movement import can_carry_n, can_carry_w, get_carry_weight
from mud.world.obj_find import get_obj_carry
from mud.world.vision import can_see_character, can_see_object


def do_give(char: Character, args: str) -> str:
    """
    Give an item or money to another character.

    ROM Reference: src/act_obj.c do_give (lines 678-855)
    """
    argument = (args or "").strip()
    if not argument:
        return "Give what to whom?"

    parts = argument.split()
    if len(parts) < 2:
        return "Give what to whom?"

    room = getattr(char, "room", None)
    if room is None:
        return "They aren't here."

    try:
        amount = int(parts[0])
        is_money = True
    except ValueError:
        amount = 0
        is_money = False

    if is_money:
        return _give_money(char, room, amount, parts)

    obj_name = parts[0]
    target_name = parts[1]

    obj = get_obj_carry(char, obj_name)
    if obj is None:
        obj = _find_equipped_obj(char, obj_name)
        if obj is not None:
            return "You must remove it first."
        return "You do not have that item."

    victim = get_char_room(char, target_name)
    if victim is None:
        return "They aren't here."

    if _has_shop(victim):
        return f"{_victim_name(victim)} tells you 'Sorry, you'll have to sell that.'"

    if not _can_drop_obj(char, obj):
        return "You can't let go of it."

    if int(getattr(victim, "carry_number", 0) or 0) + _object_carry_number(obj) > can_carry_n(victim):
        return f"{_victim_name(victim)} has { _victim_possessive(victim) } hands full."

    obj_weight = _object_carry_weight(obj)
    if get_carry_weight(victim) + obj_weight > can_carry_w(victim):
        return f"{_victim_name(victim)} can't carry that much weight."

    if not can_see_object(victim, obj):
        return f"{_victim_name(victim)} can't see it."

    _obj_from_char(char, obj)
    victim.add_object(obj)
    obj.carried_by = victim

    room_message = act_format("$n gives $p to $N.", recipient=None, actor=char, arg1=obj, arg2=victim)
    victim_message = act_format("$n gives you $p.", recipient=victim, actor=char, arg1=obj, arg2=victim)
    char_message = act_format("You give $p to $N.", recipient=char, actor=char, arg1=obj, arg2=victim)

    _broadcast_to_room_observers(room, room_message, actor=char, victim=victim)
    if hasattr(victim, "messages"):
        victim.messages.append(victim_message)

    if getattr(victim, "is_npc", False):
        from mud.mobprog import mp_give_trigger

        mp_give_trigger(victim, char, obj)

    return char_message


def _give_money(char: Character, room, amount: int, parts: list[str]) -> str:
    """ROM money-give path: give N coins|gold|silver victim."""
    if amount <= 0 or len(parts) < 3:
        return "Give what to whom?" if len(parts) < 3 else "Sorry, you can't do that."

    currency = parts[1].lower()
    if currency not in {"coins", "coin", "gold", "silver"}:
        return "Sorry, you can't do that."

    target_name = parts[2]
    victim = get_char_room(char, target_name)
    if victim is None:
        return "They aren't here."

    is_silver = currency != "gold"
    current_amount = int(getattr(char, "silver" if is_silver else "gold", 0) or 0)
    if current_amount < amount:
        return "You haven't got that much."

    if is_silver:
        char.silver = current_amount - amount
        victim.silver = int(getattr(victim, "silver", 0) or 0) + amount
        money_name = "silver"
    else:
        char.gold = current_amount - amount
        victim.gold = int(getattr(victim, "gold", 0) or 0) + amount
        money_name = "gold"

    victim_message = act_format(
        f"$n gives you {amount} {money_name}.",
        recipient=victim,
        actor=char,
        arg1=None,
        arg2=victim,
    )
    room_message = act_format("$n gives $N some coins.", recipient=None, actor=char, arg1=None, arg2=victim)
    char_message = act_format(
        f"You give $N {amount} {money_name}.",
        recipient=char,
        actor=char,
        arg1=None,
        arg2=victim,
    )

    if hasattr(victim, "messages"):
        victim.messages.append(victim_message)
    _broadcast_to_room_observers(room, room_message, actor=char, victim=victim)

    if getattr(victim, "is_npc", False):
        from mud.mobprog import mp_bribe_trigger

        mp_bribe_trigger(victim, char, amount if is_silver else amount * 100)

    if _is_changer(victim) and can_see_character(victim, char):
        _handle_changer_exchange(victim, char, amount, is_silver)

    return char_message


def _find_equipped_obj(char: Character, name: str):
    """Best-effort ROM-style equipped item lookup for GIVE's remove-first message."""
    name_lower = (name or "").lower()
    equipment = getattr(char, "equipment", {}) or {}
    for obj in equipment.values():
        if obj is None:
            continue
        obj_name = (getattr(obj, "name", "") or "").lower()
        obj_short = (getattr(obj, "short_descr", "") or "").lower()
        if name_lower in obj_name or name_lower in obj_short:
            return obj
    return None


def _has_shop(victim: Character) -> bool:
    """Check the common shop attachment points used in this codebase."""
    for source in (
        getattr(victim, "pShop", None),
        getattr(getattr(victim, "prototype", None), "pShop", None),
        getattr(getattr(victim, "pIndexData", None), "pShop", None),
        getattr(victim, "shop", None),
    ):
        if source is not None:
            return True
    return False


def _is_changer(victim: Character) -> bool:
    """ROM changer special: ACT_IS_CHANGER NPCs exchange coins after a bribe/give."""
    act_flags = int(getattr(victim, "act", 0) or 0)
    return bool(act_flags & int(ActFlag.IS_CHANGER))


def _handle_changer_exchange(victim: Character, char: Character, amount: int, is_silver: bool) -> None:
    """Mirror ROM changer logic by giving converted currency back through do_give()."""
    change = (95 * amount // 100 // 100) if is_silver else (95 * amount // 100)

    if not is_silver and change > int(getattr(victim, "silver", 0) or 0):
        victim.silver = int(getattr(victim, "silver", 0) or 0) + change

    if is_silver and change > int(getattr(victim, "gold", 0) or 0):
        victim.gold = int(getattr(victim, "gold", 0) or 0) + change

    if change < 1:
        _append_message(victim, char, "$n tells you 'I'm sorry, you did not give me enough to change.'")
        char.reply = victim
        do_give(victim, f"{amount} {'silver' if is_silver else 'gold'} {char.name}")
        return

    do_give(victim, f"{change} {'gold' if is_silver else 'silver'} {char.name}")
    if is_silver:
        silver_change = 95 * amount // 100 - change * 100
        do_give(victim, f"{silver_change} silver {char.name}")

    _append_message(victim, char, "$n tells you 'Thank you, come again.'")
    char.reply = victim


def _append_message(actor: Character, recipient: Character, template: str) -> None:
    """Append an act-formatted message when the recipient tracks messages in tests/runtime."""
    if not hasattr(recipient, "messages"):
        return
    recipient.messages.append(act_format(template, recipient=recipient, actor=actor, arg1=None, arg2=recipient))


def _broadcast_to_room_observers(room, message: str, actor: Character, victim: Character) -> None:
    """Mirror ROM TO_NOTVICT by excluding both the actor and the victim."""
    for occupant in list(getattr(room, "people", [])):
        if occupant is actor or occupant is victim:
            continue
        writer = getattr(occupant, "connection", None)
        if writer:
            # fire and forget
            import asyncio

            asyncio.create_task(send_to_char(occupant, message))
        if hasattr(occupant, "messages"):
            occupant.messages.append(message)


def _victim_name(victim: Character) -> str:
    """Display name used in give feedback."""
    return getattr(victim, "short_descr", None) or getattr(victim, "name", "They")


def _victim_possessive(victim: Character) -> str:
    """POSSESSIVE token substitute for hand-capacity feedback."""
    sex = getattr(victim, "sex", None)
    if sex == 1:
        return "his"
    if sex == 2:
        return "her"
    return "their"
