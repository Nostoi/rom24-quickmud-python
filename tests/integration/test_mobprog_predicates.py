"""Integration tests for mob_prog.c cmd_eval predicates (MOB_PROG_C_AUDIT.md gaps).

Covers world-scoped predicates and other ``_cmd_eval`` divergences from
ROM ``src/mob_prog.c``.
"""

from __future__ import annotations

import pytest

from mud import mobprog
from mud.models.character import Character, character_registry
from mud.models.obj import ObjIndex, object_registry
from mud.models.object import Object
from mud.models.room import Room
from mud.registry import obj_registry, room_registry


@pytest.fixture(autouse=True)
def _clear_registries():
    room_registry.clear()
    obj_registry.clear()
    character_registry.clear()
    object_registry.clear()
    yield
    room_registry.clear()
    obj_registry.clear()
    character_registry.clear()
    object_registry.clear()


def _make_obj(vnum: int, name: str, short_descr: str) -> Object:
    proto = ObjIndex(vnum=vnum, name=name, short_descr=short_descr)
    obj_registry[vnum] = proto
    obj = Object(instance_id=None, prototype=proto)
    object_registry.append(obj)
    return obj


def test_objexists_finds_object_in_remote_room_by_name():
    """mirrors ROM src/mob_prog.c:399 — objexists must walk the world."""
    here = Room(vnum=4000, name="Mob Room")
    elsewhere = Room(vnum=4100, name="Vault")
    room_registry[4000] = here
    room_registry[4100] = elsewhere

    mob = Character(name="oracle", is_npc=True)
    here.add_character(mob)
    character_registry.append(mob)

    artifact = _make_obj(9999, "rare artifact relic", "a rare artifact")
    elsewhere.contents.append(artifact)
    artifact.location = elsewhere

    assert mobprog._cmd_eval("objexists", "artifact", mob, None, None, None, None) is True


def test_objexists_finds_object_in_remote_room_by_vnum():
    """mirrors ROM src/mob_prog.c:399 — objexists vnum branch must walk the world."""
    here = Room(vnum=4000, name="Mob Room")
    elsewhere = Room(vnum=4100, name="Vault")
    room_registry[4000] = here
    room_registry[4100] = elsewhere

    mob = Character(name="oracle", is_npc=True)
    here.add_character(mob)
    character_registry.append(mob)

    artifact = _make_obj(9999, "amulet glowing", "a glowing amulet")
    elsewhere.contents.append(artifact)
    artifact.location = elsewhere

    assert mobprog._cmd_eval("objexists", "9999", mob, None, None, None, None) is True


def test_objexists_returns_false_when_object_not_in_world():
    """No matching object anywhere in object_registry → False."""
    here = Room(vnum=4000, name="Mob Room")
    room_registry[4000] = here

    mob = Character(name="oracle", is_npc=True)
    here.add_character(mob)
    character_registry.append(mob)

    # Unrelated object so registry isn't empty.
    _make_obj(123, "stick", "a stick")

    assert mobprog._cmd_eval("objexists", "phoenix", mob, None, None, None, None) is False
    assert mobprog._cmd_eval("objexists", "9999", mob, None, None, None, None) is False


def test_vnum_compare_against_pc_uses_zero_lval():
    """mirrors ROM src/mob_prog.c:631-648 — for PCs, lval stays 0; comparison still runs."""
    here = Room(vnum=4000, name="Hall")
    room_registry[4000] = here

    mob = Character(name="oracle", is_npc=True)
    here.add_character(mob)
    character_registry.append(mob)

    pc = Character(name="hero", is_npc=False)
    here.add_character(pc)
    character_registry.append(pc)

    # PC → lval = 0 → "$n vnum == 0" is True, "!= 0" is False, "> 0" is False.
    assert mobprog._cmd_eval("vnum", "$n == 0", mob, pc, None, None, None) is True
    assert mobprog._cmd_eval("vnum", "$n != 0", mob, pc, None, None, None) is False
    assert mobprog._cmd_eval("vnum", "$n > 0", mob, pc, None, None, None) is False


def test_vnum_compare_against_npc_uses_proto_vnum():
    """mirrors ROM src/mob_prog.c:640-642 — NPC vnum comes from pIndexData."""
    from mud.models.mob import MobIndex

    here = Room(vnum=4001, name="Hall")
    room_registry[4001] = here

    mob = Character(name="oracle", is_npc=True)
    here.add_character(mob)
    character_registry.append(mob)

    other_npc = Character(name="goblin", is_npc=True)
    other_npc.prototype = MobIndex(vnum=3500, short_descr="a goblin")
    here.add_character(other_npc)
    character_registry.append(other_npc)

    assert mobprog._cmd_eval("vnum", "$n == 3500", mob, other_npc, None, None, None) is True
    assert mobprog._cmd_eval("vnum", "$n == 0", mob, other_npc, None, None, None) is False


def test_class_lookup_resolves_named_keyword():
    """mirrors ROM src/mob_prog.c:607-609 — class_lookup converts name to int index."""
    from mud.models.classes import CLASS_TABLE

    mage_idx = next(i for i, c in enumerate(CLASS_TABLE) if c.name == "mage")

    here = Room(vnum=4002, name="Hall")
    room_registry[4002] = here

    mob = Character(name="oracle", is_npc=True)
    here.add_character(mob)
    character_registry.append(mob)

    pc = Character(name="hero", is_npc=False)
    pc.ch_class = mage_idx
    here.add_character(pc)
    character_registry.append(pc)

    assert mobprog._cmd_eval("class", "$n mage", mob, pc, None, None, None) is True
    assert mobprog._cmd_eval("class", "$n cleric", mob, pc, None, None, None) is False
    # ROM prefix match: "mag" should also resolve to mage.
    assert mobprog._cmd_eval("class", "$n mag", mob, pc, None, None, None) is True


def test_race_lookup_resolves_named_keyword():
    """mirrors ROM src/mob_prog.c:604-606 — race_lookup converts name to int index."""
    from mud.models.races import RACE_TABLE

    dwarf_idx = next((i for i, r in enumerate(RACE_TABLE) if r.name == "dwarf"), None)
    assert dwarf_idx is not None

    here = Room(vnum=4003, name="Hall")
    room_registry[4003] = here

    mob = Character(name="oracle", is_npc=True)
    here.add_character(mob)
    character_registry.append(mob)

    npc = Character(name="thane", is_npc=True)
    npc.race = dwarf_idx
    here.add_character(npc)
    character_registry.append(npc)

    assert mobprog._cmd_eval("race", "$n dwarf", mob, npc, None, None, None) is True
    assert mobprog._cmd_eval("race", "$n elf", mob, npc, None, None, None) is False


def test_clan_lookup_resolves_named_keyword():
    """mirrors ROM src/mob_prog.c:601-603 — clan_lookup converts name to int index."""
    from mud.models.clans import CLAN_TABLE

    if len(CLAN_TABLE) < 2:
        pytest.skip("CLAN_TABLE has no named clan entries")
    target_idx = 1
    target_name = CLAN_TABLE[target_idx].name

    here = Room(vnum=4004, name="Hall")
    room_registry[4004] = here

    mob = Character(name="oracle", is_npc=True)
    here.add_character(mob)
    character_registry.append(mob)

    pc = Character(name="hero", is_npc=False)
    pc.clan = target_idx
    here.add_character(pc)
    character_registry.append(pc)

    assert mobprog._cmd_eval("clan", f"$n {target_name}", mob, pc, None, None, None) is True


def test_dollar_R_uses_ch_name_replicate_rom_bug():
    """ROM src/mob_prog.c:798-799 — `$R` substitutes ``ch`` (the original
    actor), NOT ``rch`` (the random victim). This is a long-standing ROM bug
    that QuickMUD must replicate per AGENTS.md ROM Parity Rules.
    """
    here = Room(vnum=4005, name="Hall")
    room_registry[4005] = here

    mob = Character(name="oracle", is_npc=True)
    here.add_character(mob)
    character_registry.append(mob)

    pc = Character(name="hero", is_npc=False)
    here.add_character(pc)
    character_registry.append(pc)

    rch_npc = Character(name="goblin", is_npc=True)
    rch_npc.short_descr = "a sly goblin"
    here.add_character(rch_npc)
    character_registry.append(rch_npc)

    expanded = mobprog._expand_arg("$R waves", mob, pc, None, None, rch_npc)
    # ROM bug: substitutes ch (PC) → "hero", not the goblin short_descr.
    assert "hero" in expanded.lower()
    assert "goblin" not in expanded.lower()


def test_dollar_R_uses_ch_short_descr_when_actor_is_npc():
    """ROM src/mob_prog.c:798-799 — when ``ch`` is an NPC, `$R` uses
    ``ch->short_descr``."""
    here = Room(vnum=4006, name="Hall")
    room_registry[4006] = here

    mob = Character(name="oracle", is_npc=True)
    here.add_character(mob)
    character_registry.append(mob)

    npc_actor = Character(name="raider", is_npc=True)
    npc_actor.short_descr = "a savage raider"
    here.add_character(npc_actor)
    character_registry.append(npc_actor)

    rch_npc = Character(name="goblin", is_npc=True)
    rch_npc.short_descr = "a sly goblin"
    here.add_character(rch_npc)
    character_registry.append(rch_npc)

    expanded = mobprog._expand_arg("$R approaches", mob, npc_actor, None, None, rch_npc)
    assert "savage raider" in expanded
    assert "goblin" not in expanded
