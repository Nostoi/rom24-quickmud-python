"""Regression guard for SHOP-PET-001 (reclassified N/A — premise-incorrect).

SHOP-PET-001 was filed claiming a bought pet's ``dam_type`` ends up ``0`` →
attack-table index 0 → noun ``"hit"``, because ``_clone_pet_character`` was
believed to read ``proto.dam_type`` (which the loader leaves at 0; the ``.are``
word lands in ``proto.damage_type``). That premise is factually wrong:
``getattr(template, "dam_type", 0)`` reads the *instance's* resolved index, not
the proto. The pet-shop kennel mob is a ``MobInstance`` produced by
``from_prototype`` (gameplay: ``apply_resets`` → ``spawn_mob`` → ``from_prototype``;
``src/db.c:2084`` ``create_mobile`` does ``attack_lookup`` at load), so its
``dam_type`` is already a resolved attack-table index before the clone copies it.

This guard locks the correct contract so a future "fix" that switches the clone
to read ``proto.dam_type`` (which would reintroduce the noun-"hit" symptom) is
caught. The residual genuine divergence — ROM ``do_buy`` does
``create_mobile(pIndexData)`` (a fresh re-roll), where Python clones the
template's runtime fields — is filed separately as SHOP-PET-002.

ROM C: src/act_obj.c:2613 (``pet = create_mobile(pet->pIndexData)``),
        src/db.c:2084-2097 (``create_mobile`` dam_type resolution),
        src/db2.c:270 (``pMobIndex->dam_type = attack_lookup(fread_word())``).
Python: mud/commands/shop.py:_clone_pet_character (copies template.dam_type).
"""

from __future__ import annotations

import pytest

from mud.combat.messages import ATTACK_TABLE
from mud.commands.shop import do_buy
from mud.models.character import Character, character_registry
from mud.models.constants import ActFlag, RoomFlag, attack_lookup
from mud.models.mob import MobIndex
from mud.models.room import Room
from mud.registry import mob_registry, room_registry
from mud.spawning.templates import MobInstance

# Unique vnums (storefront, storefront+1 = kennel) to avoid collisions with
# sibling tests sharing the registries on the same xdist worker.
_STOREFRONT_VNUM = 48600
_KENNEL_VNUM = _STOREFRONT_VNUM + 1
_PET_PROTO_VNUM = 48650
_DAMTYPE_WORD = "pierce"  # attack_lookup("pierce") == 11, noun "pierce" (not "hit")


@pytest.fixture
def pet_shop():
    """Self-contained pet shop; snapshots/restores the global registries."""
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
    proto.level = 5
    proto.act_flags = int(ActFlag.PET)
    # The .are damtype word lives on proto.damage_type (a string); the loader
    # leaves proto.dam_type at 0. from_prototype resolves it to an index.
    proto.damage_type = _DAMTYPE_WORD
    mob_registry[proto.vnum] = proto

    kennel_pet = MobInstance.from_prototype(proto)
    kennel.add_mob(kennel_pet)

    buyer = Character(name="Buyer", level=10, is_npc=False)
    buyer.gold = 50  # 5000 coins; cost = 10 * 5 * 5 = 250, no haggle needed
    buyer.silver = 0
    storefront.add_character(buyer)
    character_registry.append(buyer)

    try:
        yield buyer, kennel_pet, proto
    finally:
        room_registry.clear()
        room_registry.update(room_snapshot)
        mob_registry.clear()
        mob_registry.update(mob_snapshot)
        character_registry[:] = char_snapshot


def test_bought_pet_inherits_resolved_attack_index(pet_shop):
    """A bought pet's dam_type is the resolved attack-table index, never 0."""
    buyer, kennel_pet, proto = pet_shop

    expected_index = attack_lookup(_DAMTYPE_WORD)
    assert expected_index == 11, "fixture invariant: 'pierce' resolves to index 11"

    # The loader leaves the proto's dam_type at 0 — reading it directly is the
    # SHOP-PET-001 trap. from_prototype resolves the word onto the *instance*.
    assert getattr(proto, "dam_type", 0) == 0
    assert kennel_pet.dam_type == expected_index

    response = do_buy(buyer, "companion")
    assert response == "Enjoy your pet."

    pet = buyer.pet
    assert pet is not None
    # The clone copies the template's resolved index (mirrors ROM create_mobile,
    # which gets the same index for an explicit-word proto).
    assert pet.dam_type == expected_index
    assert pet.dam_type != 0


def test_bought_pet_renders_resolved_noun_not_hit(pet_shop):
    """The bought pet's attack noun is the resolved word, not the index-0 'hit'."""
    buyer = pet_shop[0]

    response = do_buy(buyer, "companion")
    assert response == "Enjoy your pet."

    pet = buyer.pet
    assert pet is not None
    # dam_message resolves the noun via ATTACK_TABLE[dam_type].noun
    # (mud/combat/messages.py:161). Index 0 → "hit"; the SHOP-PET-001 symptom.
    assert ATTACK_TABLE[pet.dam_type].noun == _DAMTYPE_WORD
    assert ATTACK_TABLE[pet.dam_type].noun != "hit"
    assert ATTACK_TABLE[0].noun == "hit"  # documents the symptom we're guarding against
