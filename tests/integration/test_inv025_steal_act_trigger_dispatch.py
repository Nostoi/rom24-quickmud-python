"""INV-025 sweep - steal failure act() room lines dispatch TRIG_ACT.

ROM ``src/act_obj.c:2223-2224`` emits steal-failure visible
lines through unsuppressed ``act()`` calls (no MOBtrigger wrapper).
Per ``src/comm.c:2384``, matching NPC recipients must receive TRIG_ACT.

- L2223: act("$n tried to steal from you.", ch, NULL, victim, TO_VICT)
- L2224: act("$n tried to steal from $N.",  ch, NULL, victim, TO_NOTVICT)
"""

from __future__ import annotations

import pytest

from mud.commands.thief_skills import do_steal
from mud.models.character import Character, PCData, character_registry
from mud.models.constants import Position
from mud.models.room import Room
from mud.registry import room_registry
from mud.utils.rng_mm import seed_mm


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)
    room_registry.pop(9700, None)


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def _make_room() -> Room:
    room = Room(vnum=9700, name="Thief Alley", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9700] = room
    return room


def _make_pc(room: Room, name: str = "thief") -> Character:
    pc = Character(
        name=name,
        is_npc=False,
        level=20,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    pc.messages = []
    pc.inventory = []
    pc.equipment = {}
    pc.pcdata = PCData()
    pc.skills = {"steal": 0}
    pc.gold = 100
    pc.silver = 100
    room.people.append(pc)
    character_registry.append(pc)
    return pc


def _make_pc_victim(room: Room, name: str = "victim") -> Character:
    pc = Character(
        name=name,
        is_npc=False,
        level=20,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    pc.messages = []
    pc.inventory = []
    pc.equipment = {}
    pc.pcdata = PCData()
    pc.gold = 200
    pc.silver = 200
    room.people.append(pc)
    character_registry.append(pc)
    return pc


def _make_listener(room: Room, phrase: str, vnum: int = 9701, name: str | None = None) -> Character:
    from mud.mobprog import Trigger
    from mud.models.mob import MobIndex

    listener = Character(
        name=name or f"watcher_{vnum}",
        is_npc=True,
        level=10,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    listener.messages = []
    listener.inventory = []
    listener.equipment = {}
    proto = MobIndex(vnum=vnum, short_descr="a watcher", level=10)
    proto.mprogs = [
        _FakeProg(
            trig_type=int(Trigger.ACT),
            trig_phrase=phrase,
            code='mob echo "STEAL_SEEN"\n',
            vnum=vnum,
        )
    ]
    listener.prototype = proto
    room.people.append(listener)
    character_registry.append(listener)
    return listener


def _recorded_act_triggers(call):
    import mud.mobprog as mobprog

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        call()
    finally:
        mobprog.mp_act_trigger = original
    return fired


def test_steal_failure_to_vict_fires_act_trigger_on_npc_victim():
    """ROM src/act_obj.c:2223 / src/comm.c:2384 - TO_VICT act() fires TRIG_ACT on victim NPC.

    Using a PC thief against an NPC victim with ACT trigger.
    Steal fails (skill=0, no clan). The victim NPC must receive TRIG_ACT
    with the "tried to steal from you" message.
    """
    room = _make_room()
    pc = _make_pc(room)
    # NPC victim with ACT trigger — will also be attacked by multi_hit
    # but the steal-failure TO_VICT message must still be in the triggers
    _make_listener(room, "tried to steal", vnum=9702, name="target")
    seed_mm(42)

    fired = _recorded_act_triggers(lambda: do_steal(pc, "coin target"))

    victim_steal_triggers = [(n, m) for n, m in fired if n == "target" and "tried to steal" in m.lower()]
    assert len(victim_steal_triggers) >= 1, f"Expected 'tried to steal' in victim NPC triggers, got: {fired}"


def test_steal_failure_to_notvict_fires_act_trigger_on_npc_bystander():
    """ROM src/act_obj.c:2224 / src/comm.c:2384 - TO_NOTVICT act() fires TRIG_ACT on bystander NPC.

    Using a PC thief stealing from a PC victim (no multi_hit).
    A bystander NPC with ACT trigger must receive TRIG_ACT with
    the "tried to steal from $N" message.
    """
    room = _make_room()
    pc = _make_pc(room)
    # PC victim — avoids multi_hit noise
    _make_pc_victim(room, name="target")
    _make_listener(room, "tried to steal", vnum=9704, name="bystander")
    seed_mm(42)

    fired = _recorded_act_triggers(lambda: do_steal(pc, "coin target"))

    bystander_steal_triggers = [(n, m) for n, m in fired if n == "bystander" and "tried to steal" in m.lower()]
    assert len(bystander_steal_triggers) >= 1, f"Expected 'tried to steal' in bystander NPC triggers, got: {fired}"


def test_steal_failure_pc_victim_sees_message():
    """Steal failure delivers the TO_VICT message to a PC victim's mailbox."""
    room = _make_room()
    pc = _make_pc(room)
    victim = _make_pc_victim(room, name="target")
    seed_mm(42)

    do_steal(pc, "coin target")

    victim_msgs = "".join(victim.messages)
    assert "tried to steal from you" in victim_msgs.lower(), (
        f"Expected 'tried to steal from you' in victim messages, got: {victim_msgs}"
    )


def test_steal_failure_no_act_trigger_when_mobtrigger_suppressed():
    """When MOBtrigger is suppressed, steal failure must NOT fire TRIG_ACT.

    This mirrors the ROM behaviour where MOBtrigger=FALSE gates the
    dispatch in src/comm.c:2384. The steal-failure act() calls are NOT
    wrapped in MOBtrigger=FALSE, so they should always dispatch.
    This test confirms the guard mechanism works — if we manually
    suppress MOBtrigger, no steal-failure TRIG_ACT fires.
    """
    import mud.mobprog as mobprog

    room = _make_room()
    pc = _make_pc(room)
    _make_pc_victim(room, name="target")
    _make_listener(room, "tried to steal", vnum=9705, name="bystander")
    seed_mm(42)

    mobprog.MOBtrigger = False
    fired = _recorded_act_triggers(lambda: do_steal(pc, "coin target"))
    mobprog.MOBtrigger = True

    steal_triggers = [(n, m) for n, m in fired if "tried to steal" in m.lower()]
    assert len(steal_triggers) == 0, f"Expected no steal TRIG_ACT when MOBtrigger=False, got: {fired}"
