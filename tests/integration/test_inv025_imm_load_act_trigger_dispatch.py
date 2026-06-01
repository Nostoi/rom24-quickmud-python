"""INV-025 sweep — imm_load act() lines dispatch TRIG_ACT.

ROM ``src/comm.c:2384`` dispatches ``mp_act_trigger`` from inside ``act()``
for NPC recipients when ``MOBtrigger`` is true. The immortal load/purge/restore
calls covered here have no ``MOBtrigger = FALSE`` wrapper.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from mud.commands.imm_load import do_mload, do_oload, do_purge, do_restore
from mud.models.character import Character, PCData, character_registry
from mud.models.constants import ActFlag, Position, Sector
from mud.models.mob import MobIndex
from mud.models.room import Room


@pytest.fixture(autouse=True)
def _cleanup():
    from mud import registry

    snapshot = list(character_registry)
    character_registry.clear()
    prev_char_list = list(getattr(registry, "char_list", []))
    prev_players = dict(getattr(registry, "players", {})) if hasattr(registry, "players") else {}
    mob_registry = getattr(registry, "mob_registry", {})
    obj_registry = getattr(registry, "obj_registry", {})
    prev_mob_registry = dict(mob_registry)
    prev_obj_registry = dict(obj_registry)
    registry.char_list = []
    registry.players = {}
    mob_registry.clear()
    obj_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)
    registry.char_list = prev_char_list
    registry.players = prev_players
    mob_registry.clear()
    mob_registry.update(prev_mob_registry)
    obj_registry.clear()
    obj_registry.update(prev_obj_registry)


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def _make_room(vnum: int = 9900) -> Room:
    room = Room(
        vnum=vnum,
        name="Test Room",
        description="",
        room_flags=0,
        sector_type=int(Sector.INSIDE),
    )
    room.people = []
    room.contents = []
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


def _make_npc(room: Room, name: str, *, phrase: str | None = None, vnum: int = 9901) -> Character:
    from mud import registry
    from mud.mobprog import Trigger

    npc = Character(
        name=name,
        is_npc=True,
        level=10,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    npc.messages = []
    npc.inventory = []
    npc.equipment = {}
    proto = MobIndex(vnum=vnum, short_descr=name.replace("_", " "), level=10)
    if phrase is not None:
        proto.mprogs = [
            _FakeProg(
                trig_type=int(Trigger.ACT),
                trig_phrase=phrase,
                code='mob echo "ACT_SEEN"\n',
                vnum=vnum,
            )
        ]
    npc.prototype = proto
    room.people.append(npc)
    character_registry.append(npc)
    registry.char_list.append(npc)
    return npc


def _recorded_act_triggers(monkeypatch, call):
    import mud.mobprog as mobprog

    fired: list[tuple[str, str]] = []

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), str(argument)))

    monkeypatch.setattr(mobprog, "mp_act_trigger", _probe)
    call()
    return fired


def test_mload_room_broadcast_fires_act_trigger(monkeypatch):
    """ROM src/act_wiz.c:2512 — mload TO_ROOM act() fires TRIG_ACT on NPC bystanders."""
    import mud.spawning.mob_spawner as mob_spawner
    from mud import registry

    room = _make_room()
    imm = _make_imm(room)
    _make_npc(room, "watcher", phrase="has created", vnum=9902)
    registry.mob_registry[9903] = MobIndex(vnum=9903, short_descr="loaded mob", level=1)

    def _spawn_mob(vnum: int):
        return Character(name="loaded_mob", is_npc=True, level=1, short_descr="loaded mob")

    monkeypatch.setattr(mob_spawner, "spawn_mob", _spawn_mob)

    fired = _recorded_act_triggers(monkeypatch, lambda: do_mload(imm, "9903"))

    assert ("watcher", "Immortal has created loaded mob!") in fired


def test_oload_room_broadcast_fires_act_trigger(monkeypatch):
    """ROM src/act_wiz.c:2566 — oload TO_ROOM act() fires TRIG_ACT on NPC bystanders."""
    import mud.spawning.obj_spawner as obj_spawner
    from mud import registry

    room = _make_room()
    imm = _make_imm(room)
    _make_npc(room, "watcher", phrase="has created", vnum=9904)
    registry.obj_registry[9905] = SimpleNamespace(vnum=9905, short_descr="loaded relic")

    def _spawn_object(vnum: int):
        return SimpleNamespace(
            level=0,
            wear_flags=0,
            short_descr="loaded relic",
            prototype=registry.obj_registry[vnum],
        )

    monkeypatch.setattr(obj_spawner, "spawn_object", _spawn_object)

    fired = _recorded_act_triggers(monkeypatch, lambda: do_oload(imm, "9905"))

    assert ("watcher", "Immortal has created loaded relic!") in fired


def test_purge_npc_notvict_fires_act_trigger(monkeypatch):
    """ROM src/act_wiz.c:2645 — purge NPC TO_NOTVICT act() fires TRIG_ACT on bystander NPCs."""
    room = _make_room()
    imm = _make_imm(room)
    victim = _make_npc(room, "target_npc", vnum=9906)
    _make_npc(room, "watcher", phrase="purges", vnum=9907)

    fired = _recorded_act_triggers(monkeypatch, lambda: do_purge(imm, victim.name))

    assert ("watcher", "Immortal purges target_npc.") in fired


def test_purge_room_broadcast_fires_act_trigger_on_nopurge_npc(monkeypatch):
    """ROM src/act_wiz.c:2605 — purge room TO_ROOM act() fires for NPCs left by ACT_NOPURGE."""
    room = _make_room()
    imm = _make_imm(room)
    watcher = _make_npc(room, "watcher", phrase="purges the room", vnum=9908)
    watcher.act = int(ActFlag.NOPURGE)

    fired = _recorded_act_triggers(monkeypatch, lambda: do_purge(imm, ""))

    assert ("watcher", "Immortal purges the room!") in fired


def test_restore_npc_victim_fires_act_trigger(monkeypatch):
    """ROM src/act_wiz.c:2863 — restore target TO_VICT act() fires TRIG_ACT on NPC victims."""
    room = _make_room()
    imm = _make_imm(room)
    victim = _make_npc(room, "patient", phrase="restored you", vnum=9909)
    victim.hit = 1
    victim.max_hit = 20

    fired = _recorded_act_triggers(monkeypatch, lambda: do_restore(imm, victim.name))

    assert ("patient", "Immortal has restored you.") in fired
