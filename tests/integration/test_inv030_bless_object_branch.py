"""
INV-030: BLESS-OBJECT-BRANCH

Cross-file contract: ROM spell_bless (src/magic.c:788-834) has a TARGET_OBJ
branch that (a) checks ITEM_BLESS (already-blessed), (b) tries to dispel
ITEM_EVIL (removing the curse affect and Evil flag via affect_remove_obj +
REMOVE_BIT), (c) on a clean object, adds an affect with TO_OBJECT /
APPLY_SAVES / modifier -1 / ITEM_BLESS bitvector via affect_to_obj, and
(d) if the blessed object is worn, gives the carrier saving_throw -= 1.

The Python bless() handler previously only had the character branch
(src/magic.c:836-865). The TARGET_OBJ branch is now implemented, matching
ROM src/magic.c:788-834.

Enforced tests:
  1. Bless on a clean object adds ITEM_BLESS affect and holy aura message.
  2. Bless on an already-blessed object is rejected.
  3. Bless on an evil object: dispel success removes Evil + curse affect.
  4. Bless on an evil object: dispel failure leaves Evil intact.
  5. Bless on an evil object: curse affect is removed on dispel success.
  6. Bless on a worn object: carrier gets saving_throw -= 1.
  7. do_cast routes object targets to bless() for defensive_character_or_object.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from mud.models.character import Character, character_registry
from mud.models.constants import (
    ExtraFlag,
    ItemType,
    Position,
    WearFlag,
    WearLocation,
)
from mud.models.obj import Affect, ObjIndex, object_registry
from mud.models.object import Object
from mud.models.room import Room
from mud.skills.handlers import bless
from mud.skills.registry import load_skills, skill_registry

_TO_OBJECT = 1
_APPLY_SAVES = 20
_APPLY_NONE = 0


@pytest.fixture(autouse=True)
def _load_skills_and_cleanup():
    skill_registry.skills.clear()
    skill_registry.handlers.clear()
    load_skills(Path("data/skills.json"))
    yield
    skill_registry.skills.clear()
    skill_registry.handlers.clear()


def _make_room():
    return Room(vnum=30000, name="Test Room")


def _make_caster(level: int = 10):
    room = _make_room()
    char = Character(name="caster", level=level, position=Position.STANDING)
    char.room = room
    char.mana = 999
    character_registry.append(char)
    return char


def _make_object(name: str = "sword", item_type: int = int(ItemType.WEAPON), **kw):
    proto = ObjIndex(
        vnum=kw.pop("vnum", 99001),
        name=name,
        short_descr=f"a {name}",
        level=kw.pop("level", 1),
        item_type=item_type,
        extra_flags=kw.pop("extra_flags", 0),
        wear_flags=kw.pop("wear_flags", int(WearFlag.TAKE)),
    )
    obj = Object(instance_id=None, prototype=proto)
    # Synchronize value from prototype
    obj.value = list(proto.value) if hasattr(proto, "value") and proto.value else [0, 0, 0, 0, 0]
    # Apply overrides
    for k, v in kw.items():
        setattr(obj, k, v)
    object_registry.append(obj)
    return obj


def _cleanup(char):
    if char in character_registry:
        character_registry.remove(char)


def _cleanup_obj(obj):
    if obj in object_registry:
        object_registry.remove(obj)


class TestBlessObjectBranch:
    """INV-030: bless on objects mirrors ROM src/magic.c:788-834."""

    def test_bless_clean_object_adds_bless_affect_and_message(self):
        # ROM :820-829 — clean object gets affect + holy aura message
        caster = _make_caster(level=10)
        obj = _make_object("longsword", extra_flags=0)
        try:
            result = bless(caster, obj)

            assert result is True, "bless on clean object should succeed"
            # Object should have ITEM_BLESS in extra_flags
            assert obj.extra_flags & int(ExtraFlag.BLESS), "bless should set ITEM_BLESS"

            # Object should have a bless affect with ITEM_BLESS bitvector
            bless_affects = [
                a
                for a in obj.affected
                if hasattr(a, "bitvector") and a.bitvector == int(ExtraFlag.BLESS)
            ]
            assert len(bless_affects) == 1, "bless should add one ITEM_BLESS affect"
            aff = bless_affects[0]
            assert aff.where == _TO_OBJECT
            assert aff.location == _APPLY_SAVES
            assert aff.modifier == -1
            assert aff.duration == 6 + 10  # ROM :823 — 6 + level
        finally:
            _cleanup(caster)
            _cleanup_obj(obj)

    def test_bless_already_blessed_object_rejected(self):
        # ROM :792-795 — ITEM_BLESS check
        caster = _make_caster(level=10)
        obj = _make_object("longsword", extra_flags=int(ExtraFlag.BLESS))
        try:
            result = bless(caster, obj)
            assert result is False, "bless on already-blessed object should fail"
        finally:
            _cleanup(caster)
            _cleanup_obj(obj)

    def test_bless_evil_object_dispel_success(self):
        # ROM :798-817 — ITEM_EVIL branch: dispel succeeds → remove evil
        caster = _make_caster(level=50)
        obj = _make_object("cursed sword", level=1, extra_flags=int(ExtraFlag.EVIL))
        try:
            result = bless(caster, obj)
            assert result is True, "bless on low-level evil object should succeed via dispel"
            # Evil flag should be removed
            assert not (obj.extra_flags & int(ExtraFlag.EVIL)), "dispel should remove ITEM_EVIL"
            # Bless flag should NOT be set (dispel path, not bless path)
            assert not (obj.extra_flags & int(ExtraFlag.BLESS)), "dispel path does not add ITEM_BLESS"
        finally:
            _cleanup(caster)
            _cleanup_obj(obj)

    def test_bless_evil_object_dispel_failure(self):
        # ROM :812-817 — ITEM_EVIL branch: dispel fails (high obj level)
        caster = _make_caster(level=1)
        obj = _make_object("ancient evil sword", level=100, extra_flags=int(ExtraFlag.EVIL))
        try:
            from mud.affects import saves as saves_mod

            with patch.object(saves_mod, "saves_dispel", return_value=True):
                result = bless(caster, obj)

            assert result is False, "bless should fail when dispel on evil object fails"
            # Evil flag should remain
            assert obj.extra_flags & int(ExtraFlag.EVIL), "ITEM_EVIL should remain after failed dispel"
        finally:
            _cleanup(caster)
            _cleanup_obj(obj)

    def test_bless_evil_object_removes_curse_affect_on_success(self):
        # ROM :806-807 — affect_remove_obj removes the curse affect on dispel
        # Also ROM :809 — REMOVE_BIT(obj->extra_flags, ITEM_EVIL)
        caster = _make_caster(level=50)
        obj = _make_object("cursed sword", level=1, extra_flags=int(ExtraFlag.EVIL))
        # Add a curse affect to the object
        curse_affect = Affect(
            where=_TO_OBJECT,
            type=0,
            level=1,
            duration=-1,
            location=_APPLY_NONE,
            modifier=0,
            bitvector=int(ExtraFlag.EVIL),
        )
        curse_affect.spell_name = "curse"
        obj.affected = [curse_affect]
        try:
            result = bless(caster, obj)
            assert result is True
            # Curse affect should be removed
            curse_affects = [
                a for a in obj.affected if hasattr(a, "spell_name") and a.spell_name == "curse"
            ]
            assert len(curse_affects) == 0, "dispel success should remove the curse affect"
        finally:
            _cleanup(caster)
            _cleanup_obj(obj)

    def test_bless_worn_object_applies_saving_throw_to_carrier(self):
        # ROM :831-832 — if obj->wear_loc != WEAR_NONE, ch->saving_throw -= 1
        caster = _make_caster(level=10)
        obj = _make_object("amulet", item_type=int(ItemType.ARMOR))
        obj.wear_flags = int(WearFlag.TAKE | WearFlag.WEAR_NECK)
        obj.wear_loc = int(WearLocation.NECK_1)
        obj.carried_by = caster
        caster.equipment[int(WearLocation.NECK_1)] = obj

        base_saving_throw = getattr(caster, "saving_throw", 0) or 0
        try:
            result = bless(caster, obj)
            assert result is True, "bless on worn object should succeed"

            # The saving_throw should be decremented by 1
            # (APPLY_SAVES modifier -1, ROM :831-832)
            assert (
                getattr(caster, "saving_throw", 0) == base_saving_throw - 1
            ), f"worn bless should give saving_throw -= 1, got {getattr(caster, 'saving_throw', 0)} vs {base_saving_throw - 1}"
        finally:
            _cleanup(caster)
            _cleanup_obj(obj)


class TestDoCastBlessObjectRouting:
    """Verify do_cast routes object targets to bless() for defensive_character_or_object spells."""

    def test_cast_bless_on_carried_object(self):
        from mud.commands.combat import do_cast

        caster = _make_caster(level=20)
        caster.skills = {"bless": 100}
        caster.ch_class = 1  # cleric — bless required at level 7
        obj = _make_object("robe", item_type=int(ItemType.ARMOR))
        obj.wear_flags = int(WearFlag.TAKE)
        caster.inventory.append(obj)
        obj.carried_by = caster

        try:
            # Mock RNG so concentration always succeeds
            with patch("mud.utils.rng_mm.number_percent", return_value=0):
                result = do_cast(caster, "'bless' robe")

            # Should not crash; bless on a clean object should set ITEM_BLESS
            assert obj.extra_flags & int(ExtraFlag.BLESS), f"cast bless on object should set ITEM_BLESS, got result={result!r} extra_flags={obj.extra_flags}"
        finally:
            _cleanup(caster)
            _cleanup_obj(obj)
