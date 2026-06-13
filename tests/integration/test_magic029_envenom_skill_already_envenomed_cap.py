"""MAGIC-029 — envenom skill "already envenomed" dict message capitalizes buf[0].

ROM `do_envenom` (`src/act_obj.c:929`): `act("$p is already envenomed.", ch, obj,
NULL, TO_CHAR)` caps the first letter. The Python `envenom` skill returns this
via a `{"message": …}` dict (not `_send_to_char`), and baked a lowercase
`short_descr` ("a serrated dagger is already envenomed."). Filed as a follow-up
under the MAGIC-026 row (different delivery contract from the `poison`-spell weapon
branch closed there).
"""

from __future__ import annotations

from types import SimpleNamespace

from mud.models.character import AffectData, Character
from mud.models.constants import ItemType, WeaponFlag
from mud.models.object import Object
from mud.skills.handlers import envenom

_TO_WEAPON = 5  # mirrors handlers._TO_WEAPON / ROM TO_WEAPON


def test_magic029_envenom_already_poisoned_weapon_message_capitalized():
    # Object.name is a read-only property backed by the prototype, so the lookup
    # name lives on a lightweight proto.
    proto = SimpleNamespace(name="serrated dagger", short_descr=None, item_type=None, extra_flags=0)
    weapon = Object(instance_id=None, prototype=proto)
    weapon.short_descr = "a serrated dagger"
    weapon.item_type = int(ItemType.WEAPON)
    weapon.value = [0, 0, 0, 0]
    weapon.affected = [
        AffectData(
            type=0, level=0, duration=0, location=0, modifier=0, bitvector=int(WeaponFlag.POISON), where=_TO_WEAPON
        )
    ]

    caster = Character(name="Rogue", level=20, is_npc=False)
    caster.skills = {"envenom": 75}
    caster.inventory = [weapon]

    result = envenom(caster, item_name="dagger")
    assert result["success"] is False
    # ROM act("$p is already envenomed.") caps buf[0].
    assert result["message"] == "A serrated dagger is already envenomed.", result
