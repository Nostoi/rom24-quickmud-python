"""Integration tests for JSON loader ROM parity gaps (JSONLD-001..018).

Each test loads a minimal JSON area and verifies that the loader produces
ROM-correct data structures, closing gaps identified in
``docs/parity/JSON_LOADER_C_AUDIT.md``.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from mud.loaders.json_loader import load_area_from_json
from mud.models.constants import (
    EX_CLOSED,
    EX_ISDOOR,
    EX_LOCKED,
    FormFlag,
    ImmFlag,
    OffFlag,
    PartFlag,
    ResFlag,
    VulnFlag,
    WearFlag,
)
from mud.models.obj import Affect
from mud.models.races import race_lookup
from mud.models.room import ExtraDescr
from mud.registry import area_registry, mob_registry, obj_registry, room_registry


@pytest.fixture(autouse=True)
def _clean_registries():
    saved_area = dict(area_registry)
    saved_mob = dict(mob_registry)
    saved_obj = dict(obj_registry)
    saved_room = dict(room_registry)
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    room_registry.clear()
    try:
        yield
    finally:
        area_registry.clear()
        mob_registry.clear()
        obj_registry.clear()
        room_registry.clear()
        area_registry.update(saved_area)
        mob_registry.update(saved_mob)
        obj_registry.update(saved_obj)
        room_registry.update(saved_room)


def _write_json(tmp_path: pathlib.Path, data: dict) -> pathlib.Path:
    p = tmp_path / "test_area.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


_MINIMAL_AREA = {
    "name": "Test Area",
    "vnum_range": {"min": 3000, "max": 3099},
    "builders": ["Tester"],
    "rooms": [],
    "mobiles": [],
    "objects": [],
    "resets": [],
}


class TestJSONLD004DiceTuples:
    """JSONLD-004: mob hit/mana/damage int tuples populated at load time."""

    def test_hit_tuple_parsed_from_dice_string(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        area_data["mobiles"] = [
            {
                "id": 3000,
                "name": "test mob",
                "race": "human",
                "hit_dice": "5d10+20",
                "mana_dice": "3d8+5",
                "damage_dice": "2d6+3",
            }
        ]
        p = _write_json(tmp_path, area_data)
        load_area_from_json(str(p))
        mob = mob_registry[3000]
        assert mob.hit == (5, 10, 20), f"Expected (5,10,20) got {mob.hit}"
        assert mob.mana == (3, 8, 5), f"Expected (3,8,5) got {mob.mana}"
        assert mob.damage == (2, 6, 3), f"Expected (2,6,3) got {mob.damage}"

    def test_dice_tuple_defaults_to_dice_string_default(self, tmp_path: pathlib.Path):
        """When hit_dice is omitted from JSON, MobIndex default is ``1d1+0``,
        which parses to ``(1, 1, 0)`` — not ``(0, 0, 0)``. This matches ROM
        which uses ``1d1`` as the base mob dice profile."""
        area_data = dict(_MINIMAL_AREA)
        area_data["mobiles"] = [{"id": 3001, "name": "minimal mob", "race": "human"}]
        p = _write_json(tmp_path, area_data)
        load_area_from_json(str(p))
        mob = mob_registry[3001]
        assert mob.hit == (1, 1, 0), f"Default hit tuple should parse 1d1+0, got {mob.hit}"
        assert mob.mana == (1, 1, 0)
        assert mob.damage == (1, 4, 0)  # default damage_dice is 1d4+0


class TestJSONLD007Hitroll:
    """JSONLD-007: mob hitroll populated from JSON, prefers hitroll over thac0."""

    def test_hitroll_from_hitroll_key(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        area_data["mobiles"] = [{"id": 3000, "name": "hitroll mob", "race": "human", "hitroll": 5, "thac0": 20}]
        p = _write_json(tmp_path, area_data)
        load_area_from_json(str(p))
        assert mob_registry[3000].hitroll == 5

    def test_hitroll_falls_back_to_thac0(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        area_data["mobiles"] = [{"id": 3001, "name": "thac0 mob", "race": "human", "thac0": 17}]
        p = _write_json(tmp_path, area_data)
        load_area_from_json(str(p))
        assert mob_registry[3001].hitroll == 17

    def test_hitroll_defaults_to_zero(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        area_data["mobiles"] = [{"id": 3002, "name": "no hitroll mob", "race": "human"}]
        p = _write_json(tmp_path, area_data)
        load_area_from_json(str(p))
        assert mob_registry[3002].hitroll == 0


class TestJSONLD005WearFlags:
    """JSONLD-005: object wear_flags converted from string to int bitmask."""

    def test_wear_flags_string_converted_to_int(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        # "A" = TAKE (bit 0), "N" = WIELD (bit 13): TAKE+WEAR_NECK+WEAR_ARMS+WIELD
        area_data["objects"] = [{"id": 3000, "name": "a sword", "item_type": "weapon", "wear_flags": "AN"}]
        p = _write_json(tmp_path, area_data)
        load_area_from_json(str(p))
        obj = obj_registry[3000]
        assert isinstance(obj.wear_flags, int), f"Expected int, got {type(obj.wear_flags)}"
        assert obj.wear_flags & int(WearFlag.TAKE)
        assert obj.wear_flags & int(WearFlag.WIELD)

    def test_wear_flags_integer_passthrough(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        area_data["objects"] = [{"id": 3001, "name": "a ring", "item_type": "armor", "wear_flags": 3}]
        p = _write_json(tmp_path, area_data)
        load_area_from_json(str(p))
        obj = obj_registry[3001]
        assert isinstance(obj.wear_flags, int)
        assert obj.wear_flags == 3

    def test_wear_flags_empty_string_is_zero(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        area_data["objects"] = [{"id": 3002, "name": "a thing", "item_type": "trash", "wear_flags": ""}]
        p = _write_json(tmp_path, area_data)
        load_area_from_json(str(p))
        assert obj_registry[3002].wear_flags == 0


class TestJSONLD002ExtraDescr:
    """JSONLD-002: object extra_descr stored as ExtraDescr instances, not raw dicts."""

    def test_object_extra_descr_are_extradescr_instances(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        area_data["objects"] = [
            {
                "id": 3000,
                "name": "a glowing sword",
                "item_type": "weapon",
                "extra_descriptions": [
                    {"keyword": "runes blade", "description": "Ancient runes glow on the blade.\n"},
                    {"keyword": "hilt", "description": "The hilt is wrapped in leather.\n"},
                ],
            }
        ]
        p = _write_json(tmp_path, area_data)
        load_area_from_json(str(p))
        obj = obj_registry[3000]
        assert len(obj.extra_descr) == 2
        assert isinstance(obj.extra_descr[0], ExtraDescr)
        assert obj.extra_descr[0].keyword == "runes blade"
        assert obj.extra_descr[0].description.startswith("Ancient runes")
        assert isinstance(obj.extra_descr[1], ExtraDescr)
        assert obj.extra_descr[1].keyword == "hilt"


class TestJSONLD006ObjectAffects:
    """JSONLD-006: object affects populate both dicts and typed Affect instances."""

    def test_object_affects_populate_affected_list(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        area_data["objects"] = [
            {
                "id": 3000,
                "name": "a ring of strength",
                "item_type": "armor",
                "level": 10,
                "affects": [
                    {"location": 1, "modifier": 2},
                    {"location": 3, "modifier": -1},
                ],
            }
        ]
        p = _write_json(tmp_path, area_data)
        load_area_from_json(str(p))
        obj = obj_registry[3000]
        assert len(obj.affects) == 2
        assert len(obj.affected) == 2
        aff0 = obj.affected[0]
        assert isinstance(aff0, Affect)
        assert aff0.location == 1
        assert aff0.modifier == 2
        assert aff0.level == 10  # mirrors ROM: pObjIndex->level
        assert aff0.duration == -1
        assert aff0.type == -1

    def test_object_affects_with_where_field(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        area_data["objects"] = [
            {
                "id": 3001,
                "name": "an immune cloak",
                "item_type": "armor",
                "level": 15,
                "affects": [
                    {"where": "TO_IMMUNE", "location": 0, "modifier": 0, "bitvector": 4},
                ],
            }
        ]
        p = _write_json(tmp_path, area_data)
        load_area_from_json(str(p))
        obj = obj_registry[3001]
        aff = obj.affected[0]
        assert aff.where == 2  # TO_IMMUNE = 2
        assert aff.bitvector == 4


class TestJSONLD008OffImmResVulnInts:
    """JSONLD-008: mob off/imm/res/vuln int fields populated after merge_race_flags."""

    def test_off_flags_populated_as_int(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        area_data["mobiles"] = [{"id": 3000, "name": "a warrior", "race": "human", "offensive": "B"}]
        p = _write_json(tmp_path, area_data)
        load_area_from_json(str(p))
        mob = mob_registry[3000]
        assert isinstance(mob.off_flags, int), f"Expected int, got {type(mob.off_flags)}"
        assert mob.off_flags & int(OffFlag.BACKSTAB)

    def test_imm_flags_populated_as_int(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        area_data["mobiles"] = [{"id": 3001, "name": "a fire elemental", "race": "human", "immune": "A"}]
        p = _write_json(tmp_path, area_data)
        load_area_from_json(str(p))
        mob = mob_registry[3001]
        assert isinstance(mob.imm_flags, int)
        assert mob.imm_flags & int(ImmFlag.SUMMON)

    def test_res_flags_populated_as_int(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        area_data["mobiles"] = [{"id": 3002, "name": "a resistant mob", "race": "human", "resist": "D"}]
        p = _write_json(tmp_path, area_data)
        load_area_from_json(str(p))
        mob = mob_registry[3002]
        assert isinstance(mob.res_flags, int)
        assert mob.res_flags & int(ResFlag.WEAPON)

    def test_vuln_flags_populated_as_int(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        # "E" = bit 4 = BASH in VulnFlag namespace
        area_data["mobiles"] = [{"id": 3003, "name": "a vuln mob", "race": "human", "vuln": "E"}]
        p = _write_json(tmp_path, area_data)
        load_area_from_json(str(p))
        mob = mob_registry[3003]
        assert isinstance(mob.vuln_flags, int)
        assert mob.vuln_flags & int(VulnFlag.BASH)

    def test_empty_flags_default_to_zero(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        area_data["mobiles"] = [
            {
                "id": 3004,
                "name": "a blank mob",
                "race": "human",
                "offensive": "",
                "immune": "",
                "resist": "",
                "vuln": "",
            }
        ]
        p = _write_json(tmp_path, area_data)
        load_area_from_json(str(p))
        mob = mob_registry[3004]
        assert mob.off_flags == 0
        assert mob.imm_flags == 0
        assert mob.res_flags == 0
        assert mob.vuln_flags == 0


class TestJSONLD011FormParts:
    """JSONLD-011: mob form/parts stored as int bitmasks after merge_race_flags."""

    def test_form_converted_to_int(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        area_data["mobiles"] = [{"id": 3000, "name": "an edible mob", "race": "human", "form": "A"}]
        p = _write_json(tmp_path, area_data)
        load_area_from_json(str(p))
        mob = mob_registry[3000]
        assert isinstance(mob.form, int), f"Expected int, got {type(mob.form)}"
        assert mob.form & int(FormFlag.EDIBLE)

    def test_parts_converted_to_int(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        area_data["mobiles"] = [{"id": 3001, "name": "a mob with parts", "race": "human", "parts": "ABC"}]
        p = _write_json(tmp_path, area_data)
        load_area_from_json(str(p))
        mob = mob_registry[3001]
        assert isinstance(mob.parts, int), f"Expected int, got {type(mob.parts)}"
        assert mob.parts & int(PartFlag.HEAD)
        assert mob.parts & int(PartFlag.ARMS)
        assert mob.parts & int(PartFlag.LEGS)

    def test_form_zero_string_propagates_race_flags(self, tmp_path: pathlib.Path):
        """Even when form starts as "0", merge_race_flags adds race base
        form flags (e.g. human: SENTIENT|BIPED|MAMMAL). The int result
        must include those race bits."""
        area_data = dict(_MINIMAL_AREA)
        area_data["mobiles"] = [{"id": 3002, "name": "a formless mob", "race": "human", "form": "0"}]
        p = _write_json(tmp_path, area_data)
        load_area_from_json(str(p))
        mob = mob_registry[3002]
        assert isinstance(mob.form, int)
        # Human race adds SENTIENT|BIPED|MAMMAL = H|M|V bits = (1<<7)|(1<<12)|(1<<21)
        assert mob.form & int(FormFlag.SENTIENT)


class TestJSONLD009AreaSecurity:
    """JSONLD-009: area security defaults to ROM's builder security value."""

    def test_format1_area_security_defaults_to_nine(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        p = _write_json(tmp_path, area_data)

        area = load_area_from_json(str(p))

        assert area.security == 9

    def test_format2_area_security_defaults_to_nine_when_missing(self, tmp_path: pathlib.Path):
        area_data = {
            "area": {
                "vnum": 3200,
                "name": "Format Two Area",
                "filename": "format_two",
                "builders": "Tester",
            },
            "rooms": [],
            "mobs": [],
            "objects": [],
            "resets": [],
        }
        p = _write_json(tmp_path, area_data)

        area = load_area_from_json(str(p))

        assert area.security == 9

    def test_format2_area_security_uses_json_value_when_present(self, tmp_path: pathlib.Path):
        area_data = {
            "area": {
                "vnum": 3201,
                "name": "Format Two Area",
                "filename": "format_two",
                "builders": "Tester",
                "security": 4,
            },
            "rooms": [],
            "mobs": [],
            "objects": [],
            "resets": [],
        }
        p = _write_json(tmp_path, area_data)

        area = load_area_from_json(str(p))

        assert area.security == 4


class TestJSONLD010AreaCredits:
    """JSONLD-010: Format 1 area credits load from JSON when present."""

    def test_format1_area_credits_loaded_from_json(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        area_data["credits"] = "ROM area credits string"
        p = _write_json(tmp_path, area_data)

        area = load_area_from_json(str(p))

        assert area.credits == "ROM area credits string"


class TestJSONLD013RoomClan:
    """JSONLD-013: room clan names resolve through ROM clan_lookup semantics."""

    def test_room_clan_name_resolves_to_clan_id(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        area_data["rooms"] = [{"id": 3000, "name": "Clan Room", "description": "", "clan": "rom"}]
        p = _write_json(tmp_path, area_data)

        load_area_from_json(str(p))

        assert room_registry[3000].clan == 2

    def test_room_clan_prefix_resolves_to_clan_id(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        area_data["rooms"] = [{"id": 3000, "name": "Clan Room", "description": "", "clan": "lo"}]
        p = _write_json(tmp_path, area_data)

        load_area_from_json(str(p))

        assert room_registry[3000].clan == 1

    def test_room_clan_integer_passes_through(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        area_data["rooms"] = [{"id": 3000, "name": "Clan Room", "description": "", "clan": 2}]
        p = _write_json(tmp_path, area_data)

        load_area_from_json(str(p))

        assert room_registry[3000].clan == 2


class TestJSONLD014DoorResets:
    """JSONLD-014: D resets apply boot door state and are discarded."""

    def test_d_reset_locks_forward_exit_and_is_not_stored(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        area_data["rooms"] = [
            {
                "id": 3000,
                "name": "West Room",
                "description": "",
                "exits": {
                    "east": {
                        "to_room": 3001,
                        "description": "",
                        "keyword": "door",
                        "flags": EX_ISDOOR,
                    }
                },
            },
            {"id": 3001, "name": "East Room", "description": ""},
        ]
        # mirrors ROM src/db.c:1058-1104 — D reset sets boot door state and is freed.
        area_data["resets"] = [{"command": "D", "arg1": 3000, "arg2": 1, "arg3": 2}]
        p = _write_json(tmp_path, area_data)

        area = load_area_from_json(str(p))

        east_exit = room_registry[3000].exits[1]
        assert east_exit is not None
        assert east_exit.rs_flags & EX_ISDOOR
        assert east_exit.rs_flags & EX_CLOSED
        assert east_exit.rs_flags & EX_LOCKED
        assert east_exit.exit_info == east_exit.rs_flags
        assert all(reset.command != "D" for reset in area.resets)
        assert all(reset.command != "D" for reset in room_registry[3000].resets)


class TestJSONLD012MobRaceIndex:
    """JSONLD-012: JSON mob race names resolve to ROM race_table indexes."""

    def test_mob_race_name_resolves_to_int_index(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        area_data["mobiles"] = [{"id": 3000, "name": "a human", "race": "human"}]
        p = _write_json(tmp_path, area_data)

        load_area_from_json(str(p))

        mob = mob_registry[3000]
        assert isinstance(mob.race, int)
        assert mob.race == race_lookup("human")

    def test_mob_race_prefix_matches_rom_race_lookup(self, tmp_path: pathlib.Path):
        area_data = dict(_MINIMAL_AREA)
        area_data["mobiles"] = [{"id": 3001, "name": "a dragon", "race": "drag"}]
        p = _write_json(tmp_path, area_data)

        load_area_from_json(str(p))

        mob = mob_registry[3001]
        assert isinstance(mob.race, int)
        assert mob.race == race_lookup("dragon")
