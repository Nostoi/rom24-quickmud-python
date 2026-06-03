"""Integration tests for do_cast object-targeting legs.

ROM parity references:
- src/magic.c:449-465 — TAR_OBJ_INV (object-only spells)
- src/magic.c:466-512 — TAR_OBJ_CHAR_OFF (offensive char/object spells)
- src/magic.c:514-535 — TAR_OBJ_CHAR_DEF (defensive char/object spells)

Covers CAST-004 (TAR_OBJ_INV), CAST-005 (TAR_OBJ_CHAR_OFF object fallback),
CAST-006 (TAR_OBJ_CHAR_DEF object fallback).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mud.commands.combat import do_cast
from mud.models.character import Character
from mud.models.constants import ItemType
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.skills.registry import load_skills, skill_registry


@pytest.fixture(autouse=True)
def _load_skills():
    skill_registry.skills.clear()
    skill_registry.handlers.clear()
    load_skills(Path("data/skills.json"))
    yield
    skill_registry.skills.clear()
    skill_registry.handlers.clear()


def _make_caster(**overrides) -> Character:
    defaults = {
        "name": "Merlin",
        "level": 30,
        "ch_class": 0,
        "is_npc": False,
        "perm_stat": [0, 18, 0, 0, 0],
        "mana": 500,
        "position": 8,
        "wait": 0,
        "skills": {"identify": 100},
    }
    defaults.update(overrides)
    return Character(**defaults)


def _make_object(name: str = "scroll", vnum: int = 99001, **overrides) -> Object:
    proto_kwargs = {
        "vnum": vnum,
        "name": name,
        "short_descr": name,
        "item_type": int(ItemType.SCROLL),
        "value": [25, 0, 0, 0, 0],
    }
    proto_kwargs.update(overrides)
    proto = ObjIndex(**proto_kwargs)
    obj = Object(instance_id=None, prototype=proto)
    obj.value = list(proto.value)
    return obj


# ---------------------------------------------------------------------------
# CAST-004: TAR_OBJ_INV (object-only spells)
# ---------------------------------------------------------------------------


class TestCastObjectTarget:
    """ROM src/magic.c:449-465 — TAR_OBJ_INV requires a named object target
    found in the caster's inventory via get_obj_carry."""

    def test_object_spell_no_arg_errors(self):
        caster = _make_caster(skills={"identify": 100})
        result = do_cast(caster, "identify")
        assert result == "What should the spell be cast upon?", result

    def test_object_spell_not_carried_errors(self):
        caster = _make_caster(skills={"identify": 100})
        result = do_cast(caster, "identify backpack")
        assert result == "You are not carrying that.", result

    def test_object_spell_carried_object_resolves(self):
        from mud.utils import rng_mm

        room = Room(vnum=99100, name="Lab", description="Test room")
        caster = _make_caster(skills={"identify": 100})
        caster.room = room
        room.people.append(caster)
        obj = _make_object(name="potion vial", vnum=99200)
        caster.inventory.append(obj)

        rng_mm.seed_mm(42)
        result = do_cast(caster, "'identify' 'potion vial'")

        assert result == "", f"successful cast should be silent, got: {result}"
        assert caster.mana < 500, "mana should be consumed"


# ---------------------------------------------------------------------------
# CAST-005: TAR_OBJ_CHAR_OFF (offensive char/object fallback)
# ---------------------------------------------------------------------------


class TestCastOffensiveObjectFallback:
    """ROM src/magic.c:466-512 — TAR_OBJ_CHAR_OFF first tries get_char_room,
    then falls back to get_obj_here when no character matches."""

    def test_offensive_char_spell_char_target_still_works(self):
        from mud.utils import rng_mm

        room = Room(vnum=99200, name="Arena", description="Test arena")
        caster = _make_caster(skills={"curse": 100}, ch_class=1)
        caster.room = room
        room.people.append(caster)
        victim = Character(
            name="Fido",
            level=10,
            ch_class=0,
            is_npc=True,
            hit=200,
            max_hit=200,
        )
        victim.room = room
        room.people.append(victim)

        rng_mm.seed_mm(42)
        result = do_cast(caster, "curse Fido")
        assert result == "", f"successful cast should be silent, got: {result}"

    def test_offensive_char_spell_no_room_match_falls_back_to_object(self):
        room = Room(vnum=99300, name="Lab", description="Test room")
        caster = _make_caster(skills={"curse": 100}, ch_class=1)
        caster.room = room
        room.people.append(caster)
        obj = _make_object(name="cursed amulet", vnum=99301)
        obj.item_type = int(ItemType.ARMOR)
        caster.inventory.append(obj)

        result = do_cast(caster, "curse amulet")
        assert result != "They aren't here.", "offensive spell must fall back to object search before erroring"
        assert result != "You don't see that here.", "object should be found via get_obj_here fallback"

    def test_offensive_char_spell_no_char_no_object_errors(self):
        room = Room(vnum=99400, name="Empty", description="Empty room")
        caster = _make_caster(skills={"curse": 100}, ch_class=1, mana=200)
        caster.room = room
        room.people.append(caster)

        result = do_cast(caster, "curse nobody")
        assert result == "You don't see that here.", result


# ---------------------------------------------------------------------------
# CAST-006: TAR_OBJ_CHAR_DEF (defensive char/object fallback)
# ---------------------------------------------------------------------------


class TestCastDefensiveObjectFallback:
    """ROM src/magic.c:514-535 — TAR_OBJ_CHAR_DEF first tries get_char_room,
    then falls back to get_obj_carry when no character matches."""

    def test_defensive_char_spell_no_arg_self_casts(self):
        from mud.utils import rng_mm

        room = Room(vnum=99500, name="Chapel", description="Test chapel")
        caster = _make_caster(skills={"bless": 100}, ch_class=1)
        caster.messages = []
        caster.room = room
        room.people.append(caster)

        rng_mm.seed_mm(42)
        result = do_cast(caster, "bless")

        assert result == "", result
        assert caster.has_spell_effect("bless")

    def test_defensive_char_spell_char_target_still_works(self):
        from mud.utils import rng_mm

        room = Room(vnum=99501, name="Chapel", description="Test chapel")
        caster = _make_caster(skills={"bless": 100}, ch_class=1)
        caster.messages = []
        caster.room = room
        room.people.append(caster)
        target = Character(
            name="Paladin",
            level=20,
            ch_class=1,
            is_npc=False,
            hit=200,
            max_hit=200,
        )
        target.room = room
        room.people.append(target)

        rng_mm.seed_mm(42)
        result = do_cast(caster, "bless Paladin")
        assert result == ""

    def test_defensive_char_spell_no_char_match_falls_back_to_object(self):
        room = Room(vnum=99600, name="Lab", description="Test room")
        caster = _make_caster(skills={"bless": 100}, ch_class=1)
        caster.messages = []
        caster.room = room
        room.people.append(caster)
        obj = _make_object(name="holy sword", vnum=99601)
        obj.item_type = int(ItemType.WEAPON)
        caster.inventory.append(obj)

        result = do_cast(caster, "bless 'holy sword'")

        assert result != "They aren't here.", "defensive spell must fall back to object search before erroring"
        assert result != "You don't see that here.", "object should be found via get_obj_carry fallback"

    def test_defensive_char_spell_no_char_no_object_errors(self):
        room = Room(vnum=99700, name="Empty", description="Empty room")
        caster = _make_caster(skills={"bless": 100}, ch_class=1, mana=200)
        caster.room = room
        room.people.append(caster)

        result = do_cast(caster, "bless nobody_here")
        assert result == "You don't see that here.", result
