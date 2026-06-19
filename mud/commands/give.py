"""
Give command - give items or money to another character.

ROM Reference: src/act_obj.c do_give (lines 678-855)
"""

from __future__ import annotations

from mud.commands.obj_manipulation import _can_drop_obj, _obj_from_char
from mud.game_loop import _obj_to_char
from mud.mobprog import disable_mobtrigger
from mud.models.character import Character, _object_carry_number, _object_carry_weight
from mud.models.constants import ActFlag
from mud.utils.act import act_format, act_to_room
from mud.utils.messaging import push_message
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
        # GIVE-002: ROM src/act_obj.c — act("$N tells you 'Sorry, you'll have to sell that.'", ...).
        # GIVE-005: ROM src/act_obj.c:801 also sets `ch->reply = victim` so the giver
        # can `reply` to the keeper after the refusal.
        char.reply = victim
        return act_format("$N tells you 'Sorry, you'll have to sell that.'", recipient=char, actor=char, arg2=victim)

    if not _can_drop_obj(char, obj):
        return "You can't let go of it."

    # GIVE-002: ROM renders these via act() with the victim's pronouns/PERS name,
    # not a baked name + "their". ROM src/act_obj.c:
    #   act("$N has $S hands full.", ch, NULL, victim, TO_CHAR)   ($S = his/her/its)
    #   act("$N can't carry that much weight.", ch, NULL, victim, TO_CHAR)
    #   act("$N can't see it.", ch, NULL, victim, TO_CHAR)
    if int(getattr(victim, "carry_number", 0) or 0) + _object_carry_number(obj) > can_carry_n(victim):
        return act_format("$N has $S hands full.", recipient=char, actor=char, arg2=victim)

    obj_weight = _object_carry_weight(obj)
    if get_carry_weight(victim) + obj_weight > can_carry_w(victim):
        return act_format("$N can't carry that much weight.", recipient=char, actor=char, arg2=victim)

    if not can_see_object(victim, obj):
        return act_format("$N can't see it.", recipient=char, actor=char, arg2=victim)

    _obj_from_char(char, obj)
    _obj_to_char(obj, victim)

    victim_message = act_format("$n gives you $p.", recipient=victim, actor=char, arg1=obj, arg2=victim)
    char_message = act_format("You give $p to $N.", recipient=char, actor=char, arg1=obj, arg2=victim)

    # ROM src/act_obj.c:832-836 wraps the give act() trio in MOBtrigger=FALSE/TRUE so
    # the TO_NOTVICT room line does NOT fire TRIG_ACT; the explicit mp_give_trigger
    # below covers the give event. INV-025: act_to_room renders $n/$N per-recipient
    # (PERS masking, an invisible giver → "Someone"); exclude=victim + auto-excluded
    # actor = ROM TO_NOTVICT; disable_mobtrigger() suppresses the per-NPC dispatch.
    with disable_mobtrigger():
        act_to_room(room, "$n gives $p to $N.", char, arg1=obj, arg2=victim, exclude=victim)
        # ROM src/act_obj.c:834 act("$n gives you $p.", …, TO_VICT) writes to the
        # recipient's descriptor immediately; push_message routes a connected PC
        # to the async send and falls back to the mailbox only for disconnected
        # chars (GIVE-001 / INV-001 wrong-channel — push_message does not dispatch
        # TRIG_ACT, so the disable_mobtrigger contract is unaffected).
        push_message(victim, victim_message)

    if getattr(victim, "is_npc", False):
        from mud.mobprog import mp_give_trigger

        mp_give_trigger(victim, char, obj)

    return char_message


def _give_money(char: Character, room, amount: int, parts: list[str]) -> str:
    """ROM money-give path: give N coins|gold|silver victim."""
    # GIVE-003: ROM src/act_obj.c:683-698 validates amount + currency BEFORE
    # re-reading the victim token, so a malformed currency or non-positive amount
    # with no recipient yields "Sorry, you can't do that.", not the missing-target
    # message. The prior single guard checked `len(parts) < 3` first and inverted
    # ROM's order (same gate-ordering class as SHOUT-005).
    currency = parts[1].lower()
    if amount <= 0 or currency not in {"coins", "coin", "gold", "silver"}:
        return "Sorry, you can't do that."

    # ROM src/act_obj.c:693-698 — re-read arg2 as the recipient; empty → ask whom.
    if len(parts) < 3:
        return "Give what to whom?"

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
    char_message = act_format(
        f"You give $N {amount} {money_name}.",
        recipient=char,
        actor=char,
        arg1=None,
        arg2=victim,
    )

    # ROM coins branch act(..., TO_VICT) writes to the recipient's descriptor
    # immediately; push_message routes a connected PC to the async send (GIVE-001
    # / INV-001 wrong-channel), mailbox fallback for disconnected chars.
    push_message(victim, victim_message)
    # ROM src/act_obj.c:726 "$n gives $N some coins." TO_NOTVICT — NOT
    # MOBtrigger-suppressed (the suppressor block is only the object branch at
    # :832), so the room line DOES fire TRIG_ACT. INV-025: act_to_room renders $N
    # per-recipient (PERS masking) + dispatches TRIG_ACT; exclude=victim +
    # auto-excluded actor = ROM TO_NOTVICT.
    act_to_room(room, "$n gives $N some coins.", char, arg2=victim, exclude=victim)

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
    # GIVE-004: ROM src/act_obj.c:741 — `change = silver ? 95 * amount / 100 / 100 : 95 * amount`.
    # The gold branch has NO division: giving N gold returns `95 * N` *silver*
    # (1 gold == 100 silver, so the 5% fee already lands in silver units). The
    # prior `95 * amount // 100` divided by an extra 100, so 10 gold returned 9
    # silver instead of 950 and small gifts wrongly hit "not enough to change".
    change = (95 * amount // 100 // 100) if is_silver else (95 * amount)

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
    """Deliver an act-formatted changer-exchange line to the recipient.

    INV-001 (GIVE-001 cousin): single-channel delivery (push_message XOR) — the
    prior raw mailbox append arrived late for a connected recipient. ROM's
    changer path sends the "$n tells you ..." line via act(TO_VICT), immediate.
    """
    push_message(recipient, act_format(template, recipient=recipient, actor=actor, arg1=None, arg2=recipient))


# GIVE-002: the former `_victim_name` / `_victim_possessive` helpers (baked name +
# a "their"-for-sexless possessive) were removed — these feedback lines now render
# through `act_format` ($N PERS name + $S = his/her/its), matching ROM act().
