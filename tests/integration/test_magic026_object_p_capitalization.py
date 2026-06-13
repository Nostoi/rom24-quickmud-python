"""MAGIC-026 — object `$p` blocking lines capitalize via act_format.

ROM renders each already-affected object line as `act("$p …", ch, obj, NULL,
TO_CHAR)` — `$p` = `can_see_obj ? obj->short_descr : "something"`, with `buf[0]`
capitalized. The Python baked a lowercase `_object_short_descr(obj)`:

  - `bless` object        — `src/magic.c:794`  "$p is already blessed."
  - `continual_light`     — `src/magic.c:1483` "$p is already glowing."
  - `fireproof`           — `src/magic.c:2770` "$p is already protected from burning."
  - `poison` (weapon)     — `src/magic.c:3968` "$p is already envenomed."

So blessing an already-blessed "a glowing rune" showed "a glowing rune is already
blessed." vs ROM "A glowing rune is already blessed."
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import ExtraFlag, ItemType, WeaponFlag
from mud.models.object import Object
from mud.skills.handlers import bless, continual_light, fireproof, poison


def _obj(short: str, *, extra_flags: int = 0, item_type: int | None = None, value=None) -> Object:
    o = Object(instance_id=None, prototype=None)
    o.short_descr = short
    o.extra_flags = extra_flags
    if item_type is not None:
        o.item_type = item_type
    if value is not None:
        o.value = list(value)
    return o


def _caster() -> Character:
    c = Character(name="Mage", level=30)
    c.messages = []
    return c


def test_magic026_bless_already_blessed_object_capitalized():
    caster = _caster()
    obj = _obj("a glowing rune", extra_flags=int(ExtraFlag.BLESS))
    assert bless(caster, target=obj) is False
    assert any("A glowing rune is already blessed." in m for m in caster.messages), caster.messages


def test_magic026_continual_light_already_glowing_object_capitalized():
    caster = _caster()
    obj = _obj("a bright orb", extra_flags=int(ExtraFlag.GLOW))
    assert continual_light(caster, target=obj) is False
    assert any("A bright orb is already glowing." in m for m in caster.messages), caster.messages


def test_magic026_fireproof_already_protected_object_capitalized():
    caster = _caster()
    obj = _obj("an iron shield", extra_flags=int(ExtraFlag.BURN_PROOF))
    assert fireproof(caster, target=obj) is False
    assert any("An iron shield is already protected from burning." in m for m in caster.messages), caster.messages


def test_magic026_poison_weapon_already_envenomed_object_capitalized():
    caster = _caster()
    weapon = _obj("a sharp dagger", item_type=int(ItemType.WEAPON), value=[0, 0, 0, 0, int(WeaponFlag.POISON)])
    assert poison(caster, target=weapon) is False
    assert any("A sharp dagger is already envenomed." in m for m in caster.messages), caster.messages
