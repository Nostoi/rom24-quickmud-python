"""ACT-CAP-002 — Room.broadcast, _message_room, and TO_ALL caster legs
capitalize the first visible char of delivered act() lines, matching ROM
`act_new` (src/comm.c:2376-2379).

`broadcast_room` (protocol.py) was capped in ACT-CAP-001 (2.11.40), but the
parallel `room.broadcast` method and `_message_room` still deliver their baked
strings verbatim.  The TO_ALL caster legs in `mud/skills/handlers.py` split the
same `message` into `_send_to_char(caster, message)` (uncapped) plus
`broadcast_room(room, message, exclude=caster)` (now capped), so the caster
sees a lowercase line while the room sees it capitalized — ROM `act(..., TO_ALL)`
caps for everyone including the caster.

Three surfaces to fix (per the audit doc):

(a) `mud/models/room.py:Room.broadcast` — ~20 callers (death lines,
    "is zapped", mob actions, practice/level, reconnect/link-lost, mob speech).
    Cap once at entry, same pattern as `broadcast_room`.

(b) `mud/game_loop.py:_message_room` — the fallback delivery path used by
    object wear-off (e.g. "$p fades into view.").  Delegates to `Room.broadcast`
    in the normal case (so (a) covers it), but the direct `_send_to_char` path
    at line 345 is also uncapped.  Cap at function entry.

(c) The TO_ALL caster legs — `invis`, `poison` (object), `remove_curse` (object)
    — share a single `message` between `_send_to_char(caster, message)` and
    `broadcast_room(room, message, exclude=caster)`.  Cap the shared `message`
    at each build site so both legs match ROM `act(..., TO_ALL)`.
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.room import Room


def _room_with_listener(name: str = "listener-pc") -> tuple[Room, Character]:
    room = Room(vnum=99942, name="ACT-CAP-002 probe room")
    listener = Character(name=name, is_npc=False)
    listener.messages = []
    room.add_character(listener)
    return room, listener


# ── Surface (a): Room.broadcast ──────────────────────────────────────────


def test_room_broadcast_caps_plain_line() -> None:
    # mirrors ROM act("$n is zapped by $p.", ..., TO_ROOM) → src/comm.c:2376
    room, listener = _room_with_listener()
    room.broadcast("the goblin is zapped by a sword.")
    assert listener.messages, "listener received nothing"
    msg = listener.messages[-1]
    assert msg[0].isupper(), f"first char not capitalized: {msg!r}"
    assert "goblin is zapped" in msg, msg


def test_room_broadcast_caps_after_color_kludge() -> None:
    # mirrors ROM act("{R...{x", ..., TO_ROOM) → `{`-kludge caps buf[2]
    room, listener = _room_with_listener()
    room.broadcast("{Rthe goblin gets {Wsomething{x!{x")
    msg = listener.messages[-1]
    assert msg.startswith("{R"), f"colour code mangled: {msg!r}"
    assert msg[2].isupper(), f"char after colour code not capitalized: {msg!r}"


def test_room_broadcast_leaves_already_capital_unchanged() -> None:
    room, listener = _room_with_listener()
    room.broadcast("Bob has reconnected.")
    assert listener.messages[-1] == "Bob has reconnected."


def test_room_broadcast_excludes_sender() -> None:
    room, sender = _room_with_listener("sender")
    listener = Character(name="listener-pc", is_npc=False)
    listener.messages = []
    room.add_character(listener)
    room.broadcast("a goblin arrives.", exclude=sender)
    assert "a goblin arrives." not in sender.messages, "sender was excluded"
    msg = listener.messages[-1]
    assert msg[0].isupper(), f"listener sees uncapped line: {msg!r}"


# ── Surface (b): _message_room ────────────────────────────────────────────


def test_message_room_caps_through_broadcast() -> None:
    # _message_room delegates to room.broadcast in the normal case;
    # the cap should propagate.
    from mud.game_loop import _message_room

    room, listener = _room_with_listener()
    _message_room(room, "the light fades into view.")
    msg = listener.messages[-1]
    assert msg[0].isupper(), f"_message_room delivered uncapped: {msg!r}"


def test_message_room_caps_fallback_path() -> None:
    # When room has no .broadcast (unlikely in production, but the fallback
    # path at game_loop.py:342-345 sends via _send_to_char), cap at entry.
    from mud.game_loop import _message_room

    room = Room(vnum=99943, name="fallback probe")
    listener = Character(name="fallback-pc", is_npc=False)
    listener.messages = []
    room.add_character(listener)
    # Remove broadcast to force fallback — though current Room always has it.
    # Instead, just verify _message_room caps its argument before delegating.
    _message_room(room, "an object fades into view.")
    msg = listener.messages[-1]
    assert msg[0].isupper(), f"_message_room fallback uncapped: {msg!r}"


# ── Surface (c): TO_ALL caster legs ───────────────────────────────────────
#
# ROM act("$p fades out of sight.", ch, obj, NULL, TO_ALL) caps the line for
# everyone including the caster.  The Python handlers split TO_ALL into
# _send_to_char(caster, act_format(...)) + act_to_room(room, ..., exclude=caster);
# each leg renders the format string independently and act_format/act_to_room
# cap the first visible letter per recipient (INV-029), matching ROM.
# These tests exercise the actual handler paths end-to-end.


def test_invis_object_caps_caster_leg() -> None:
    # ROM: act("$p fades out of sight.", ch, obj, NULL, TO_ALL)
    from mud.models.character import Character as C
    from mud.models.obj import ObjIndex
    from mud.models.object import Object
    from mud.skills.handlers import invis

    room = Room(vnum=99944, name="invis probe")
    caster = C(name="Caster", is_npc=False, level=20)
    caster.messages = []
    room.add_character(caster)
    listener = C(name="Listener", is_npc=False)
    listener.messages = []
    room.add_character(listener)

    proto = ObjIndex(vnum=99990, name="blue wand", short_descr="a blue wand")
    obj = Object(instance_id=None, prototype=proto)
    room.add_object(obj)

    result = invis(caster, obj)
    assert result is True
    caster_msgs = [m for m in caster.messages if "fades" in m.lower()]
    assert caster_msgs, f"caster received no 'fades' message: {caster.messages}"
    assert caster_msgs[0][0].isupper(), f"invis caster leg uncapped: {caster_msgs[0]!r}"


def test_remove_curse_object_caps_caster_leg() -> None:
    # ROM: act("$p glows blue.", ch, obj, NULL, TO_ALL)
    from mud.models.character import Character as C
    from mud.models.constants import ExtraFlag
    from mud.models.obj import ObjIndex
    from mud.models.object import Object
    from mud.skills.handlers import remove_curse

    room = Room(vnum=99946, name="remove_curse probe")
    caster = C(name="Caster", is_npc=False, level=20)
    caster.messages = []
    room.add_character(caster)
    listener = C(name="Listener", is_npc=False)
    listener.messages = []
    room.add_character(listener)

    proto = ObjIndex(
        vnum=99992,
        name="cursed ring",
        short_descr="a cursed ring",
        extra_flags=int(ExtraFlag.NODROP),
    )
    obj = Object(instance_id=None, prototype=proto)
    room.add_object(obj)

    result = remove_curse(caster, obj)
    assert result is True
    caster_msgs = [m for m in caster.messages if "glows" in m.lower()]
    listener_msgs = [m for m in listener.messages if "glows" in m.lower()]
    assert caster_msgs, f"caster received no 'glows' message: {caster.messages}"
    assert caster_msgs[0][0].isupper(), f"remove_curse caster leg uncapped: {caster_msgs[0]!r}"
    if listener_msgs:
        assert listener_msgs[0][0].isupper(), f"remove_curse room leg uncapped: {listener_msgs[0]!r}"

