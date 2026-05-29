"""SHOP-PET-002: a bought pet is a fresh ``create_mobile(pIndexData)``, not a
template clone.

ROM ``do_buy`` (``src/act_obj.c:2613``) does ``pet = create_mobile (pet->pIndexData)``
— a **fresh** mobile re-rolled from the index, NOT a copy of the kennel template's
already-rolled runtime fields. ``create_mobile`` (``src/db.c:2047-2113``) draws the
spawn RNG stream in a fixed order — gold -> hp -> mana -> damtype (when unset) ->
sex (when random) — and re-rolls each value from the prototype.

The pre-fix Python (``_clone_pet_character``) instead copied the kennel
``MobInstance``'s runtime fields, so a bought pet:
  (a) inherited the template's *cloned* random-default dam_type instead of
      re-rolling ``number_range(1,3)`` per ``create_mobile``;
  (b) advanced the spawn RNG stream by **zero** draws, desyncing any RNG consumer
      ordered after the purchase versus ROM;
  (c) inherited HP/mana/gold from the template rather than freshly rolling them.

This test pins the ROM contract: the bought pet's random fields equal a fresh
``MobInstance.from_prototype`` (the ``create_mobile`` equivalent) rolled from the
same seed, AND the purchase advances the RNG stream by exactly the same number of
draws. The stream-advance assertion is the deterministic clone discriminator — a
clone draws nothing.

ROM C: src/act_obj.c:2613 (``pet = create_mobile(pet->pIndexData)``),
        src/db.c:2047-2113 (``create_mobile`` RNG draw order).
Python: mud/commands/shop.py:_handle_pet_shop_purchase.
"""

from __future__ import annotations

import pytest

from mud.commands.shop import do_buy
from mud.models.character import Character, character_registry
from mud.models.constants import ActFlag, AffectFlag, CommFlag, RoomFlag
from mud.models.mob import MobIndex
from mud.models.room import Room
from mud.registry import mob_registry, room_registry
from mud.spawning.templates import MobInstance
from mud.utils import rng_mm

# Unique vnums (storefront, storefront+1 = kennel) to avoid collisions with
# sibling tests sharing the registries on the same xdist worker.
_STOREFRONT_VNUM = 48700
_KENNEL_VNUM = _STOREFRONT_VNUM + 1
_PET_PROTO_VNUM = 48750
_SEED = 20260529


@pytest.fixture
def pet_shop():
    """Self-contained pet shop with a *rollable* proto; restores registries.

    The proto carries rollable random fields (wealth, hit/mana dice, and an
    unset damage word) so ``create_mobile`` actually draws the spawn RNG stream,
    making the clone-vs-reroll divergence observable.
    """
    room_snapshot = dict(room_registry)
    mob_snapshot = dict(mob_registry)
    char_snapshot = list(character_registry)

    storefront = Room(vnum=_STOREFRONT_VNUM, name="Pet Shop Lobby")
    storefront.room_flags = int(RoomFlag.ROOM_PET_SHOP)
    kennel = Room(vnum=_KENNEL_VNUM, name="Kennel")
    room_registry[storefront.vnum] = storefront
    room_registry[kennel.vnum] = kennel

    proto = MobIndex(
        vnum=_PET_PROTO_VNUM,
        short_descr="a cuddly companion",
        player_name="companion pet",
    )
    proto.description = "A bright-eyed pet watches you expectantly.\n"
    proto.level = 3
    proto.act_flags = int(ActFlag.PET)
    # Rollable fields so create_mobile draws gold -> hp -> mana -> damtype.
    proto.wealth = 5000
    proto.hit = (10, 10, 100)  # max_hit = dice(10,10)+100 -> 110..200
    proto.mana = (5, 5, 50)
    # damage_type defaults to "beating" (resolves to a fixed index); blank it so
    # create_mobile takes the unset path and rolls number_range(1,3) for dam_type.
    proto.damage_type = ""
    mob_registry[proto.vnum] = proto

    # Kennel template — itself a from_prototype instance (rolled at whatever the
    # ambient RNG state is). The bought pet must NOT be a copy of this.
    template = MobInstance.from_prototype(proto)
    kennel.add_mob(template)

    buyer = Character(name="Buyer", level=10, is_npc=False)
    buyer.gold = 10  # 1000 coins; cost = 10 * 3 * 3 = 90
    buyer.silver = 0
    # No haggle skill: the ONLY RNG draws during the purchase are create_mobile's.
    storefront.add_character(buyer)
    character_registry.append(buyer)

    try:
        yield buyer, template, proto
    finally:
        room_registry.clear()
        room_registry.update(room_snapshot)
        mob_registry.clear()
        mob_registry.update(mob_snapshot)
        character_registry[:] = char_snapshot


def test_bought_pet_is_fresh_create_mobile_not_template_clone(pet_shop):
    """The bought pet re-rolls from the prototype and advances the RNG stream."""
    buyer, template, proto = pet_shop

    # Control: exactly what ROM create_mobile(pIndexData) yields from this proto,
    # plus the RNG stream position immediately afterward.
    rng_mm.seed_mm(_SEED)
    control = MobInstance.from_prototype(proto)
    control_next = rng_mm.number_range(1, 1_000_000)

    # Buy from the same seed. With no haggle skill, the only RNG draws in the
    # purchase path are create_mobile's (haggle would draw before pet creation).
    rng_mm.seed_mm(_SEED)
    response = do_buy(buyer, "companion")
    assert response == "Enjoy your pet."
    bought = buyer.pet
    assert bought is not None
    bought_next = rng_mm.number_range(1, 1_000_000)

    # (b) The purchase advanced the spawn RNG stream exactly as create_mobile
    # does. A template clone draws ZERO — this is the deterministic discriminator.
    assert bought_next == control_next

    # (a)(c) The pet's random fields are FRESHLY rolled from the index, matching a
    # create_mobile from the same seed — not copied from the kennel template.
    assert bought.max_hit == control.max_hit
    assert bought.hit == control.max_hit  # full health, like ROM mob->hit = max_hit
    assert bought.gold == control.gold
    assert bought.silver == control.silver
    assert bought.dam_type == control.dam_type

    # It is a distinct instance re-created from the prototype, not the template.
    assert bought is not template
    assert bought.prototype is proto

    # The ROM do_buy overrides survive the re-creation (src/act_obj.c:2614-2616).
    assert bought.act & int(ActFlag.PET)
    assert bought.has_affect(AffectFlag.CHARM)
    assert bought.comm & int(CommFlag.NOTELL)
    assert bought.comm & int(CommFlag.NOSHOUT)
    assert bought.comm & int(CommFlag.NOCHANNELS)
