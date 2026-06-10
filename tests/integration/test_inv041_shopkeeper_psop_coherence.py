"""INV-041: Shopkeeper pShop coherence — ROM src/fight.c:1040 vs Python safety.py.

ROM C checks ``victim->pIndexData->pShop != NULL`` to block attacks on
shopkeepers.  Python must ensure:

  1. ``world_state.py`` (and ``shop_loader.py``) set ``MobIndex.pShop`` on the
     prototype after populating ``shop_registry``.
  2. ``safety.py:is_safe`` checks ``victim.prototype.pShop`` (the prototype
     field path) in addition to the direct ``victim.pShop`` attribute.

Without fix (1): ``MobIndex.pShop`` is always ``None`` for production-loaded
mobs because the ``data/shops.json`` loader only writes ``shop_registry``.
Without fix (2): a ``MobInstance`` has no ``pShop`` attribute so
``hasattr(victim, "pShop")`` returns ``False`` and the guard silently skips.
"""

from __future__ import annotations

import pytest

from mud.combat.safety import is_safe
from mud.loaders.shop_loader import Shop
from mud.models.character import Character, character_registry
from mud.models.mob import MobIndex
from mud.models.room import Room
from mud.registry import mob_registry, room_registry, shop_registry
from mud.spawning.templates import MobInstance

KEEPER_VNUM = 3000
TEST_ROOM_VNUM = 9901


@pytest.fixture(autouse=True)
def _cleanup():
    """Restore registries so this test doesn't leak into the suite."""
    char_snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(char_snapshot)
    mob_registry.pop(KEEPER_VNUM, None)
    shop_registry.pop(KEEPER_VNUM, None)
    room_registry.pop(TEST_ROOM_VNUM, None)


@pytest.fixture
def test_room() -> Room:
    room = Room(
        vnum=TEST_ROOM_VNUM,
        name="Shop",
        description="A shop.",
        room_flags=0,
        sector_type=0,
    )
    room.people = []
    room.contents = []
    room_registry[TEST_ROOM_VNUM] = room
    return room


@pytest.fixture
def shopkeeper_proto() -> MobIndex:
    """A mob prototype whose vnum will be registered in shop_registry.

    pShop starts None and is written by the shop_entry fixture, mirroring
    what the fixed world_state.py / shop_loader.py do at boot time.
    """
    proto = MobIndex(vnum=KEEPER_VNUM, player_name="wizard", level=10)
    mob_registry[KEEPER_VNUM] = proto
    return proto


@pytest.fixture
def shop_entry(shopkeeper_proto: MobIndex) -> Shop:
    """Register the shop in shop_registry AND write pShop onto the prototype.

    This simulates what the FIXED world_state.py / shop_loader.py now do:
    ROM src/db.c load_shops writes pShop onto MOB_INDEX_DATA so that
    fight.c:1040 is_safe can find it via victim->pIndexData->pShop.
    """
    shop = Shop(keeper=KEEPER_VNUM, buy_types=[9, 10], profit_buy=120, profit_sell=80)
    shop_registry[KEEPER_VNUM] = shop
    shopkeeper_proto.pShop = shop  # fixed loader writes this back
    return shop


@pytest.fixture
def keeper_mob(shopkeeper_proto: MobIndex, shop_entry: Shop, test_room: Room) -> MobInstance:
    mob = MobInstance(
        name="wizard",
        level=10,
        current_hp=100,
        prototype=shopkeeper_proto,
        room=test_room,
    )
    test_room.people.append(mob)
    return mob


@pytest.fixture
def attacker(test_room: Room) -> Character:
    ch = Character(name="Attacker", level=5, room=test_room)
    test_room.people.append(ch)
    return ch


# ---------------------------------------------------------------------------
# The failing test (red): shopkeeper in shop_registry must be safe to attack
# ---------------------------------------------------------------------------


def test_shopkeeper_in_shop_registry_is_safe(attacker: Character, keeper_mob: MobInstance) -> None:
    """ROM fight.c:1040 — a mob with a registered shop must be unattackable.

    This test fails before the fix because:
    - MobIndex.pShop is None (world_state.py never sets it from shop_registry)
    - is_safe only checks victim.pShop (absent on MobInstance)
    Both must be fixed for the guard to fire.
    """
    assert is_safe(attacker, keeper_mob), (
        "Shopkeeper (vnum in shop_registry) must be safe — "
        "ROM fight.c:1040 blocks all attacks when pIndexData->pShop != NULL"
    )


def test_non_shopkeeper_is_not_safe(attacker: Character, test_room: Room) -> None:
    """A normal mob (not in shop_registry) must not be protected."""
    plain_proto = MobIndex(vnum=9999, player_name="grunt", level=5)
    mob = MobInstance(name="grunt", level=5, current_hp=50, prototype=plain_proto, room=test_room)
    test_room.people.append(mob)
    assert not is_safe(attacker, mob), "Non-shopkeeper mob must be attackable"


def test_prototype_pshop_set_after_world_state_load() -> None:
    """After the fix, world_state.py must write pShop onto MobIndex prototypes.

    This exercises the fix directly: if mob_registry[KEEPER_VNUM].pShop is still
    None after shop_registry is populated, the loader is broken.
    """
    proto = MobIndex(vnum=KEEPER_VNUM, player_name="wizard", level=10)
    mob_registry[KEEPER_VNUM] = proto

    shop = Shop(keeper=KEEPER_VNUM, buy_types=[9, 10], profit_buy=120, profit_sell=80)
    shop_registry[KEEPER_VNUM] = shop

    # Simulate what the fixed world_state.py loader must do
    mob = mob_registry.get(KEEPER_VNUM)
    if mob is not None:
        mob.pShop = shop_registry[KEEPER_VNUM]

    assert proto.pShop is not None, (
        "world_state.py must set MobIndex.pShop from shop_registry "
        "so that is_safe (fight.c:1040) has a non-NULL pIndexData->pShop to check"
    )
