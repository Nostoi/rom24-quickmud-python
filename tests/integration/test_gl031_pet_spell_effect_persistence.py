"""GL-031 — a charmed pet's spell-cast buffs must survive save/reload.

ROM ``fwrite_pet`` (``src/save.c:508-517``) writes every entry on
``pet->affected`` by skill name; ``fread_pet`` (``src/save.c:1544-1573``) links
them straight back onto ``pet->affected`` **without** calling
``affect_modify`` — the saved ``ACs``/``Hit``/``AMod`` lines already include the
affect bonuses, so the affect is restored as *data only* (for duration ticking
and wear-off), never re-applied on top of the already-modified stats.

The Python port stores spell-cast pet buffs in ``MobInstance.spell_effects``
(a ``SpellEffect`` dict), separate from the integer-SN ``affected`` list that
``_serialize_pet`` walks. Those ``spell_effects`` were never serialized
(GL-030 correctly skips their string-named shadow ``AffectData``), so a pet
buffed with armor/sanctuary/giant-strength lost the buff on reload.

This guards the round-trip: ``_serialize_pet`` → JSON-style dict →
``_deserialize_pet`` must preserve ``spell_effects`` (and must restore them
data-only, with no double-application against the already-modified saved stats —
mirroring ROM ``fread_pet``).
"""

from __future__ import annotations

from mud.account.account_manager import _dataclass_to_dict
from mud.db.serializers import _deserialize_pet, _serialize_pet
from mud.models.character import SpellEffect
from mud.models.constants import AffectFlag, Stat
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


def test_pet_spell_effects_survive_save_reload():
    pet, owner = _make_pet_and_owner()

    # Buff the pet the way casting a spell on a charmed follower does. Cover the
    # tricky-to-serialize SpellEffect fields: ac_mod, an AffectFlag, and a
    # stat_modifiers dict keyed by the Stat IntEnum.
    pet.apply_spell_effect(
        SpellEffect(name="armor", duration=24, level=10, ac_mod=-20)
    )
    pet.apply_spell_effect(
        SpellEffect(
            name="sanctuary",
            duration=8,
            level=12,
            affect_flag=AffectFlag.SANCTUARY,
        )
    )
    pet.apply_spell_effect(
        SpellEffect(
            name="giant strength",
            duration=10,
            level=15,
            stat_modifiers={Stat.STR: 2},
        )
    )
    # A hitroll/damroll-bearing buff is the *discriminating* effect: unlike
    # ac_mod/stat_modifiers (which MobInstance.apply_spell_effect ignores),
    # hitroll_mod/damroll_mod ARE applied live, so they move pet.hitroll/damroll.
    # This is what makes the "no double-application" assertion below non-vacuous —
    # restoring via apply_spell_effect (instead of data-only) would re-add +2,
    # leaving the reloaded pet at base+4 instead of the saved base+2.
    pet.apply_spell_effect(
        SpellEffect(name="bless", duration=6, level=10, hitroll_mod=2, damroll_mod=2)
    )

    # Snapshot the modified stats at save time — ROM saves these *with* the
    # affect bonuses already folded in, so a correct reload must NOT re-apply.
    saved_armor = list(pet.armor)
    saved_hitroll = pet.hitroll
    saved_damroll = pet.damroll

    # Round-trip through the same dict form the DB persists (JSON-style).
    snapshot = _serialize_pet(pet)
    assert snapshot is not None
    pet_dict = _dataclass_to_dict(snapshot)

    restored = _deserialize_pet(pet_dict, owner)
    assert restored is not None

    # The spell effects must be present after reload.
    assert "armor" in restored.spell_effects
    assert "sanctuary" in restored.spell_effects
    assert "giant strength" in restored.spell_effects

    armor_eff = restored.spell_effects["armor"]
    assert armor_eff.ac_mod == -20
    assert armor_eff.duration == 24
    assert armor_eff.level == 10

    sanc_eff = restored.spell_effects["sanctuary"]
    assert sanc_eff.affect_flag == AffectFlag.SANCTUARY

    gs_eff = restored.spell_effects["giant strength"]
    assert gs_eff.stat_modifiers.get(Stat.STR) == 2

    bless_eff = restored.spell_effects["bless"]
    assert bless_eff.hitroll_mod == 2
    assert bless_eff.damroll_mod == 2

    # Data-only restore (ROM fread_pet links affects without affect_modify):
    # the restored stats equal the saved modified values — no double-application.
    # The hitroll/damroll checks are the discriminating ones: a restore that
    # re-ran apply_spell_effect would re-add bless's +2, giving base+4 here.
    assert list(restored.armor) == saved_armor
    assert restored.hitroll == saved_hitroll
    assert restored.damroll == saved_damroll
