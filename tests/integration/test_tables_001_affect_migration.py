"""TABLES-001 — pfile AffectFlag bit-position migration.

ROM ``src/merc.h:953-982`` defines ``AFF_*`` letter macros A..dd at bits 0..29.
Pre-2.6.34 Python pfiles encoded ``AffectFlag`` with diverging bit positions.
Saves are now ROM-canonical (``pfile_version=1``); legacy pfiles get
translated on load by ``mud.persistence.translate_legacy_affect_bits``.

These tests pin down:
1. Legacy ``affected_by`` translates to ROM-canonical bits.
2. Legacy nested ``Affect.bitvector`` (item affects) translates.
3. Saves write ``pfile_version=1``.
4. Re-saving a migrated pfile is idempotent (no double-translation).
"""

from __future__ import annotations

import json

import pytest

import mud.persistence as persistence
from mud.models.character import character_registry
from mud.models.constants import AffectFlag, ItemType
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.registry import obj_registry
from mud.world import create_test_character, initialize_world

# Legacy (pre-TABLES-001) Python bit positions, hard-coded for parity.
# These are what pre-2.6.34 saves wrote to disk.
_LEGACY_SANCTUARY = 1 << 6
_LEGACY_DETECT_GOOD = 1 << 10
_LEGACY_HASTE = 1 << 23
_LEGACY_SLOW = 1 << 24
_LEGACY_PLAGUE = 1 << 25


@pytest.fixture
def registered_test_object_factory():
    """Create temporary object prototypes for deterministic migration tests."""

    created_vnums: list[int] = []

    def _factory(vnum: int, *, name: str, short_descr: str, item_type: ItemType | int | str) -> Object:
        proto = ObjIndex(
            vnum=vnum,
            name=name,
            short_descr=short_descr,
            description=f"{short_descr.capitalize()} is here.",
            item_type=item_type,
            value=[0, 0, 0, 0, 0],
        )
        obj_registry[vnum] = proto
        created_vnums.append(vnum)
        obj = Object(instance_id=None, prototype=proto)
        obj.value = list(proto.value)
        obj.contained_items = []
        obj.affected = []
        return obj

    yield _factory

    for vnum in created_vnums:
        obj_registry.pop(vnum, None)


def _save_then_mutate(tmp_path, name: str, mutator) -> None:
    persistence.PLAYERS_DIR = tmp_path
    character_registry.clear()
    initialize_world("area/area.lst")
    char = create_test_character(name, 3001)
    persistence.save_character(char)
    path = tmp_path / f"{name.lower()}.json"
    raw = json.loads(path.read_text())
    mutator(raw)
    path.write_text(json.dumps(raw))


def test_legacy_pfile_affect_bits_translated(tmp_path):
    legacy_bits = _LEGACY_SANCTUARY | _LEGACY_DETECT_GOOD | _LEGACY_HASTE | _LEGACY_SLOW | _LEGACY_PLAGUE

    def _mutate(raw):
        raw["pfile_version"] = 0
        raw["affected_by"] = legacy_bits

    _save_then_mutate(tmp_path, "Legacy", _mutate)
    character_registry.clear()
    loaded = persistence.load_character("Legacy")
    assert loaded is not None

    expected = (
        int(AffectFlag.SANCTUARY)
        | int(AffectFlag.DETECT_GOOD)
        | int(AffectFlag.HASTE)
        | int(AffectFlag.SLOW)
        | int(AffectFlag.PLAGUE)
    )
    assert loaded.affected_by == expected, (
        f"legacy bits {legacy_bits:#x} should translate to {expected:#x}, "
        f"got {loaded.affected_by:#x}"
    )


def test_legacy_active_affect_bitvector_translated(tmp_path, registered_test_object_factory):
    persistence.PLAYERS_DIR = tmp_path
    character_registry.clear()
    initialize_world("area/area.lst")
    char = create_test_character("LegacyObj", 3001)
    sword = registered_test_object_factory(
        3022,
        name="sword",
        short_descr="a wooden sword",
        item_type=ItemType.WEAPON,
    )
    char.add_object(sword)
    persistence.save_character(char)

    path = tmp_path / "legacyobj.json"
    raw = json.loads(path.read_text())
    raw["pfile_version"] = 0
    # Inject a legacy-bit affect on the saved sword.
    if raw["inventory"]:
        raw["inventory"][0]["affects"] = [
            {
                "where": 0,
                "type": 0,
                "level": 1,
                "duration": -1,
                "location": 0,
                "modifier": 0,
                "bitvector": _LEGACY_SANCTUARY | _LEGACY_HASTE,
            }
        ]
    path.write_text(json.dumps(raw))

    character_registry.clear()
    loaded = persistence.load_character("LegacyObj")
    assert loaded is not None
    sword_obj = next((o for o in loaded.inventory if o.prototype.vnum == 3022), None)
    assert sword_obj is not None
    affected = list(getattr(sword_obj, "affected", []))
    assert affected, "expected restored affect on legacy item"
    assert affected[0].bitvector == int(AffectFlag.SANCTUARY) | int(AffectFlag.HASTE)


def test_pfile_save_writes_pfile_version_1(tmp_path):
    persistence.PLAYERS_DIR = tmp_path
    character_registry.clear()
    initialize_world("area/area.lst")
    char = create_test_character("Versioned", 3001)
    persistence.save_character(char)
    raw = json.loads((tmp_path / "versioned.json").read_text())
    assert raw.get("pfile_version") == 1


def test_pfile_round_trip_post_migration_is_idempotent(tmp_path):
    legacy_bits = _LEGACY_SANCTUARY | _LEGACY_HASTE

    def _mutate(raw):
        raw["pfile_version"] = 0
        raw["affected_by"] = legacy_bits

    _save_then_mutate(tmp_path, "Roundtrip", _mutate)
    character_registry.clear()
    loaded = persistence.load_character("Roundtrip")
    assert loaded is not None
    persistence.save_character(loaded)

    raw_after = json.loads((tmp_path / "roundtrip.json").read_text())
    assert raw_after["pfile_version"] == 1
    expected = int(AffectFlag.SANCTUARY) | int(AffectFlag.HASTE)
    assert raw_after["affected_by"] == expected

    # Second load must not re-translate (idempotent).
    character_registry.clear()
    loaded2 = persistence.load_character("Roundtrip")
    assert loaded2 is not None
    assert loaded2.affected_by == expected
