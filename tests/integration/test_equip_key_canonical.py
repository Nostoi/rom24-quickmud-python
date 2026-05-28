"""Equipment-key canonicalization — every equipped object is keyed by the
integer ROM wear slot, `int(WearLocation.X)`.

ROM ground truth: a slot's identity is an integer. `get_eq_char(ch, iWear)`
(`src/handler.c:1733`) loops `obj->wear_loc == iWear`; `equip_char` sets
`obj->wear_loc = iWear` (`src/handler.c:1781`); `merc.h` defines `WEAR_LIGHT 0`,
`WEAR_SHIELD 11`, `WEAR_WIELD 16`. There are no string slot names in ROM.

Python contract: `Character.equipment` is keyed by `int(WearLocation.X)`. The
write paths (`do_wear`, `Character.equip_object`, JSON restore) all canonicalize
to that int key; every reader looks up by that int key. String slot names
("wield", "shield", "hold", "float", "light") are a pre-2.9.87 divergence that
left objects equipped under string keys invisible to int-keyed readers.

This was the broader followup left open by INV-028 (which fixed only the LIGHT
slot via per-reader shims). See AGENTS.md "Equipment lookup" and the
test_equipment_key_convention.py grep-guard that prevents regression.
"""

from __future__ import annotations

import pytest

from mud.account.account_manager import save_character_to_db
from mud.account.account_service import clear_active_accounts, create_character
from mud.combat.engine import _has_shield_equipped
from mud.commands.equipment import do_wear
from mud.commands.inventory import give_school_outfit
from mud.db.models import Base
from mud.db.models import Character as DBCharacter
from mud.db.session import SessionLocal, engine
from mud.models.character import from_orm
from mud.models.constants import ItemType, WearFlag, WearLocation
from mud.models.room import Room, _has_lit_light_source
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.security import bans
from mud.world import create_test_character, initialize_world
from mud.world.world_state import reset_lockdowns


@pytest.fixture(scope="module", autouse=True)
def _world():
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    room_registry.clear()


@pytest.fixture(autouse=True)
def _clean_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()
    yield


def test_school_outfit_light_is_counted_in_room_light():
    """give_school_outfit equips a lit war banner (vnum 3716, item_type light,
    value[2]=200) — it must land under int(WearLocation.LIGHT) so room-light
    accounting (ROM src/handler.c:1504-1573) and burnout decay see it."""
    char = create_test_character("Newbie", 3001)
    char.is_npc = False
    char.equipment = {}

    give_school_outfit(char)

    assert int(WearLocation.LIGHT) in char.equipment, "school light not under int LIGHT key"
    assert _has_lit_light_source(char) is True


def test_do_wear_shield_is_seen_by_combat_shield_check(object_factory):
    """A shield worn via do_wear lands under int(WearLocation.SHIELD); the combat
    shield check (engine._has_shield_equipped, ROM uses get_eq_char(ch,WEAR_SHIELD))
    must find it. Pre-fix the check read the string key 'shield' and missed it."""
    room = Room(vnum=29101, name="Test Room", description="d")
    char = create_test_character("Shielder", 3001)
    char.is_npc = False
    char.equipment = {}
    char.room = room

    shield = object_factory(
        {
            "vnum": 29100,
            "name": "shield",
            "short_descr": "a battered shield",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.TAKE | WearFlag.WEAR_SHIELD),
            "value": [0, 0, 0, 0, 0],
        }
    )
    shield.value = [0, 0, 0, 0, 0]
    char.inventory.append(shield)

    do_wear(char, "shield")

    assert int(WearLocation.SHIELD) in char.equipment, "shield not under int SHIELD key"
    assert _has_shield_equipped(char) is True


def test_equipment_key_survives_db_round_trip_as_int():
    """do_wear a light, save to DB, reload via from_orm — the equipment key must
    come back as int(WearLocation.LIGHT), not the JSON str '0'."""
    from mud.spawning.obj_spawner import spawn_object

    create_character(None, "Rounder", starting_room_vnum=3001)
    session = SessionLocal()
    db_row = session.query(DBCharacter).filter_by(name="Rounder").first()
    assert db_row is not None
    char = from_orm(db_row)
    session.close()

    banner = spawn_object(3716)  # a war banner — item_type light, value[2]=200
    assert banner is not None
    char.inventory.append(banner)

    do_wear(char, "banner")
    assert int(WearLocation.LIGHT) in char.equipment

    session = SessionLocal()
    try:
        save_character_to_db(session, char)
        session.commit()
        db_char = session.query(DBCharacter).filter_by(name="Rounder").first()
        reloaded = from_orm(db_char)
    finally:
        session.close()

    assert int(WearLocation.LIGHT) in reloaded.equipment, "reloaded LIGHT key is not int"
    assert str(int(WearLocation.LIGHT)) not in reloaded.equipment, "stale str key survived reload"
