"""INV-025 sweep — imm_display do_invis/do_incognito act() room lines dispatch TRIG_ACT.

ROM ``src/comm.c:2384`` — inside ``act()``, every NPC recipient whose
descriptor is not CON_PLAYING receives ``mp_act_trigger(buf, to, ch, arg1,
arg2, TRIG_ACT)`` provided the global ``MOBtrigger`` is TRUE. The immortal
display commands ``do_invis`` and ``do_incognito`` have NO ``MOBtrigger =
FALSE`` wrapper around their ``act(TO_ROOM)`` calls, so TRIG_ACT must fire
for NPC recipients.

Targets:
- ``do_invis`` — fade-into-existence TO_ROOM (src/act_wiz.c:4342)
- ``do_invis`` — fade-into-thin-air TO_ROOM (src/act_wiz.c:4348-4350)
- ``do_invis`` — level-set fade-into-thin-air TO_ROOM (src/act_wiz.c:4366)
- ``do_incognito`` — no-longer-cloaked TO_ROOM (src/act_wiz.c:4388)
- ``do_incognito`` — cloaks-presence TO_ROOM (src/act_wiz.c:4398)
- ``do_incognito`` — level-set cloaks-presence TO_ROOM (src/act_wiz.c:4412)
"""

from __future__ import annotations

import pytest

from mud.commands.imm_display import do_incognito, do_invis
from mud.models.character import Character, PCData, character_registry
from mud.models.constants import Position, Sector
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
    room_registry.pop(9700, None)
    room_registry.pop(9701, None)


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def _make_room(vnum: int = 9700, name: str = "Test Room") -> Room:
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
    return imm


def _make_listener(room: Room, phrase: str, vnum: int = 9701, name: str | None = None) -> Character:
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
# do_invis — src/act_wiz.c:4329-4373
# ---------------------------------------------------------------------------


def test_invis_fade_in_fires_act_trigger_on_npc():
    """ROM src/act_wiz.c:4342 — '$n slowly fades into existence.' TO_ROOM fires TRIG_ACT on NPC."""
    room = _make_room()
    imm = _make_imm(room)
    imm.invis_level = 58
    _make_listener(room, "fades into existence", vnum=9702, name="watcher")

    fired = _recorded_act_triggers(lambda: do_invis(imm, ""))

    watcher_triggers = [(n, m) for n, m in fired if n == "watcher" and "fades into existence" in m.lower()]
    assert len(watcher_triggers) >= 1, f"Expected 'fades into existence' ACT trigger on NPC, got: {fired}"


def test_invis_fade_out_fires_act_trigger_on_npc():
    """ROM src/act_wiz.c:4348-4350 — '$n slowly fades into thin air.' TO_ROOM fires TRIG_ACT on NPC."""
    room = _make_room()
    imm = _make_imm(room)
    _make_listener(room, "fades into thin air", vnum=9703, name="watcher")

    fired = _recorded_act_triggers(lambda: do_invis(imm, ""))

    watcher_triggers = [(n, m) for n, m in fired if n == "watcher" and "fades into thin air" in m.lower()]
    assert len(watcher_triggers) >= 1, f"Expected 'fades into thin air' ACT trigger on NPC, got: {fired}"


def test_invis_level_set_fires_act_trigger_on_npc():
    """ROM src/act_wiz.c:4366 — level-set '$n slowly fades into thin air.' fires TRIG_ACT."""
    room = _make_room()
    imm = _make_imm(room)
    _make_listener(room, "fades into thin air", vnum=9704, name="watcher")

    fired = _recorded_act_triggers(lambda: do_invis(imm, "30"))

    watcher_triggers = [(n, m) for n, m in fired if n == "watcher" and "fades into thin air" in m.lower()]
    assert len(watcher_triggers) >= 1, f"Expected 'fades into thin air' ACT trigger on level-set invis, got: {fired}"


# ---------------------------------------------------------------------------
# do_incognito — src/act_wiz.c:4375-4420
# ---------------------------------------------------------------------------


def test_incognito_uncloak_fires_act_trigger_on_npc():
    """ROM src/act_wiz.c:4388 — '$n is no longer cloaked.' TO_ROOM fires TRIG_ACT on NPC."""
    room = _make_room()
    imm = _make_imm(room)
    imm.incog_level = 58
    _make_listener(room, "no longer cloaked", vnum=9705, name="watcher")

    fired = _recorded_act_triggers(lambda: do_incognito(imm, ""))

    watcher_triggers = [(n, m) for n, m in fired if n == "watcher" and "no longer cloaked" in m.lower()]
    assert len(watcher_triggers) >= 1, f"Expected 'no longer cloaked' ACT trigger on NPC, got: {fired}"


def test_incognito_cloak_fires_act_trigger_on_npc():
    """ROM src/act_wiz.c:4398 — '$n cloaks $s presence.' TO_ROOM fires TRIG_ACT on NPC."""
    room = _make_room()
    imm = _make_imm(room)
    _make_listener(room, "cloaks", vnum=9706, name="watcher")

    fired = _recorded_act_triggers(lambda: do_incognito(imm, ""))

    watcher_triggers = [(n, m) for n, m in fired if n == "watcher" and "cloaks" in m.lower()]
    assert len(watcher_triggers) >= 1, f"Expected 'cloaks' ACT trigger on NPC, got: {fired}"


def test_incognito_level_set_fires_act_trigger_on_npc():
    """ROM src/act_wiz.c:4412 — level-set '$n cloaks $s presence.' fires TRIG_ACT."""
    room = _make_room()
    imm = _make_imm(room)
    _make_listener(room, "cloaks", vnum=9707, name="watcher")

    fired = _recorded_act_triggers(lambda: do_incognito(imm, "30"))

    watcher_triggers = [(n, m) for n, m in fired if n == "watcher" and "cloaks" in m.lower()]
    assert len(watcher_triggers) >= 1, f"Expected 'cloaks' ACT trigger on level-set incognito, got: {fired}"


def test_invis_pc_bystander_no_trigger():
    """PC bystanders do not receive TRIG_ACT — only NPCs (src/comm.c:2384 gate)."""
    room = _make_room()
    imm = _make_imm(room)
    _make_pc_listener(room, name="pc_watcher")

    import mud.mobprog as mobprog

    fired_count = [0]
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired_count[0] += 1
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        do_invis(imm, "")
    finally:
        mobprog.mp_act_trigger = original

    assert fired_count[0] == 0, f"Expected no TRIG_ACT fires on PC bystander, got {fired_count[0]}"


def _make_pc_listener(room: Room, name: str = "pc_watcher") -> Character:
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
    return pc
