"""Integration tests for mob_cmds.c edge cases (P1-8 closeout).

Covers ROM parity gaps in `mpat`, `mptransfer`, `mppurge`, and the
mobprog variable substitution surface (`expand_arg`).

ROM C reference: src/mob_cmds.c (do_mpat/do_mptransfer/do_mppurge),
src/mob_prog.c (expand_arg).
"""

from __future__ import annotations

import pytest

from mud import mob_cmds
from mud import mobprog
from mud.models.area import Area
from mud.models.character import Character, character_registry
from mud.models.constants import ActFlag, ITEM_NOPURGE, RoomFlag
from mud.models.mob import MobIndex, MobProgram
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Exit, Room
from mud.registry import area_registry, mob_registry, obj_registry, room_registry


@pytest.fixture(autouse=True)
def clear_registries():
    room_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    area_registry.clear()
    character_registry.clear()
    yield
    room_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    area_registry.clear()
    character_registry.clear()


def _setup_area(vnum: int = 1) -> tuple[Area, Room, Room]:
    area = Area(vnum=vnum, name="Edge Area")
    area_registry[vnum] = area
    origin = Room(vnum=100 + vnum, name="Origin", area=area)
    destination = Room(vnum=200 + vnum, name="Destination", area=area)
    origin.exits[0] = Exit(to_room=destination)
    destination.exits[2] = Exit(to_room=origin)
    room_registry[origin.vnum] = origin
    room_registry[destination.vnum] = destination
    return area, origin, destination


# ---------------------------------------------------------------------------
# mpat
# ---------------------------------------------------------------------------


def test_mpat_round_trip_returns_mob_to_origin(monkeypatch):
    """`mpat <vnum> <cmd>` runs the command in the destination then returns."""
    _, origin, destination = _setup_area()

    mob = Character(name="Wanderer", is_npc=True)
    origin.add_character(mob)
    character_registry.append(mob)

    rooms_seen: list[int | None] = []

    def fake_process(char: Character, command: str) -> str:
        rooms_seen.append(getattr(char.room, "vnum", None))
        return ""

    monkeypatch.setattr("mud.commands.dispatcher.process_command", fake_process)

    mob_cmds.mob_interpret(mob, f"at {destination.vnum} say hi")

    assert rooms_seen == [destination.vnum]
    # Mob is back where it started after the at-command.
    assert mob.room is origin
    assert mob in origin.people
    assert mob not in destination.people


# ---------------------------------------------------------------------------
# mptransfer
# ---------------------------------------------------------------------------


def test_mptransfer_single_target_moves_player_and_auto_looks(monkeypatch):
    _, origin, destination = _setup_area()

    mob = Character(name="Caller", is_npc=True)
    origin.add_character(mob)
    character_registry.append(mob)

    hero = Character(name="Hero", is_npc=False)
    origin.add_character(hero)
    character_registry.append(hero)
    hero.messages = []

    look_calls: list[tuple[Character, str]] = []

    def fake_look(char: Character, args: str = "") -> str:
        look_calls.append((char, args))
        return "ROOM DESC"

    monkeypatch.setattr("mud.commands.inspection.do_look", fake_look)

    mob_cmds.mob_interpret(mob, f"transfer Hero {destination.vnum}")

    assert hero.room is destination
    assert hero in destination.people
    assert hero not in origin.people
    assert look_calls and look_calls[0][0] is hero and look_calls[0][1] == "auto"
    assert "ROOM DESC" in hero.messages


def test_mptransfer_all_moves_only_players(monkeypatch):
    _, origin, destination = _setup_area()

    mob = Character(name="Caller", is_npc=True)
    origin.add_character(mob)
    character_registry.append(mob)

    npc_buddy = Character(name="Buddy", is_npc=True)
    origin.add_character(npc_buddy)
    character_registry.append(npc_buddy)

    hero = Character(name="Hero", is_npc=False)
    origin.add_character(hero)
    character_registry.append(hero)
    hero.messages = []

    sidekick = Character(name="Sidekick", is_npc=False)
    origin.add_character(sidekick)
    character_registry.append(sidekick)
    sidekick.messages = []

    monkeypatch.setattr("mud.commands.inspection.do_look", lambda c, a="": "")

    mob_cmds.mob_interpret(mob, f"transfer all {destination.vnum}")

    # NPCs (including the running mob) stay put; only PCs are transferred.
    assert mob.room is origin
    assert npc_buddy.room is origin
    assert hero.room is destination
    assert sidekick.room is destination


def test_mptransfer_blocks_private_destination(monkeypatch):
    _, origin, destination = _setup_area()

    # Mark destination ROOM_PRIVATE and seed two occupants so the
    # ROM `room_is_private` predicate returns true.
    destination.room_flags = int(RoomFlag.ROOM_PRIVATE)
    occupant_a = Character(name="OwnerA", is_npc=False)
    destination.add_character(occupant_a)
    character_registry.append(occupant_a)
    occupant_b = Character(name="OwnerB", is_npc=False)
    destination.add_character(occupant_b)
    character_registry.append(occupant_b)

    mob = Character(name="Caller", is_npc=True)
    origin.add_character(mob)
    character_registry.append(mob)

    hero = Character(name="Hero", is_npc=False)
    origin.add_character(hero)
    character_registry.append(hero)

    monkeypatch.setattr("mud.commands.inspection.do_look", lambda c, a="": "")

    mob_cmds.mob_interpret(mob, f"transfer Hero {destination.vnum}")

    # Private destination must reject the transfer (ROM behavior).
    assert hero.room is origin


# ---------------------------------------------------------------------------
# mppurge
# ---------------------------------------------------------------------------


def test_mppurge_whole_room_excludes_pcs_running_mob_and_nopurge(monkeypatch):
    _, room, _ = _setup_area()

    controller_proto = MobIndex(vnum=8000, short_descr="the controller")
    controller = Character(name="Controller", is_npc=True)
    controller.prototype = controller_proto
    room.add_character(controller)
    character_registry.append(controller)

    grunt_proto = MobIndex(vnum=8001, short_descr="a grunt")
    grunt = Character(name="Grunt", is_npc=True)
    grunt.prototype = grunt_proto
    room.add_character(grunt)
    character_registry.append(grunt)

    # ROM ACT_NOPURGE must protect this NPC from a no-arg purge.
    sacred_proto = MobIndex(vnum=8002, short_descr="a sacred guardian")
    sacred = Character(name="Sacred", is_npc=True)
    sacred.prototype = sacred_proto
    sacred.act = int(ActFlag.NOPURGE)
    room.add_character(sacred)
    character_registry.append(sacred)

    pc = Character(name="Hero", is_npc=False)
    room.add_character(pc)
    character_registry.append(pc)

    junk_obj = Object(instance_id=None, prototype=ObjIndex(vnum=8100, short_descr="junk", name="junk"))
    room.add_object(junk_obj)

    keepsake_proto = ObjIndex(vnum=8101, short_descr="keepsake", name="keepsake")
    keepsake = Object(instance_id=None, prototype=keepsake_proto)
    keepsake.extra_flags = int(ITEM_NOPURGE)
    room.add_object(keepsake)

    mob_cmds.mob_interpret(controller, "purge")

    # PCs and the running mob remain.
    assert controller in room.people
    assert pc in room.people
    # ACT_NOPURGE NPC remains; ordinary NPCs are extracted.
    assert sacred in room.people
    assert grunt not in room.people
    # ITEM_NOPURGE object remains; ordinary objects are extracted.
    assert keepsake in room.contents
    assert junk_obj not in room.contents


def test_mppurge_specific_target_refuses_pc_and_self(monkeypatch):
    _, room, _ = _setup_area()

    controller = Character(name="Controller", is_npc=True)
    room.add_character(controller)
    character_registry.append(controller)

    pc = Character(name="Hero", is_npc=False)
    room.add_character(pc)
    character_registry.append(pc)

    mob_cmds.mob_interpret(controller, "purge Hero")
    assert pc in room.people  # ROM never purges PCs

    mob_cmds.mob_interpret(controller, "purge Controller")
    assert controller in room.people  # never purge the running mob


# ---------------------------------------------------------------------------
# Variable substitution -- exercise >= 6 distinct codes in one snippet.
# ---------------------------------------------------------------------------


def test_expand_arg_covers_six_plus_distinct_variables(monkeypatch):
    """Drive a mobprog whose echo references $i $I $n $N $t $T $e $m $s $p $P."""
    _, room, _ = _setup_area()

    mob_proto = MobIndex(vnum=9500, short_descr="the riddler")
    mob = Character(name="riddler herald", is_npc=True)
    mob.prototype = mob_proto
    mob.short_descr = "the riddler"
    mob.sex = 1
    room.add_character(mob)
    character_registry.append(mob)

    actor = Character(name="Bilbo", is_npc=False)
    actor.short_descr = "Bilbo of the Shire"
    actor.sex = 1
    room.add_character(actor)
    character_registry.append(actor)

    target = Character(name="Frodo", is_npc=False)
    target.short_descr = "Frodo Baggins"
    target.sex = 1
    room.add_character(target)
    character_registry.append(target)

    obj_a = Object(
        instance_id=None,
        prototype=ObjIndex(vnum=9600, short_descr="a glowing ring", name="ring shiny"),
    )
    obj_b = Object(
        instance_id=None,
        prototype=ObjIndex(vnum=9601, short_descr="a stout staff", name="staff oak"),
    )
    obj_a.short_descr = "a glowing ring"
    obj_b.short_descr = "a stout staff"

    template = "$i|$I|$n|$N|$t|$T|$e|$m|$s|$p|$P"
    expanded = mobprog._expand_arg(template, mob, actor, obj_a, target, None)

    parts = expanded.split("|")
    assert len(parts) == 11
    i_tok, big_i, n_tok, big_n, t_tok, big_t, e_tok, m_tok, s_tok, p_tok, big_p = parts

    # $i = first word of mob name
    assert i_tok == "riddler"
    # $I = mob short_descr
    assert big_i == "the riddler"
    # $n = first word of actor name, capitalised
    assert n_tok == "Bilbo"
    # $N = actor short_descr (PCs use short_descr if set, else name)
    assert big_n in {"Bilbo of the Shire", "Bilbo"}
    # $t / $T = vch (target) name
    assert t_tok == "Frodo"
    assert big_t in {"Frodo Baggins", "Frodo"}
    # $e/$m/$s = pronouns derived from actor sex (male)
    assert e_tok == "he"
    assert m_tok == "him"
    assert s_tok == "his"
    # When arg2 is a Character (vch), $p/$P fall back to "something"
    # because Object-typed lookups treat non-objects as missing.
    # Re-run with the object in arg2 to verify $p/$P emit object names.
    expanded_obj = mobprog._expand_arg("$p|$P", mob, actor, obj_a, obj_b, None)
    p_word, big_p_word = expanded_obj.split("|")
    assert p_word == "staff"  # first word of obj2.name
    assert big_p_word == "a stout staff"  # obj2.short_descr
