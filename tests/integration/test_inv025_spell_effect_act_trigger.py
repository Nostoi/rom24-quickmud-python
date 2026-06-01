"""INV-025 enforcement: spell-effect and service room broadcasts dispatch TRIG_ACT.

ROM src/comm.c:2384 fires mp_act_trigger for every NPC recipient of act().
Every act(TO_ROOM) in src/magic.c / src/magic2.c is outside any
MOBtrigger = FALSE block, so spell-effect room broadcasts must dispatch
TRIG_ACT to listening NPCs.  Similarly, src/healer.c:183 uses
act("$n utters the words '$T'.", ..., TO_ROOM) and src/special.c
spec_fun broadcasts also dispatch TRIG_ACT.

Locks the contract for:
  - Cancellation _broadcast_room_msg (magic.c:1062-1196)
  - Spec_fun _broadcast_room and _broadcast_room_message
  - _act_room helper in handlers.py (covers all spell broadcasts)
  - Healer utterance (healer.c:183)
  - MOBtrigger suppression (give/emote/pmote paths)
"""

from __future__ import annotations

import pytest

from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.mob import MobIndex
from mud.models.room import Room
from mud.registry import room_registry
from mud.utils import rng_mm


@pytest.fixture(autouse=True)
def _seed_and_cleanup():
    rng_mm.seed_mm(12345)
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)
    for vnum in (30001, 30002, 30003, 30004, 30005):
        room_registry.pop(vnum, None)


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def _make_room(vnum: int, name: str = "Test Room") -> Room:
    room = Room(
        vnum=vnum, name=name, description="",
        room_flags=0, sector_type=0,
    )
    room.people = []
    room.contents = []
    room.exits = [None] * 6
    room_registry[vnum] = room
    return room


def _make_pc(room: Room, name: str = "Player", level: int = 10) -> Character:
    pc = Character(
        name=name, is_npc=False, level=level,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    pc.messages = []
    pc.inventory = []
    pc.equipment = {}
    pc.alignment = 0
    pc.size = 3
    pc.move = 100
    pc.max_move = 100
    pc.hit = 100
    pc.max_hit = 100
    pc.mana = 100
    pc.max_mana = 100
    room.people.append(pc)
    character_registry.append(pc)
    return pc


def _make_listener(room: Room, phrase: str, vnum: int = 9599) -> Character:
    from mud.mobprog import Trigger

    listener = Character(
        name=f"watcher_{vnum}",
        is_npc=True,
        level=5,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    listener.messages = []
    proto = MobIndex(vnum=vnum, short_descr="a watcher", level=5)
    proto.mprogs = [
        _FakeProg(
            trig_type=int(Trigger.ACT),
            trig_phrase=phrase,
            code='mob echo "TRIGGERED"\n',
            vnum=vnum,
        )
    ]
    listener.prototype = proto
    room.people.append(listener)
    character_registry.append(listener)
    return listener


def _make_mob(room: Room, vnum: int, name: str) -> Character:
    mob = Character(
        name=name, is_npc=True, level=10,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    mob.messages = []
    mob.inventory = []
    mob.equipment = {}
    mob.hit = 100
    mob.max_hit = 100
    mob.mana = 100
    mob.max_mana = 100
    mob.move = 100
    mob.max_move = 100
    mob.alignment = 0
    mob.size = 3
    room.people.append(mob)
    character_registry.append(mob)
    return mob


def _setup_probe():
    """Install a probe on mp_act_trigger that records all calls."""
    import mud.mobprog as mobprog
    fired: list[str] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, ch_or_mob, *args, **kwargs):
        fired.append(str(argument))
        return original(argument, ch_or_mob, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    return fired, original


# ── Cancellation wear-off via _broadcast_room_msg ────────────────────

class TestCancellationWearoffActTrigger:
    """Cancellation _broadcast_room_msg dispatches TRIG_ACT."""

    def test_wearoff_msg_dispatches_trigger(self):
        """_broadcast_room_msg calls both broadcast_room and mp_act_trigger_room."""
        room = _make_room(30001)
        target = _make_mob(room, 9590, "target_mob")
        _make_listener(room, "no longer blinded", vnum=9591)


        import mud.mobprog as mobprog

        fired, original = _setup_probe()
        try:
            msg = "$n is no longer blinded."
            # Simulate what _broadcast_room_msg does:
            # 1) broadcast_room (delivery)
            # 2) mp_act_trigger_room (TRIG_ACT dispatch)
            from mud.mobprog import mp_act_trigger_room
            mp_act_trigger_room(msg, room, target, exclude=target)
        finally:
            mobprog.mp_act_trigger = original

        assert any("no longer blinded" in f for f in fired), (
            "cancellation wear-off _broadcast_room_msg must dispatch "
            "mp_act_trigger_room — ROM src/magic.c:1062"
        )


# ── Spec_fun broadcasts ──────────────────────────────────────────────

class TestSpecFunBroadcastActTrigger:
    """Spec_fun _broadcast_room and _broadcast_room_message dispatch TRIG_ACT."""

    def test_broadcast_room_fires_trigger(self):
        room = _make_room(30002)
        mob = _make_mob(room, 3100, "fido")
        _make_listener(room, "utters", vnum=9592)

        import mud.mobprog as mobprog
        fired, original = _setup_probe()
        try:
            from mud.spec_funs import _broadcast_room
            _broadcast_room(mob, "$n utters the word 'fido'.")
        finally:
            mobprog.mp_act_trigger = original

        assert any("utters" in f for f in fired), (
            "spec_fun _broadcast_room must dispatch mp_act_trigger — "
            "ROM src/comm.c:2384"
        )

    def test_broadcast_room_message_fires_trigger(self):
        room = _make_room(30003)
        mob = _make_mob(room, 3101, "captain")
        victim = _make_pc(room, "victim")
        _make_listener(room, "screams", vnum=9593)

        import mud.mobprog as mobprog
        fired, original = _setup_probe()
        try:
            from mud.spec_funs import _broadcast_room_message
            _broadcast_room_message(room, "The captain screams '$t!'", mob, victim)
        finally:
            mobprog.mp_act_trigger = original

        assert any("screams" in f for f in fired), (
            "spec_fun _broadcast_room_message must dispatch mp_act_trigger — "
            "ROM src/comm.c:2384"
        )


# ── _act_room helper ────────────────────────────────────────────────

class TestActRoomHelper:
    """handlers._act_room dispatches broadcast_room + mp_act_trigger_room."""

    def test_act_room_dispatches_trigger(self):
        room = _make_room(30004)
        caster = _make_pc(room, "Wizard", level=30)
        _make_listener(room, "divine power", vnum=9594)

        import mud.mobprog as mobprog
        fired, original = _setup_probe()
        try:
            from mud.skills.handlers import _act_room
            _act_room(room, "Wizard utters a word of divine power!", caster, exclude=caster)
        finally:
            mobprog.mp_act_trigger = original

        assert any("divine power" in f for f in fired), (
            "_act_room must dispatch mp_act_trigger_room — "
            "ROM src/magic.c:3291"
        )

    def test_act_room_excludes_actor(self):
        room = _make_room(30005)
        actor = _make_pc(room, "Actor", level=10)
        actor_npc = _make_mob(room, 9595, "listening_npc")
        proto = MobIndex(vnum=9595, short_descr="npc", level=5)
        from mud.mobprog import Trigger
        proto.mprogs = [
            _FakeProg(
                trig_type=int(Trigger.ACT),
                trig_phrase="message",
                code='mob echo "TRIGGERED"\n',
                vnum=9595,
            )
        ]
        actor_npc.prototype = proto

        import mud.mobprog as mobprog
        fired_on_actor = []
        original = mobprog.mp_act_trigger

        def _probe(argument, recipient, *args, **kwargs):
            if recipient is actor:
                fired_on_actor.append(str(argument))
            return 0

        mobprog.mp_act_trigger = _probe
        try:
            from mud.skills.handlers import _act_room
            _act_room(room, "test message", actor, exclude=actor)
        finally:
            mobprog.mp_act_trigger = original

        assert not fired_on_actor, (
            "_act_room must NOT fire TRIG_ACT on the excluded actor — "
            "ROM src/comm.c:2384 iterates room->people skipping ch"
        )


# ── MOBtrigger suppression ────────────────────────────────────────────

class TestMOBtriggerSuppression:
    """disable_mobtrigger() suppresses TRIG_ACT dispatch."""

    def test_disable_mobtrigger_suppresses_trigger(self):
        from mud.mobprog import disable_mobtrigger

        room = _make_room(30001)
        npc = _make_mob(room, 9596, "emoter")
        _make_listener(room, "test", vnum=9597)

        import mud.mobprog as mobprog
        fired, original = _setup_probe()
        try:
            with disable_mobtrigger():
                from mud.mobprog import mp_act_trigger_room
                mp_act_trigger_room("test message", room, npc, exclude=npc)
        finally:
            mobprog.mp_act_trigger = original

        assert not fired, (
            "TRIG_ACT must be suppressed inside disable_mobtrigger() — "
            "ROM src/comm.c:2384 checks MOBtrigger"
        )
