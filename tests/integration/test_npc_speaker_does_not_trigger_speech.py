"""Probe: NPC speaker must not fire SPEECH triggers on listening NPCs.

ROM ``src/act_comm.c:779-789`` (do_say):

    if (!IS_NPC (ch))
    {
        CHAR_DATA *mob, *mob_next;
        for (mob = ch->in_room->people; mob != NULL; mob = mob_next)
        {
            mob_next = mob->next_in_room;
            if (IS_NPC (mob) && HAS_TRIGGER (mob, TRIG_SPEECH)
                && mob->position == mob->pIndexData->default_pos)
                mp_act_trigger (argument, mob, ch, NULL, NULL, TRIG_SPEECH);
        }
    }

The outer ``if (!IS_NPC (ch))`` gate is load-bearing: it prevents
mob-to-mob speech-trigger cascades.  ROM's MOBtrigger global
(``src/comm.c:311, 2384``) plays a related role for ``act()``-driven
triggers, but the SPEECH path in do_say has its own static gate at the
loop head — it never enters the listener loop when the speaker is an
NPC.

Python's ``mud/commands/communication.py:do_say`` (lines 168-174) iterates
``char.room.people`` and calls ``mp_speech_trigger`` on every listening
NPC whose position matches its default_pos — but it does NOT check
``char.is_npc`` first.  If an NPC ever calls ``do_say`` (via
``mud/agent/character_agent.py`` or any future agent-driven mob), the
listener loop runs, contradicting ROM.

Status: probe.  If this test FAILS (the SPEECH trigger fires on the
listening NPC when an NPC speaker calls do_say), the gap is real and a
gap-closer follows.  If it PASSES, the contract is enforced by some
other gate and the probe is closed.
"""

from __future__ import annotations

import pytest

from mud.commands.communication import do_say
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
    room_registry.pop(9400, None)


def _make_room() -> Room:
    room = Room(vnum=9400, name="Speech", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9400] = room
    return room


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int = 9401):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def test_npc_speaker_does_not_fire_speech_trigger_on_listener():
    """ROM gate: NPC speakers must not trigger SPEECH on listening NPCs.

    Set up a speaker NPC (with messages list to receive its own self-line)
    and a listener NPC with a SPEECH trigger keyed off a phrase.  The
    listener's trigger fires by appending to a sentinel list on the mob.
    """
    from mud.mobprog import Trigger

    room = _make_room()

    speaker = Character(
        name="speaker",
        is_npc=True,
        level=10,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    speaker.messages = []
    room.people.append(speaker)
    character_registry.append(speaker)

    listener = Character(
        name="listener",
        is_npc=True,
        level=10,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    listener.messages = []
    # Attach a SPEECH trigger whose phrase matches our say.
    prog = _FakeProg(
        trig_type=int(Trigger.SPEECH),
        trig_phrase="hello",
        code='mob echo "TRIGGERED"\n',
        vnum=9401,
    )
    proto = MobIndex(vnum=9401, short_descr="a listener", level=10)
    proto.mprogs = [prog]
    listener.prototype = proto

    room.people.append(listener)
    character_registry.append(listener)

    # Capture trigger firings via a probe wrapper around mp_act_trigger.
    fired: list[tuple[str, str]] = []

    import mud.mobprog as mobprog

    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), argument))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        do_say(speaker, "hello")
    finally:
        mobprog.mp_act_trigger = original

    # ROM gate: NPC speakers do NOT enter the SPEECH listener loop.
    assert fired == [], (
        f"NPC speaker must not fire SPEECH trigger on listening NPCs "
        f"(ROM src/act_comm.c:779 `if (!IS_NPC (ch))`); "
        f"fired triggers: {fired}"
    )


def test_npc_teller_does_not_fire_speech_trigger_on_target():
    """ROM src/act_comm.c:946 — `if (!IS_NPC (ch) && IS_NPC (victim) ...)`.

    do_tell carries the same anti-cascade gate as do_say.  An NPC who
    tells another NPC something must not fire the target's SPEECH
    trigger.
    """
    from mud.commands.communication import do_tell
    from mud.mobprog import Trigger

    room = _make_room()

    speaker = Character(
        name="speaker",
        is_npc=True,
        level=10,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    speaker.messages = []
    speaker.banned_channels = set()
    speaker.comm = 0
    room.people.append(speaker)
    character_registry.append(speaker)

    target = Character(
        name="target",
        is_npc=True,
        level=10,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    target.messages = []
    target.banned_channels = set()
    target.comm = 0
    proto = MobIndex(vnum=9402, short_descr="a target", level=10)
    prog = _FakeProg(
        trig_type=int(Trigger.SPEECH),
        trig_phrase="hello",
        code='mob echo "TELL_TRIGGERED"\n',
        vnum=9402,
    )
    proto.mprogs = [prog]
    target.prototype = proto
    room.people.append(target)
    character_registry.append(target)

    fired: list[tuple[str, str]] = []
    import mud.mobprog as mobprog

    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), argument))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        do_tell(speaker, "target hello")
    finally:
        mobprog.mp_act_trigger = original

    assert fired == [], (
        f"NPC teller must not fire SPEECH trigger on NPC target "
        f"(ROM src/act_comm.c:946); fired triggers: {fired}"
    )
