"""Position commands - stand, rest, sit, sleep, wake.

ROM Reference: src/act_move.c
- do_stand: lines 999-1106
- do_rest:  lines 1110-1246
- do_sit:   lines 1249-1372
- do_sleep: lines 1375-1449
- do_wake:  lines 1453-1492
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.constants import AffectFlag, FurnitureFlag, ItemType, Position
from mud.net.protocol import broadcast_room
from mud.utils.act import act_format

if TYPE_CHECKING:
    from mud.models.character import Character


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_furniture(obj) -> bool:
    """Match ROM ``obj->item_type == ITEM_FURNITURE``.

    QuickMUD ``Object.item_type`` may be int or string; mirror the
    convention used in ``mud/commands/obj_manipulation.py``.
    """
    item_type = getattr(obj, "item_type", None)
    if item_type is None:
        proto = getattr(obj, "prototype", None)
        if proto is not None:
            item_type = getattr(proto, "item_type", None)
    return item_type == ItemType.FURNITURE or str(item_type) == "furniture"


def _furn_flags(obj) -> int:
    """Return ``obj->value[2]`` (furniture position bitfield)."""
    values = getattr(obj, "value", None) or getattr(getattr(obj, "prototype", None), "value", None)
    if not values or len(values) < 3:
        return 0
    try:
        return int(values[2])
    except (TypeError, ValueError):
        return 0


def _capacity(obj) -> int:
    """Return ``obj->value[0]`` (max occupants)."""
    values = getattr(obj, "value", None) or getattr(getattr(obj, "prototype", None), "value", None)
    if not values:
        return 0
    try:
        return int(values[0])
    except (TypeError, ValueError):
        return 0


def _has(flags: int, bit: FurnitureFlag) -> bool:
    return bool(flags & int(bit))


def _resolve_furniture(ch: Character, args: str):
    """Return (obj-or-None, error-message-or-None).

    Mirrors ROM C ``argument[0] != '\\0' ? get_obj_list(...) : ch->on``
    used by do_rest / do_sit / do_sleep.
    """
    args = (args or "").strip()
    if args:
        from mud.commands.obj_manipulation import get_obj_list

        room = getattr(ch, "room", None)
        contents = getattr(room, "contents", []) if room is not None else []
        obj = get_obj_list(ch, args, contents)
        if obj is None:
            return None, "You don't see that here.\r\n"
        return obj, None
    return getattr(ch, "on", None), None


def _broadcast(ch: Character, fmt: str, obj=None) -> None:
    room = getattr(ch, "room", None)
    if room is None:
        return
    msg = act_format(fmt, recipient=None, actor=ch, arg1=obj)
    broadcast_room(room, msg, exclude=ch)


def _to_char(fmt: str, ch: Character, obj=None) -> str:
    return act_format(fmt, recipient=ch, actor=ch, arg1=obj) + "\r\n"


def _count_users(obj) -> int:
    """Count occupants whose ``ch.on == obj`` (mirrors handler.c count_users)."""
    from mud.handler import count_users

    return count_users(obj)


# ---------------------------------------------------------------------------
# do_stand (ROM act_move.c:999)
# ---------------------------------------------------------------------------


def do_stand(ch: Character, args: str) -> str:
    args = (args or "").strip()
    obj = None

    if args:
        if ch.position == Position.FIGHTING:
            return "Maybe you should finish fighting first?\r\n"

        from mud.commands.obj_manipulation import get_obj_list

        room = getattr(ch, "room", None)
        contents = getattr(room, "contents", []) if room is not None else []
        obj = get_obj_list(ch, args, contents)
        if obj is None:
            return "You don't see that here.\r\n"

        flags = _furn_flags(obj)
        stand_mask = int(FurnitureFlag.STAND_AT | FurnitureFlag.STAND_ON | FurnitureFlag.STAND_IN)
        if not _is_furniture(obj) or not (flags & stand_mask):
            return "You can't seem to find a place to stand.\r\n"

        if getattr(ch, "on", None) is not obj and _count_users(obj) >= _capacity(obj):
            return _to_char("There's no room to stand on $p.", ch, obj)

        ch.on = obj

    pos = ch.position

    if pos == Position.SLEEPING:
        if ch.affected_by & AffectFlag.SLEEP:
            return "You can't wake up!\r\n"

        if obj is None:
            ch.on = None
            _broadcast(ch, "$n wakes and stands up.")
            ch.position = Position.STANDING
            output = "You wake and stand up.\r\n"
        else:
            flags = _furn_flags(obj)
            if _has(flags, FurnitureFlag.STAND_AT):
                to_char_fmt = "You wake and stand at $p."
                to_room_fmt = "$n wakes and stands at $p."
            elif _has(flags, FurnitureFlag.STAND_ON):
                to_char_fmt = "You wake and stand on $p."
                to_room_fmt = "$n wakes and stands on $p."
            else:
                to_char_fmt = "You wake and stand in $p."
                to_room_fmt = "$n wakes and stands in $p."
            _broadcast(ch, to_room_fmt, obj)
            ch.position = Position.STANDING
            output = _to_char(to_char_fmt, ch, obj)

        # ROM: do_function(ch, &do_look, "auto") after waking-and-standing
        try:
            from mud.commands.inspection import do_look

            look_text = do_look(ch, "auto")
            if look_text:
                output += look_text
        except Exception:
            pass
        return output

    if pos in (Position.RESTING, Position.SITTING):
        if obj is None:
            ch.on = None
            _broadcast(ch, "$n stands up.")
            ch.position = Position.STANDING
            return "You stand up.\r\n"
        flags = _furn_flags(obj)
        if _has(flags, FurnitureFlag.STAND_AT):
            to_char_fmt = "You stand at $p."
            to_room_fmt = "$n stands at $p."
        elif _has(flags, FurnitureFlag.STAND_ON):
            to_char_fmt = "You stand on $p."
            to_room_fmt = "$n stands on $p."
        else:
            to_char_fmt = "You stand in $p."
            # ROM bug-faithful: TO_ROOM uses "stands on $p" in this branch (act_move.c:1091)
            to_room_fmt = "$n stands on $p."
        _broadcast(ch, to_room_fmt, obj)
        ch.position = Position.STANDING
        return _to_char(to_char_fmt, ch, obj)

    if pos == Position.STANDING:
        return "You are already standing.\r\n"

    if pos == Position.FIGHTING:
        return "You are already fighting!\r\n"

    return ""


# ---------------------------------------------------------------------------
# do_rest (ROM act_move.c:1110)
# ---------------------------------------------------------------------------


def do_rest(ch: Character, args: str) -> str:
    if ch.position == Position.FIGHTING:
        return "You are already fighting!\r\n"

    obj, err = _resolve_furniture(ch, args)
    if err:
        return err

    if obj is not None:
        flags = _furn_flags(obj)
        rest_mask = int(FurnitureFlag.REST_AT | FurnitureFlag.REST_ON | FurnitureFlag.REST_IN)
        if not _is_furniture(obj) or not (flags & rest_mask):
            return "You can't rest on that.\r\n"

        if getattr(ch, "on", None) is not obj and _count_users(obj) >= _capacity(obj):
            return _to_char("There's no more room on $p.", ch, obj)

        ch.on = obj

    pos = ch.position
    flags = _furn_flags(obj) if obj is not None else 0

    if pos == Position.SLEEPING:
        if ch.affected_by & AffectFlag.SLEEP:
            return "You can't wake up!\r\n"

        if obj is None:
            _broadcast(ch, "$n wakes up and starts resting.")
            ch.position = Position.RESTING
            return "You wake up and start resting.\r\n"
        if _has(flags, FurnitureFlag.REST_AT):
            tc, tr = "You wake up and rest at $p.", "$n wakes up and rests at $p."
        elif _has(flags, FurnitureFlag.REST_ON):
            tc, tr = "You wake up and rest on $p.", "$n wakes up and rests on $p."
        else:
            tc, tr = "You wake up and rest in $p.", "$n wakes up and rests in $p."
        _broadcast(ch, tr, obj)
        ch.position = Position.RESTING
        return _to_char(tc, ch, obj)

    if pos == Position.RESTING:
        return "You are already resting.\r\n"

    if pos == Position.STANDING:
        if obj is None:
            _broadcast(ch, "$n sits down and rests.")
            ch.position = Position.RESTING
            return "You rest.\r\n"
        if _has(flags, FurnitureFlag.REST_AT):
            tc, tr = "You sit down at $p and rest.", "$n sits down at $p and rests."
        elif _has(flags, FurnitureFlag.REST_ON):
            tc, tr = "You sit on $p and rest.", "$n sits on $p and rests."
        else:
            tc, tr = "You rest in $p.", "$n rests in $p."
        _broadcast(ch, tr, obj)
        ch.position = Position.RESTING
        return _to_char(tc, ch, obj)

    if pos == Position.SITTING:
        if obj is None:
            _broadcast(ch, "$n rests.")
            ch.position = Position.RESTING
            return "You rest.\r\n"
        if _has(flags, FurnitureFlag.REST_AT):
            tc, tr = "You rest at $p.", "$n rests at $p."
        elif _has(flags, FurnitureFlag.REST_ON):
            tc, tr = "You rest on $p.", "$n rests on $p."
        else:
            tc, tr = "You rest in $p.", "$n rests in $p."
        _broadcast(ch, tr, obj)
        ch.position = Position.RESTING
        return _to_char(tc, ch, obj)

    return ""


# ---------------------------------------------------------------------------
# do_sit (ROM act_move.c:1249)
# ---------------------------------------------------------------------------


def do_sit(ch: Character, args: str) -> str:
    if ch.position == Position.FIGHTING:
        return "Maybe you should finish this fight first?\r\n"

    obj, err = _resolve_furniture(ch, args)
    if err:
        return err

    if obj is not None:
        flags = _furn_flags(obj)
        sit_mask = int(FurnitureFlag.SIT_AT | FurnitureFlag.SIT_ON | FurnitureFlag.SIT_IN)
        if not _is_furniture(obj) or not (flags & sit_mask):
            return "You can't sit on that.\r\n"

        if getattr(ch, "on", None) is not obj and _count_users(obj) >= _capacity(obj):
            return _to_char("There's no more room on $p.", ch, obj)

        ch.on = obj

    pos = ch.position
    flags = _furn_flags(obj) if obj is not None else 0

    if pos == Position.SLEEPING:
        if ch.affected_by & AffectFlag.SLEEP:
            return "You can't wake up!\r\n"
        if obj is None:
            _broadcast(ch, "$n wakes and sits up.")
            ch.position = Position.SITTING
            return "You wake and sit up.\r\n"
        if _has(flags, FurnitureFlag.SIT_AT):
            tc, tr = "You wake and sit at $p.", "$n wakes and sits at $p."
        elif _has(flags, FurnitureFlag.SIT_ON):
            # ROM bug-faithful: TO_ROOM also reads "sits at $p" here (act_move.c:1317)
            tc, tr = "You wake and sit on $p.", "$n wakes and sits at $p."
        else:
            tc, tr = "You wake and sit in $p.", "$n wakes and sits in $p."
        _broadcast(ch, tr, obj)
        ch.position = Position.SITTING
        return _to_char(tc, ch, obj)

    if pos == Position.RESTING:
        ch.position = Position.SITTING
        if obj is None:
            return "You stop resting.\r\n"
        if _has(flags, FurnitureFlag.SIT_AT):
            tc, tr = "You sit at $p.", "$n sits at $p."
            _broadcast(ch, tr, obj)
            return _to_char(tc, ch, obj)
        if _has(flags, FurnitureFlag.SIT_ON):
            tc, tr = "You sit on $p.", "$n sits on $p."
            _broadcast(ch, tr, obj)
            return _to_char(tc, ch, obj)
        # ROM emits no message in the SIT_IN-from-resting branch
        return ""

    if pos == Position.SITTING:
        return "You are already sitting down.\r\n"

    if pos == Position.STANDING:
        if obj is None:
            _broadcast(ch, "$n sits down on the ground.")
            ch.position = Position.SITTING
            return "You sit down.\r\n"
        if _has(flags, FurnitureFlag.SIT_AT):
            tc, tr = "You sit down at $p.", "$n sits down at $p."
        elif _has(flags, FurnitureFlag.SIT_ON):
            tc, tr = "You sit on $p.", "$n sits on $p."
        else:
            tc, tr = "You sit down in $p.", "$n sits down in $p."
        _broadcast(ch, tr, obj)
        ch.position = Position.SITTING
        return _to_char(tc, ch, obj)

    return ""


# ---------------------------------------------------------------------------
# do_sleep (ROM act_move.c:1375)
# ---------------------------------------------------------------------------


def do_sleep(ch: Character, args: str) -> str:
    args = (args or "").strip()
    pos = ch.position

    if pos == Position.SLEEPING:
        return "You are already sleeping.\r\n"

    if pos == Position.FIGHTING:
        return "You are already fighting!\r\n"

    if pos in (Position.RESTING, Position.SITTING, Position.STANDING):
        if not args and getattr(ch, "on", None) is None:
            _broadcast(ch, "$n goes to sleep.")
            ch.position = Position.SLEEPING
            return "You go to sleep.\r\n"

        if not args:
            obj = ch.on
        else:
            from mud.commands.obj_manipulation import get_obj_list

            room = getattr(ch, "room", None)
            contents = getattr(room, "contents", []) if room is not None else []
            obj = get_obj_list(ch, args, contents)

        if obj is None:
            return "You don't see that here.\r\n"

        flags = _furn_flags(obj)
        sleep_mask = int(FurnitureFlag.SLEEP_AT | FurnitureFlag.SLEEP_ON | FurnitureFlag.SLEEP_IN)
        if not _is_furniture(obj) or not (flags & sleep_mask):
            return "You can't sleep on that!\r\n"

        if getattr(ch, "on", None) is not obj and _count_users(obj) >= _capacity(obj):
            return _to_char("There is no room on $p for you.", ch, obj)

        ch.on = obj
        if _has(flags, FurnitureFlag.SLEEP_AT):
            tc, tr = "You go to sleep at $p.", "$n goes to sleep at $p."
        elif _has(flags, FurnitureFlag.SLEEP_ON):
            tc, tr = "You go to sleep on $p.", "$n goes to sleep on $p."
        else:
            tc, tr = "You go to sleep in $p.", "$n goes to sleep in $p."
        _broadcast(ch, tr, obj)
        ch.position = Position.SLEEPING
        return _to_char(tc, ch, obj)

    return ""


# ---------------------------------------------------------------------------
# do_wake (ROM act_move.c:1453)
# ---------------------------------------------------------------------------


def do_wake(ch: Character, args: str) -> str:
    args = (args or "").strip()
    arg = args.split()[0] if args else ""

    if not arg:
        return do_stand(ch, "")

    # ROM IS_AWAKE := position > POS_SLEEPING
    if ch.position <= Position.SLEEPING:
        return "You are asleep yourself!\r\n"

    from mud.world.char_find import get_char_room

    victim = get_char_room(ch, arg)
    if victim is None:
        return "They aren't here.\r\n"

    if getattr(victim, "position", Position.STANDING) > Position.SLEEPING:
        return act_format("$N is already awake.", recipient=ch, actor=ch, arg2=victim) + "\r\n"

    if getattr(victim, "affected_by", 0) & AffectFlag.SLEEP:
        return act_format("You can't wake $M!", recipient=ch, actor=ch, arg2=victim) + "\r\n"

    # ROM act_new($n wakes you., TO_VICT) — deliver to victim's message buffer
    vict_msg = act_format("$n wakes you.", recipient=victim, actor=ch, arg2=victim) + "\r\n"
    if hasattr(victim, "messages"):
        victim.messages.append(vict_msg)
    writer = getattr(victim, "connection", None)
    if writer:
        try:
            import asyncio

            from mud.net.protocol import send_to_char

            asyncio.create_task(send_to_char(victim, vict_msg))
        except Exception:
            pass

    # ROM faithfully calls do_function(ch, &do_stand, "") on the *caller*, not
    # the victim. Preserve this quirk; the victim's position is unchanged here.
    return do_stand(ch, "")
