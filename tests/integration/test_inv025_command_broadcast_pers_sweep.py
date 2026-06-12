"""INV-025 command-layer ``broadcast_room`` PERS sweep (4th batch).

ROM ``act("$n …", TO_ROOM)`` renders ``$n`` through ``PERS(ch, looker)`` per
recipient (``src/comm.c:act_new``), so an invisible actor renders as "someone"
(capitalized "Someone") to a witness without DETECT_INVIS (INV-027). These
command-layer sites baked the actor name into an f-string (or via
``act_format(recipient=None)``) and shipped it to every recipient through
``protocol.broadcast_room`` — leaking an invisible actor's identity. TRIG_ACT
was already dispatched via a paired ``mp_act_trigger_room``; this sweep collapses
both into a single ``act_to_room`` so the room line is rendered per-recipient.

Sites covered: position (``do_sleep``), session (``do_quit``), inspection
(``do_scan`` look-around + directional peer), imm_load (``do_mload`` ``$N``,
``do_oload`` ``$p``, ``do_purge`` room + ``$N`` TO_NOTVICT), imm_search
(``do_clone`` object ``$p`` + mobile ``$N``).

Each test: invisible actor → witness sees "Someone …"; sighted witness → name.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from mud.commands.imm_load import do_mload, do_oload, do_purge, do_restore
from mud.commands.imm_search import do_clone
from mud.commands.inspection import do_scan
from mud.commands.position import do_sleep
from mud.commands.session import do_quit
from mud.models.character import Character, PCData, character_registry
from mud.models.constants import AffectFlag, Position, Sector
from mud.models.mob import MobIndex
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture(autouse=True)
def _cleanup():
    from mud import registry

    snapshot = list(character_registry)
    character_registry.clear()
    mob_registry = getattr(registry, "mob_registry", {})
    obj_registry = getattr(registry, "obj_registry", {})
    prev_mob_registry = dict(mob_registry)
    prev_obj_registry = dict(obj_registry)
    mob_registry.clear()
    obj_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)
    mob_registry.clear()
    mob_registry.update(prev_mob_registry)
    obj_registry.clear()
    obj_registry.update(prev_obj_registry)
    room_registry.pop(9700, None)


def _room() -> Room:
    room = Room(vnum=9700, name="Vault", description="", room_flags=0, sector_type=int(Sector.INSIDE))
    room.people = []
    room.contents = []
    room.exits = []
    room_registry[9700] = room
    return room


def _actor(room: Room, *, invisible: bool, trust: int = 60) -> Character:
    ch = Character(
        name="Glark",
        is_npc=False,
        level=trust,
        trust=trust,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    ch.messages = []
    ch.inventory = []
    ch.equipment = {}
    ch.pcdata = PCData()
    ch.pcdata.condition = [0, 0, 0, 0]
    ch.condition = ch.pcdata.condition
    room.people.append(ch)
    character_registry.append(ch)
    if invisible:
        ch.add_affect(AffectFlag.INVISIBLE)
    return ch


def _witness(room: Room) -> Character:
    w = Character(name="Witness", is_npc=False, level=18, room=room, position=int(Position.STANDING))
    w.messages = []
    room.people.append(w)
    character_registry.append(w)
    return w


def _npc(room: Room, name: str, *, vnum: int = 9710) -> Character:
    npc = Character(
        name=name,
        is_npc=True,
        level=5,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    npc.messages = []
    npc.prototype = MobIndex(vnum=vnum, short_descr=name.replace("_", " "), level=5)
    npc.short_descr = name.replace("_", " ")
    room.people.append(npc)
    character_registry.append(npc)
    return npc


def _line(witness: Character) -> str:
    return "\n".join(witness.messages)


# ---------------------------------------------------------------------------
# position — do_sleep ("$n goes to sleep.")
# ---------------------------------------------------------------------------


def test_sleep_masks_invisible_actor():
    room = _room()
    ch = _actor(room, invisible=True)
    w = _witness(room)
    w.messages.clear()

    do_sleep(ch, "")

    assert "Someone goes to sleep." in _line(w), w.messages


def test_sleep_shows_name_to_sighted_witness():
    room = _room()
    ch = _actor(room, invisible=False)
    w = _witness(room)
    w.messages.clear()

    do_sleep(ch, "")

    assert "Glark goes to sleep." in _line(w), w.messages


# ---------------------------------------------------------------------------
# session — do_quit ("$n has left the game.")
# ---------------------------------------------------------------------------


def test_quit_masks_invisible_actor():
    room = _room()
    ch = _actor(room, invisible=True)
    ch.position = int(Position.STANDING)
    w = _witness(room)
    w.messages.clear()

    do_quit(ch, "")

    assert "Someone has left the game." in _line(w), w.messages


# ---------------------------------------------------------------------------
# inspection — do_scan (look-around + directional peer)
# ---------------------------------------------------------------------------


def test_scan_look_around_masks_invisible_actor():
    room = _room()
    ch = _actor(room, invisible=True)
    w = _witness(room)
    w.messages.clear()

    do_scan(ch, "")

    assert "Someone looks all around." in _line(w), w.messages


def test_scan_peer_masks_invisible_actor():
    room = _room()
    ch = _actor(room, invisible=True)
    w = _witness(room)
    w.messages.clear()

    do_scan(ch, "north")

    assert "Someone peers intently north." in _line(w), w.messages


# ---------------------------------------------------------------------------
# imm_load — do_mload ("$n has created $N!")
# ---------------------------------------------------------------------------


def test_mload_masks_invisible_actor(monkeypatch):
    import mud.spawning.mob_spawner as mob_spawner
    from mud import registry

    room = _room()
    ch = _actor(room, invisible=True)
    w = _witness(room)
    registry.mob_registry[9711] = MobIndex(vnum=9711, short_descr="a fat dwarf", level=1)
    monkeypatch.setattr(
        mob_spawner, "spawn_mob", lambda vnum: Character(name="dwarf", is_npc=True, level=1, short_descr="a fat dwarf")
    )
    w.messages.clear()

    do_mload(ch, "9711")

    assert "Someone has created a fat dwarf!" in _line(w), w.messages


def test_mload_shows_name_to_sighted_witness(monkeypatch):
    import mud.spawning.mob_spawner as mob_spawner
    from mud import registry

    room = _room()
    ch = _actor(room, invisible=False)
    w = _witness(room)
    registry.mob_registry[9711] = MobIndex(vnum=9711, short_descr="a fat dwarf", level=1)
    monkeypatch.setattr(
        mob_spawner, "spawn_mob", lambda vnum: Character(name="dwarf", is_npc=True, level=1, short_descr="a fat dwarf")
    )
    w.messages.clear()

    do_mload(ch, "9711")

    assert "Glark has created a fat dwarf!" in _line(w), w.messages


# ---------------------------------------------------------------------------
# imm_load — do_oload ("$n has created $p!")
# ---------------------------------------------------------------------------


def test_oload_masks_invisible_actor(monkeypatch):
    import mud.spawning.obj_spawner as obj_spawner
    from mud import registry

    room = _room()
    ch = _actor(room, invisible=True)
    w = _witness(room)
    registry.obj_registry[9712] = SimpleNamespace(vnum=9712, short_descr="a silver ring")
    monkeypatch.setattr(
        obj_spawner,
        "spawn_object",
        lambda vnum: SimpleNamespace(
            level=0, wear_flags=0, short_descr="a silver ring", prototype=registry.obj_registry[vnum]
        ),
    )
    w.messages.clear()

    do_oload(ch, "9712")

    assert "Someone has created a silver ring!" in _line(w), w.messages


# ---------------------------------------------------------------------------
# imm_load — do_purge room ("$n purges the room!") + $N TO_NOTVICT
# ---------------------------------------------------------------------------


def test_purge_room_masks_invisible_actor():
    room = _room()
    ch = _actor(room, invisible=True)
    w = _witness(room)
    w.messages.clear()

    do_purge(ch, "")

    assert "Someone purges the room!" in _line(w), w.messages


def test_purge_npc_notvict_masks_invisible_actor():
    room = _room()
    ch = _actor(room, invisible=True)
    w = _witness(room)
    victim = _npc(room, "target_orc", vnum=9713)
    w.messages.clear()

    do_purge(ch, victim.name)

    assert "Someone purges target orc." in _line(w), w.messages
    # TO_NOTVICT: the victim (about to be extracted) must NOT receive the line.
    assert not any("purges" in m for m in victim.messages), victim.messages


# ---------------------------------------------------------------------------
# imm_search — do_clone (object "$n has created $p." + mobile "$n has created $N.")
# ---------------------------------------------------------------------------


def test_clone_mobile_masks_invisible_actor(monkeypatch):
    import mud.spawning.mob_spawner as mob_spawner

    room = _room()
    ch = _actor(room, invisible=True)
    w = _witness(room)
    source = _npc(room, "orc", vnum=9714)
    monkeypatch.setattr(
        mob_spawner, "spawn_mob", lambda vnum: Character(name="orc", is_npc=True, level=1, short_descr="an orc")
    )
    w.messages.clear()

    do_clone(ch, f"mobile {source.name}")

    assert any("Someone has created" in m for m in w.messages), w.messages


# ---------------------------------------------------------------------------
# imm_load — do_restore (TO_VICT "$n has restored you." — per-victim PERS)
# ---------------------------------------------------------------------------


def test_restore_room_masks_invisible_restorer_to_victim():
    room = _room()
    ch = _actor(room, invisible=True)
    victim = _witness(room)
    victim.hit, victim.max_hit = 1, 30
    victim.messages.clear()

    do_restore(ch, "room")

    assert "Someone has restored you." in _line(victim), victim.messages


def test_restore_room_shows_name_to_sighted_victim():
    room = _room()
    ch = _actor(room, invisible=False)
    victim = _witness(room)
    victim.hit, victim.max_hit = 1, 30
    victim.messages.clear()

    do_restore(ch, "room")

    assert "Glark has restored you." in _line(victim), victim.messages


def test_restore_self_renders_name_even_when_invisible():
    """ROM PERS(ch, ch) returns the name (can_see self is TRUE); ROM $n has no
    "You" self-case — so a self-restore renders the actor's name, not "Someone"
    and not "You"."""
    room = _room()
    ch = _actor(room, invisible=True)
    ch.hit, ch.max_hit = 1, 30
    ch.messages.clear()

    do_restore(ch, "room")

    assert "Glark has restored you." in _line(ch), ch.messages


# ---------------------------------------------------------------------------
# communication — do_pose (act_format(recipient=None)+broadcast_room, $n)
# ---------------------------------------------------------------------------


def test_pose_masks_invisible_actor():
    from mud.commands.communication import do_pose
    from mud.utils import rng_mm

    room = _room()
    ch = _actor(room, invisible=True)
    ch.ch_class = 0
    ch.level = 10
    w = _witness(room)
    w.messages.clear()

    rng_mm.seed_mm(12345)
    do_pose(ch, "")

    line = _line(w)
    assert line, w.messages
    assert "Glark" not in line, w.messages


def test_pose_shows_name_to_sighted_witness():
    from mud.commands.communication import do_pose
    from mud.utils import rng_mm

    room = _room()
    ch = _actor(room, invisible=False)
    ch.ch_class = 0
    ch.level = 10
    w = _witness(room)
    w.messages.clear()

    rng_mm.seed_mm(12345)
    do_pose(ch, "")

    # Same seed as the masking test → same pose; visible actor must render its
    # name (confirms the seeded pose actually contains $n, so the mask test bites).
    assert "Glark" in _line(w), w.messages


# ---------------------------------------------------------------------------
# admin — cmd_incognito ("$n cloaks $s presence." baked-name broadcast)
# ---------------------------------------------------------------------------


def test_incognito_masks_invisible_actor():
    from mud.commands.admin_commands import cmd_incognito

    room = _room()
    ch = _actor(room, invisible=True, trust=60)
    w = _witness(room)
    w.messages.clear()

    cmd_incognito(ch, "")

    assert "Someone cloaks" in _line(w), w.messages
    assert "Glark" not in _line(w), w.messages
