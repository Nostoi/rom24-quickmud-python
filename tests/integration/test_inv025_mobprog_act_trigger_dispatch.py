"""INV-025 — MOBPROG-ACT-TRIGGER-DISPATCH.

ROM contract: ``src/comm.c:2384-2385`` — inside ``act()``, every NPC
recipient with ``HAS_TRIGGER(TRIG_ACT)`` receives ``mp_act_trigger`` on
the formatted message.  The dispatch is gated on the global
``bool MOBtrigger`` flag (``src/comm.c:311``) so paths that emit free-form
or recursive ``act()`` lines (do_emote, do_give, do_mpasound, …) suppress
the trigger by toggling ``MOBtrigger = FALSE`` around their own act() calls.

EMOTE-003 correction (was a false-✅): ``do_emote`` is NOT a TRIG_ACT
producer.  ROM ``src/act_comm.c:1090-1093`` wraps both of its ``act("$n
$T", …)`` calls in ``MOBtrigger = FALSE; … ; MOBtrigger = TRUE;`` —
precisely so a player cannot forge an arbitrary act-trigger phrase via
emote text (``emote bows`` must NOT trip an NPC scripted on "bows").  The
2.9.40 INV-025 enforcement picked ``do_emote`` as its canonical producer
and asserted the inverse of ROM; ``mud/commands/communication.py:do_emote``
fired ``mp_act_trigger_room`` at runtime, a shipped behavioral bug.

This suite locks the corrected contract using ``do_stand`` (a *genuine*
ROM TRIG_ACT producer — ``src/act_move.c`` ``act("$n stands up.", …)``
with no ``MOBtrigger`` wrap):

1. A PC emote does NOT fire ``mp_act_trigger`` on a listening NPC
   (ROM ``MOBtrigger = FALSE``).
2. ``do_stand`` wrapped in ``disable_mobtrigger()`` does NOT fire —
   the gate (ROM ``src/comm.c:2384`` ``else if (MOBtrigger)``).
3. An NPC's own ``do_stand`` does NOT self-fire its act trigger
   (``mp_act_trigger_room`` excludes the actor).
4. A PC ``do_stand`` fires ``mp_act_trigger`` exactly once on a
   listening NPC — the positive producer path.
"""

from __future__ import annotations

import pytest

from mud.commands.communication import do_emote
from mud.commands.position import do_stand
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.mob import MobIndex
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)
    room_registry.pop(9500, None)


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int = 9501):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def _make_room() -> Room:
    room = Room(vnum=9500, name="Bow", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9500] = room
    return room


def _make_pc(room: Room) -> Character:
    pc = Character(
        name="emoter",
        is_npc=False,
        level=10,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    pc.messages = []
    room.people.append(pc)
    character_registry.append(pc)
    return pc


def _make_listener(room: Room) -> Character:
    listener = Character(
        name="listener",
        is_npc=True,
        level=10,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    listener.messages = []
    proto = MobIndex(vnum=9501, short_descr="a listener", level=10)
    proto.mprogs = [
        _FakeProg(
            trig_type=int(_act_trigger_flag()),
            trig_phrase="bows",
            code='mob echo "ACT_TRIGGERED"\n',
            vnum=9501,
        )
    ]
    listener.prototype = proto
    room.people.append(listener)
    character_registry.append(listener)
    return listener


def _act_trigger_flag() -> int:
    from mud.mobprog import Trigger

    return int(Trigger.ACT)


def test_pc_emote_does_not_fire_act_trigger_on_listening_npc():
    """EMOTE-003 — ROM src/act_comm.c:1090-1093 wraps do_emote's act()
    in MOBtrigger=FALSE, so a PC emote must NOT dispatch mp_act_trigger
    even when the phrase matches a listening NPC's trig_phrase."""
    import mud.mobprog as mobprog

    room = _make_room()
    pc = _make_pc(room)
    _make_listener(room)  # NPC scripted on "bows"

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        do_emote(pc, "bows deeply")
    finally:
        mobprog.mp_act_trigger = original

    assert fired == [], (
        f"do_emote must NOT fire mp_act_trigger — ROM src/act_comm.c:1090 "
        f"sets MOBtrigger=FALSE around its act() calls; fired: {fired}"
    )


def test_disable_mobtrigger_suppresses_act_trigger_dispatch():
    """ROM src/comm.c:311 / src/comm.c:2384 — MOBtrigger=FALSE blocks
    dispatch.  Exercised through ``do_stand``, a genuine TRIG_ACT
    producer (no MOBtrigger wrap), so the suppression is attributable
    to the gate and not to the producer never firing."""
    import mud.mobprog as mobprog

    room = _make_room()
    pc = _make_pc(room)
    pc.position = Position.RESTING
    _make_listener(room)

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        with mobprog.disable_mobtrigger():
            do_stand(pc, "")
    finally:
        mobprog.mp_act_trigger = original

    assert fired == [], (
        f"MOBtrigger=FALSE must suppress mp_act_trigger dispatch "
        f"(ROM src/comm.c:2384); fired: {fired}"
    )


def test_act_trigger_skipped_when_actor_is_npc():
    """ROM act() dispatches to all NPC recipients, but the formatted
    line is recipient-keyed and ``mp_act_trigger_room`` excludes the
    actor (``recipient is ch``), so an NPC's own ``do_stand`` must not
    self-fire its ACT trigger.  Lock the no-self-fire contract on a
    genuine producer (not do_emote, which never fires at all)."""
    import mud.mobprog as mobprog
    from mud.mobprog import Trigger

    room = _make_room()

    npc_actor = Character(
        name="npc-actor",
        is_npc=True,
        level=10,
        room=room,
        position=int(Position.RESTING),
        default_pos=int(Position.STANDING),
    )
    npc_actor.messages = []
    proto = MobIndex(vnum=9502, short_descr="an actor", level=10)
    proto.mprogs = [
        _FakeProg(
            trig_type=int(Trigger.ACT),
            trig_phrase="stands",
            code='mob echo "SELF_TRIGGERED"\n',
            vnum=9502,
        )
    ]
    npc_actor.prototype = proto
    room.people.append(npc_actor)
    character_registry.append(npc_actor)

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        do_stand(npc_actor, "")
    finally:
        mobprog.mp_act_trigger = original

    assert fired == [], (
        f"actor must not self-fire its own TRIG_ACT; fired: {fired}"
    )


def test_position_act_room_broadcast_fires_act_trigger_on_listening_npc():
    """ROM src/act_move.c:1062 / src/comm.c:2384 — stand act() fires TRIG_ACT."""
    import mud.mobprog as mobprog

    room = _make_room()
    pc = _make_pc(room)
    pc.position = Position.RESTING
    _make_listener(room)

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        do_stand(pc, "")
    finally:
        mobprog.mp_act_trigger = original

    assert len(fired) == 1, (
        f"expected exactly one mp_act_trigger fire for the stand room act(); "
        f"got: {fired}"
    )
    assert fired[0][0] == "listener"
    assert "stands" in fired[0][1]
