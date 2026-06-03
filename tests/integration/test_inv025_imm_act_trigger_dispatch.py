"""INV-025 sweep — immortal command act() room lines dispatch TRIG_ACT.

ROM ``src/comm.c:2384`` — inside ``act()``, every NPC recipient whose
descriptor is not CON_PLAYING receives ``mp_act_trigger(buf, to, ch, arg1,
arg2, TRIG_ACT)`` provided the global ``MOBtrigger`` is TRUE. The immortal
command ``act()`` calls probed in this file have NO ``MOBtrigger = FALSE``
wrapper, so TRIG_ACT must fire for NPC recipients.

Targets:
- ``do_transfer`` — departure mushroom-cloud (TO_ROOM) and arrival puff-of-smoke
  (TO_ROOM) + victim notification (TO_VICT) (src/act_wiz.c:870,873,875).
- ``do_goto`` — bamfout (TO_VICT per-recipient, invis_level-gated) and bamfin
  (TO_VICT per-recipient, invis_level-gated)
  (src/act_wiz.c:969-978,984-994).
- ``do_violate`` — same bamf structure (src/act_wiz.c:1026-1035,1041-1051).
- ``do_force`` single-target — TO_VICT (src/act_wiz.c:4316).
"""

from __future__ import annotations

import pytest

from mud.commands.imm_commands import do_force, do_goto, do_transfer
from mud.commands.imm_server import do_violate
from mud.models.character import Character, PCData, character_registry
from mud.models.constants import Position, RoomFlag, Sector
from mud.models.mob import MobIndex
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture(autouse=True)
def _cleanup():
    from mud import registry

    snapshot = list(character_registry)
    character_registry.clear()
    prev_char_list = list(getattr(registry, "char_list", []))
    prev_players = dict(getattr(registry, "players", {})) if hasattr(registry, "players") else {}
    # Ensure registry has char_list and players
    registry.char_list = []
    registry.players = {}
    yield
    character_registry.clear()
    character_registry.extend(snapshot)
    registry.char_list = prev_char_list
    registry.players = prev_players
    room_registry.pop(9800, None)
    room_registry.pop(9801, None)


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def _make_room(vnum: int = 9800, name: str = "Test Room") -> Room:
    room = Room(
        vnum=vnum,
        name=name,
        description="",
        room_flags=0,
        sector_type=int(Sector.INSIDE),
    )
    room.people = []
    room.contents = []
    room_registry[vnum] = room
    return room


def _make_imm(room: Room, name: str = "Immortal", trust: int = 60) -> Character:
    from mud import registry

    imm = Character(
        name=name,
        is_npc=False,
        level=trust,
        trust=trust,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    imm.messages = []
    imm.inventory = []
    imm.equipment = {}
    imm.pcdata = PCData()
    room.people.append(imm)
    character_registry.append(imm)
    registry.char_list.append(imm)
    registry.players[name.lower()] = imm
    return imm


def _make_pc(room: Room, name: str = "Victim") -> Character:
    from mud import registry

    pc = Character(
        name=name,
        is_npc=False,
        level=10,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    pc.messages = []
    pc.inventory = []
    pc.equipment = {}
    pc.pcdata = PCData()
    room.people.append(pc)
    character_registry.append(pc)
    registry.char_list.append(pc)
    registry.players[name.lower()] = pc
    return pc


def _make_listener(room: Room, phrase: str, vnum: int = 9801, name: str | None = None) -> Character:
    from mud import registry
    from mud.mobprog import Trigger

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
            code='mob echo "ACT_SEEN"\n',
            vnum=vnum,
        )
    ]
    listener.prototype = proto
    room.people.append(listener)
    character_registry.append(listener)
    registry.char_list.append(listener)
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


# ---------------------------------------------------------------------------
# do_transfer — src/act_wiz.c:870,873,875
# ---------------------------------------------------------------------------


def test_transfer_departure_fires_act_trigger_on_npc_bystander():
    """ROM src/act_wiz.c:870 — mushroom-cloud TO_ROOM fires TRIG_ACT on NPC bystanders."""
    old_room = _make_room(9800, "Old Room")
    new_room = _make_room(9801, "New Room")
    imm = _make_imm(old_room)
    _make_pc(old_room, name="Victim")
    _make_listener(old_room, "mushroom cloud", vnum=9802, name="bystander")

    fired = _recorded_act_triggers(lambda: do_transfer(imm, f"Victim {new_room.vnum}"))

    bystander_triggers = [(n, m) for n, m in fired if n == "bystander" and "mushroom" in m.lower()]
    assert len(bystander_triggers) >= 1, f"Expected 'mushroom cloud' ACT trigger on departure bystander, got: {fired}"


def test_transfer_arrival_fires_act_trigger_on_npc_bystander():
    """ROM src/act_wiz.c:873 — puff-of-smoke TO_ROOM fires TRIG_ACT on NPC bystanders."""
    old_room = _make_room(9800, "Old Room")
    new_room = _make_room(9801, "New Room")
    imm = _make_imm(old_room)
    _make_pc(old_room, name="Victim")
    _make_listener(new_room, "puff of smoke", vnum=9803, name="arriver")

    fired = _recorded_act_triggers(lambda: do_transfer(imm, f"Victim {new_room.vnum}"))

    arriver_triggers = [(n, m) for n, m in fired if n == "arriver" and "puff" in m.lower()]
    assert len(arriver_triggers) >= 1, f"Expected 'puff of smoke' ACT trigger on arrival bystander, got: {fired}"


def test_transfer_vict_fires_act_trigger_on_npc_victim():
    """ROM src/act_wiz.c:875 — TO_VICT 'has transferred you' fires TRIG_ACT on NPC victim."""
    old_room = _make_room(9800, "Old Room")
    new_room = _make_room(9801, "New Room")
    imm = _make_imm(old_room)

    from mud import registry
    from mud.mobprog import Trigger

    victim = Character(
        name="target_npc",
        is_npc=True,
        level=10,
        room=old_room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    victim.messages = []
    victim.inventory = []
    victim.equipment = {}
    proto = MobIndex(vnum=9804, short_descr="a target npc", level=10)
    proto.mprogs = [
        _FakeProg(
            trig_type=int(Trigger.ACT),
            trig_phrase="transferred",
            code='mob echo "ACT_SEEN"\n',
            vnum=9804,
        )
    ]
    victim.prototype = proto
    old_room.people.append(victim)
    character_registry.append(victim)
    registry.char_list.append(victim)

    fired = _recorded_act_triggers(lambda: do_transfer(imm, f"target_npc {new_room.vnum}"))

    victim_triggers = [(n, m) for n, m in fired if n == "target_npc" and "transferred" in m.lower()]
    assert len(victim_triggers) >= 1, f"Expected 'transferred' ACT trigger on NPC victim, got: {fired}"


# ---------------------------------------------------------------------------
# do_goto — src/act_wiz.c:969-978,984-994
# ---------------------------------------------------------------------------


def test_goto_bamfout_fires_act_trigger_on_npc_witness():
    """ROM src/act_wiz.c:969-978 — bamfout act(TO_VICT) fires TRIG_ACT on NPC witnesses."""
    old_room = _make_room(9800, "Old Room")
    new_room = _make_room(9801, "New Room")
    imm = _make_imm(old_room)
    _make_listener(old_room, "swirling mist", vnum=9805, name="watcher")

    fired = _recorded_act_triggers(lambda: do_goto(imm, str(new_room.vnum)))

    watcher_triggers = [(n, m) for n, m in fired if n == "watcher" and "mist" in m.lower()]
    assert len(watcher_triggers) >= 1, f"Expected 'swirling mist' ACT trigger on goto departure, got: {fired}"


def test_goto_bamfin_fires_act_trigger_on_npc_witness():
    """ROM src/act_wiz.c:984-994 — bamfin act(TO_VICT) fires TRIG_ACT on NPC witnesses."""
    old_room = _make_room(9800, "Old Room")
    new_room = _make_room(9801, "New Room")
    imm = _make_imm(old_room)
    _make_listener(new_room, "swirling mist", vnum=9806, name="arrival_watcher")

    fired = _recorded_act_triggers(lambda: do_goto(imm, str(new_room.vnum)))

    arrival_triggers = [(n, m) for n, m in fired if n == "arrival_watcher" and "mist" in m.lower()]
    assert len(arrival_triggers) >= 1, f"Expected 'mist' ACT trigger on goto arrival, got: {fired}"


# ---------------------------------------------------------------------------
# do_violate — src/act_wiz.c:1026-1035,1041-1051
# ---------------------------------------------------------------------------


def test_violate_bamfout_fires_act_trigger_on_npc_witness():
    """ROM src/act_wiz.c:1026-1035 — bamfout act(TO_VICT) fires TRIG_ACT on NPC witnesses."""
    private_room = _make_room(9801, "Private Room")
    private_room.room_flags = int(RoomFlag.ROOM_PRIVATE)
    # Need ≥2 people in the private room for _room_is_private to return True
    _make_pc(private_room, name="occupant")
    _make_pc(private_room, name="occupant2")
    old_room = _make_room(9800, "Old Room")
    imm = _make_imm(old_room)
    _make_listener(old_room, "swirling mist", vnum=9807, name="dep_watcher")

    fired = _recorded_act_triggers(lambda: do_violate(imm, str(private_room.vnum)))

    dep_triggers = [(n, m) for n, m in fired if n == "dep_watcher" and "mist" in m.lower()]
    assert len(dep_triggers) >= 1, f"Expected 'mist' ACT trigger on violate departure, got: {fired}"


# ---------------------------------------------------------------------------
# do_force single-target — src/act_wiz.c:4316
# ---------------------------------------------------------------------------


def test_force_single_npc_target_fires_act_trigger():
    """ROM src/act_wiz.c:4316 — force 'TO_VICT' act() fires TRIG_ACT on NPC victim."""
    room = _make_room(9800, "Test Room")
    imm = _make_imm(room, trust=60)

    _make_listener(room, "forces you to", vnum=9808, name="forced_npc")

    fired = _recorded_act_triggers(lambda: do_force(imm, "forced_npc smile"))

    npc_triggers = [(n, m) for n, m in fired if n == "forced_npc" and "forces you to" in m.lower()]
    assert len(npc_triggers) >= 1, f"Expected 'forces you to' ACT trigger on forced NPC, got: {fired}"


def test_force_single_pc_target_does_not_fire_act_trigger():
    """ROM src/act_wiz.c:4316 — force on PC victim must NOT fire TRIG_ACT.

    PCs have descriptors so src/comm.c:2384 skips them. In our port,
    mp_act_trigger checks is_npc.
    """
    room = _make_room(9800, "Test Room")
    imm = _make_imm(room, trust=60)
    _make_pc(room, name="lowly")

    import mud.mobprog as mobprog

    fired_count = [0]
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired_count[0] += 1
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        do_force(imm, "lowly smile")
    finally:
        mobprog.mp_act_trigger = original

    assert fired_count[0] == 0, f"Expected no TRIG_ACT fires on PC force target, got {fired_count[0]} triggers"
