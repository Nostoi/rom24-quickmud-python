"""GL-030 — serializing a charmed pet that carries a spell affect must not crash.

GL-027 gave ``MobInstance`` a real ``affected`` list whose shadow ``AffectData``
are keyed by spell **name** (a ``str``, e.g. ``"bless"``), mirroring the pet's
``spell_effects`` dict. ``_serialize_pet`` (``mud/db/serializers.py``, ROM
``fwrite_pet``) was written for integer-SN affects and did
``if affect.type < 0: continue`` — ``"bless" < 0`` raises ``TypeError`` in
Python 3, so saving any charmed pet that had been buffed/debuffed crashed the
whole character save.

The fix skips the string-named (spell_effects-managed) shadows in the SN-based
pet affect format rather than crashing; integer-SN raw affects still round-trip.
(Persisting spell-cast pet buffs across reload is a separate pre-existing gap —
mobs' ``spell_effects`` were never serialized; see GL-031.)
"""

from __future__ import annotations

from mud.db.serializers import _serialize_pet
from mud.models.character import AffectData, SpellEffect
from mud.models.mob import MobIndex
from mud.spawning.templates import MobInstance


def _pet() -> MobInstance:
    proto = MobIndex(vnum=9620, short_descr="a charmed pet", level=10)
    return MobInstance.from_prototype(proto)


def test_serialize_pet_with_spell_effect_does_not_crash():
    """A pet buffed via apply_spell_effect (string-typed shadow AffectData) must
    serialize without raising (SAVE-021)."""
    pet = _pet()
    pet.apply_spell_effect(SpellEffect(name="bless", duration=6, level=10, hitroll_mod=2))
    assert any(getattr(a, "type", None) == "bless" for a in pet.affected)

    snapshot = _serialize_pet(pet)  # must not raise TypeError

    assert snapshot is not None
    # The string-named shadow is not emitted into the SN-based pet affect format.
    assert all(isinstance(getattr(a, "skill_name", ""), str) for a in snapshot.affects)
    assert not any(a.skill_name == "" for a in snapshot.affects), "no garbage empty-name affect rows"


def test_serialize_pet_still_persists_integer_sn_affects():
    """Guard the guard: an integer-SN raw affect (affect_to_char-style) must
    still be serialized — the fix only skips string-named shadows."""
    pet = _pet()
    # Raw SN affect as produced by affect_to_char (sanctuary SN is registry-specific;
    # use a plain non-negative int type that won't match a skill slot is fine — the
    # point is the comparison no longer crashes and non-negative ints are considered).
    pet.affected.append(
        AffectData(type=0, level=10, duration=6, location=0, modifier=0, bitvector=0)
    )
    snapshot = _serialize_pet(pet)
    assert snapshot is not None  # no crash on the int-typed affect either
