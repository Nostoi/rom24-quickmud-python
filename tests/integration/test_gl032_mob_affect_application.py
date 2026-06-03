"""GL-032 — ``MobInstance.apply_spell_effect`` must apply every affect location.

ROM's ``affect_modify`` (``src/handler.c:1018-1164``) is the *same* function for
PCs and NPCs: it applies every ``APPLY_*`` location uniformly (AC, saves, stats,
sex, hitroll, damroll, affect flags). A charmed pet (an NPC) buffed with armor
(``APPLY_AC``), giant strength (``APPLY_STR``), a save-modifying spell
(``APPLY_SAVES``), or a sex-changing spell (``APPLY_SEX``) therefore DOES get the
corresponding benefit in ROM.

The Python port's ``MobInstance.apply_spell_effect``
(``mud/spawning/templates.py``) was a "simplified" applier that only moved
``hitroll``/``damroll`` and set the affect flag — it silently ignored
``ac_mod``, ``saving_throw_mod``, ``stat_modifiers``, and ``sex_delta``. So a
charmed pet gained nothing from armor/giant-strength/save buffs.
``Character.apply_spell_effect`` applies all of them; ``MobInstance``'s must too.

This test asserts the **live observable** effect (armor lowered, effective STR
raised, saving_throw lowered, sex changed), that ``remove_spell_effect`` unwinds
each exactly, and that a save/reload round-trip preserves the bonus counted once
(folded-in runtime fields + GL-031 data-only spell_effect restore).
"""

from __future__ import annotations

from mud.account.account_manager import _dataclass_to_dict
from mud.db.serializers import _deserialize_pet, _serialize_pet
from mud.models.character import SpellEffect
from mud.models.constants import Stat
from mud.spawning.mob_spawner import spawn_mob
from mud.world import create_test_character, initialize_world


def _make_pet_and_owner():
    initialize_world("area/area.lst")
    owner = create_test_character("PetOwner", 3001)
    pet = spawn_mob(3000)
    assert pet is not None
    pet.move_to_room(owner.room)
    pet.master = owner
    pet.leader = owner
    return pet, owner


def test_mob_apply_spell_effect_applies_ac_saves_stat_sex():
    pet, _owner = _make_pet_and_owner()

    base_armor = list(pet.armor)
    base_str = pet.get_curr_stat(Stat.STR)
    base_save = pet.saving_throw
    base_sex = int(pet.sex)

    # armor: APPLY_AC lowers all four armor classes (ROM handler.c:1113-1116).
    pet.apply_spell_effect(SpellEffect(name="armor", duration=24, level=10, ac_mod=-20))
    assert list(pet.armor) == [ac - 20 for ac in base_armor]

    # giant strength: APPLY_STR raises effective STR (ROM handler.c:1072-1074),
    # which the mob reads through get_curr_stat (perm_stat + mod_stat).
    pet.apply_spell_effect(SpellEffect(name="giant strength", duration=10, level=15, stat_modifiers={Stat.STR: 2}))
    assert pet.get_curr_stat(Stat.STR) == base_str + 2

    # a save-modifying buff: APPLY_SAVES adjusts saving_throw (ROM handler.c:1123-1124).
    pet.apply_spell_effect(SpellEffect(name="protection", duration=8, level=10, saving_throw_mod=-5))
    assert pet.saving_throw == base_save - 5

    # change sex: APPLY_SEX adjusts sex (ROM handler.c:1087-1088).
    pet.apply_spell_effect(SpellEffect(name="change sex", duration=12, level=8, sex_delta=1))
    assert int(pet.sex) == base_sex + 1


def test_mob_remove_spell_effect_unwinds_ac_saves_stat_sex():
    pet, _owner = _make_pet_and_owner()

    base_armor = list(pet.armor)
    base_str = pet.get_curr_stat(Stat.STR)
    base_save = pet.saving_throw
    base_sex = int(pet.sex)

    pet.apply_spell_effect(SpellEffect(name="armor", duration=24, level=10, ac_mod=-20))
    pet.apply_spell_effect(SpellEffect(name="giant strength", duration=10, level=15, stat_modifiers={Stat.STR: 2}))
    pet.apply_spell_effect(SpellEffect(name="protection", duration=8, level=10, saving_throw_mod=-5))
    pet.apply_spell_effect(SpellEffect(name="change sex", duration=12, level=8, sex_delta=1))

    pet.remove_spell_effect("armor")
    pet.remove_spell_effect("giant strength")
    pet.remove_spell_effect("protection")
    pet.remove_spell_effect("change sex")

    assert list(pet.armor) == base_armor
    assert pet.get_curr_stat(Stat.STR) == base_str
    assert pet.saving_throw == base_save
    assert int(pet.sex) == base_sex


def test_mob_affect_bonuses_round_trip_counted_once():
    pet, owner = _make_pet_and_owner()

    pet.apply_spell_effect(SpellEffect(name="armor", duration=24, level=10, ac_mod=-20))
    pet.apply_spell_effect(SpellEffect(name="giant strength", duration=10, level=15, stat_modifiers={Stat.STR: 2}))
    pet.apply_spell_effect(SpellEffect(name="protection", duration=8, level=10, saving_throw_mod=-5))
    pet.apply_spell_effect(SpellEffect(name="change sex", duration=12, level=8, sex_delta=1))

    # Live (folded-in) values at save time.
    saved_armor = list(pet.armor)
    saved_str = pet.get_curr_stat(Stat.STR)
    saved_save = pet.saving_throw
    saved_sex = int(pet.sex)

    snapshot = _serialize_pet(pet)
    assert snapshot is not None
    restored = _deserialize_pet(_dataclass_to_dict(snapshot), owner)
    assert restored is not None

    # ROM fread_pet restores data-only (saved ACs/AMod/sex already fold in the
    # bonus), so the reloaded pet matches the live values exactly — counted once,
    # no drift (sex round-trips as an int through PetSave.sex).
    assert list(restored.armor) == saved_armor
    assert restored.get_curr_stat(Stat.STR) == saved_str
    assert restored.saving_throw == saved_save
    assert int(restored.sex) == saved_sex
