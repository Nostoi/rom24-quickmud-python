import json
from pathlib import Path

import pytest

from mud.loaders import load_area_file
from mud.loaders.json_loader import load_area_from_json
from mud.loaders.reset_loader import validate_resets
from mud.models.constants import (
    AffectFlag,
    AreaFlag,
    ContainerFlag,
    Direction,
    EX_CLOSED,
    EX_ISDOOR,
    EX_PICKPROOF,
    ExtraFlag,
    LIQUID_TABLE,
    RoomFlag,
    WeaponFlag,
    WeaponType,
    WearFlag,
    attack_lookup,
    convert_flags_from_letters,
)
from mud.models.help import clear_help_registry, help_registry
from mud.mobprog import Trigger, clear_registered_programs, get_registered_program
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.scripts.convert_are_to_json import clear_registries, convert_area
from mud.spawning.obj_spawner import spawn_object
from mud.skills.metadata import ROM_SKILL_NAMES_BY_INDEX


def test_duplicate_area_vnum_raises_value_error(tmp_path):
    area_registry.clear()
    src = Path("area") / "midgaard.are"
    lines = src.read_text(encoding="latin-1").splitlines()
    lines[1] = "dup.are~"
    dup = tmp_path / "dup.are"
    dup.write_text("\n".join(lines), encoding="latin-1")
    load_area_file(str(src))
    with pytest.raises(ValueError):
        load_area_file(str(dup))
    area_registry.clear()


def test_area_header_requires_terminating_tildes(tmp_path):
    area_registry.clear()
    content = (
        "#AREA\n"
        "invalid.are\n"  # missing trailing tilde
        "Invalid~\n"
        "Credits~\n"
        "0 1\n"
        "#$\n"
    )
    path = tmp_path / "invalid.are"
    path.write_text(content, encoding="latin-1")

    with pytest.raises(ValueError, match="must end with '~'"):
        load_area_file(str(path))

    area_registry.clear()


def test_area_header_requires_two_vnum_integers(tmp_path):
    area_registry.clear()
    content = (
        "#AREA\n"
        "valid.are~\n"
        "Valid~\n"
        "Credits~\n"
        "3000\n"  # missing max vnum
        "#$\n"
    )
    path = tmp_path / "valid.are"
    path.write_text(content, encoding="latin-1")

    with pytest.raises(ValueError, match="vnum range"):
        load_area_file(str(path))

    area_registry.clear()


def test_area_header_rejects_descending_vnum_range(tmp_path):
    area_registry.clear()
    content = (
        "#AREA\n"
        "reverse.are~\n"
        "Reverse~\n"
        "Credits~\n"
        "4000 3999\n"
        "#$\n"
    )
    path = tmp_path / "reverse.are"
    path.write_text(content, encoding="latin-1")

    with pytest.raises(ValueError, match="min_vnum cannot exceed max_vnum"):
        load_area_file(str(path))

    area_registry.clear()


def test_areadata_parsing(tmp_path):
    area_registry.clear()
    content = "#AREA\ntest.are~\nTest Area~\nCredits~\n0 0\n#AREADATA\nBuilders Alice~\nSecurity 9\nFlags 3\n#$\n"
    path = tmp_path / "test.are"
    path.write_text(content, encoding="latin-1")
    area = load_area_file(str(path))
    assert area.builders == "Alice"
    assert area.security == 9
    assert area.area_flags == 3
    area_registry.clear()


def test_new_areadata_header_populates_metadata(tmp_path):
    area_registry.clear()
    content = (
        "#AREADATA\n"
        "Name New Midgaard~\n"
        "Credits City Credits~\n"
        "Builders BuilderX~\n"
        "Security 7\n"
        "VNUMs 3000 3099\n"
        "End\n"
        "#AREA\n"
        "midgaard.are~\n"
        "Old Midgaard~\n"
        "Old Credits~\n"
        "3100 3199\n"
        "#$\n"
    )
    path = tmp_path / "new_midgaard.are"
    path.write_text(content, encoding="latin-1")

    area = load_area_file(str(path))

    assert area.name == "New Midgaard"
    assert area.credits == "City Credits"
    assert area.builders == "BuilderX"
    assert area.security == 7
    assert area.min_vnum == 3000
    assert area.max_vnum == 3099

    area_registry.clear()


def test_area_loader_seeds_rom_defaults(tmp_path):
    area_registry.clear()
    content = (
        "#AREA\n"
        "defaults.are~\n"
        "Defaults~\n"
        "Credits~\n"
        "0 0\n"
        "#$\n"
    )
    path = tmp_path / "defaults.are"
    path.write_text(content, encoding="latin-1")

    area = load_area_file(str(path))

    assert area.age == 15
    assert area.nplayer == 0
    assert area.empty is False
    assert area.security == 9
    assert area.builders == "None"
    assert area.area_flags == AreaFlag.LOADING

    area_registry.clear()


def test_help_section_registers_entries(tmp_path):
    clear_help_registry()
    area_registry.clear()
    content = (
        "#AREA\n"
        "help_test.are~\n"
        "Help Test~\n"
        "Credits~\n"
        "0 0\n"
        "#HELPS\n"
        "0 PRIMARY 'Second Keyword' third~\n"
        "First line.\n"
        "Second line.\n"
        "~\n"
        "0 $~\n"
        "#$\n"
    )
    path = tmp_path / "help_test.are"
    path.write_text(content, encoding="latin-1")

    area = load_area_file(str(path))

    entry_list = help_registry["primary"]
    assert len(entry_list) == 1
    entry = entry_list[0]
    assert entry in area.helps
    assert entry.level == 0
    assert entry.text == "First line.\nSecond line.\n"
    assert set(entry.keywords) == {"PRIMARY", "Second Keyword", "third"}
    assert help_registry["second keyword"][0] is entry
    assert help_registry["third"][0] is entry

    clear_help_registry()
    area_registry.clear()


def test_loads_mobprogs_registers_code(tmp_path):
    area_registry.clear()
    room_registry.clear()
    mob_registry.clear()
    clear_registered_programs()

    content = (
        "#AREA\n"
        "mprog.are~\n"
        "MobProg Test~\n"
        "Credits~\n"
        "1 1\n"
        "#MOBILES\n"
        "#1\n"
        "testmob~\n"
        "A test mob~\n"
        "This mob has a script.~\n"
        "A plain description.~\n"
        "human~\n"
        "0 0 0 0\n"
        "1 0 0 1d1+0 1d1+0 1d1+0 beating\n"
        "0 0 0 0\n"
        "0 0 0 0\n"
        "standing standing neutral 0\n"
        "0 0 medium 0\n"
        "M GREET 5000 hello there~\n"
        "#0\n"
        "#MOBPROGS\n"
        "#5000\n"
        "say Hello there!\n"
        "~\n"
        "#0\n"
        "#$\n"
    )
    path = tmp_path / "mprog.are"
    path.write_text(content, encoding="latin-1")

    load_area_file(str(path))

    mob = mob_registry[1]
    assert mob.mprogs
    program = mob.mprogs[0]
    assert program.vnum == 5000
    assert program.trig_phrase == "hello there"
    assert program.trig_type == int(Trigger.GREET)
    assert program.code == "say Hello there!"
    assert get_registered_program(5000) is program

    area_registry.clear()
    room_registry.clear()
    mob_registry.clear()
    clear_registered_programs()


def test_mob_flag_removal_lines_clear_flags(tmp_path):
    area_registry.clear()
    mob_registry.clear()

    content = (
        "#AREA\n"
        "flag_test.are~\n"
        "Flag Test~\n"
        "Credits~\n"
        "1 1\n"
        "#MOBILES\n"
        "#1\n"
        "flag remover~\n"
        "A flag remover mob~\n"
        "A flag remover mob stands here.~\n"
        "It looks configurable.~\n"
        "human~\n"
        "ABCD EFG 0 0\n"
        "10 0 0 1d1+0 1d1+0 1d1+0 slash\n"
        "0 0 0 0\n"
        "ABC DEF GHI JKL\n"
        "standing standing neutral 0\n"
        "ABCD EFGH medium iron\n"
        "F act AC\n"
        "F aff G\n"
        "F off AC\n"
        "F imm D\n"
        "F res HI\n"
        "F vul L\n"
        "F for AD\n"
        "F par EH\n"
        "#0\n"
        "#$\n"
    )

    path = tmp_path / "flag_test.are"
    path.write_text(content, encoding="latin-1")

    load_area_file(str(path))

    mob = mob_registry[1]
    assert mob.act_flags == "BD"
    assert mob.affected_by == "EF"
    assert mob.offensive == "B"
    assert mob.immune == "EF"
    assert mob.resist == "G"
    assert mob.vuln == "JK"
    assert mob.form == "BC"
    assert mob.parts == "FG"

    area_registry.clear()
    mob_registry.clear()


def test_object_flag_affects_loaded(tmp_path):
    area_registry.clear()
    obj_registry.clear()

    content = (
        "#AREA\n"
        "flag_obj.are~\n"
        "Flag Object~\n"
        "Credits~\n"
        "1 1\n"
        "#OBJECTS\n"
        "#1\n"
        "flagged sword~\n"
        "a flagged sword~\n"
        "A flagged sword lies here.~\n"
        "steel~\n"
        "weapon ABC AB\n"
        "0 0 0 0 0\n"
        "10 100 P\n"
        "A\n"
        "18 2\n"
        "F A 18 2 AFF_HASTE\n"
        "#0\n"
        "#$\n"
    )

    path = tmp_path / "flag_obj.are"
    path.write_text(content, encoding="latin-1")

    load_area_file(str(path))

    obj = obj_registry[1]
    base_affect = obj.affects[0]
    assert base_affect == {"location": 18, "modifier": 2}
    assert obj.affected[0].where == 1
    assert obj.affected[0].location == 18
    assert obj.affected[0].modifier == 2

    flag_affect_dict = obj.affects[1]
    assert flag_affect_dict["where"] == "A"
    assert flag_affect_dict["location"] == 18
    assert flag_affect_dict["modifier"] == 2
    assert flag_affect_dict["bitvector"] == int(AffectFlag.HASTE)

    flag_affect = obj.affected[1]
    assert flag_affect.where == 0
    assert flag_affect.location == 18
    assert flag_affect.modifier == 2
    assert flag_affect.bitvector == int(AffectFlag.HASTE)

    runtime = spawn_object(1)
    assert runtime is not None
    assert len(runtime.affected) == len(obj.affected)
    assert runtime.affected[0].location == 18
    assert runtime.affected[1].bitvector == int(AffectFlag.HASTE)

    area_registry.clear()
    obj_registry.clear()


def test_object_level_and_condition_loaded(tmp_path):
    area_registry.clear()
    obj_registry.clear()

    content = (
        "#AREA\n"
        "stats_obj.are~\n"
        "Stats Object~\n"
        "Credits~\n"
        "2 2\n"
        "#OBJECTS\n"
        "#2\n"
        "stat sword~\n"
        "a stat sword~\n"
        "A stat sword rests here.~\n"
        "steel~\n"
        "weapon ABC AB\n"
        "0 0 0 0 0\n"
        "12 8 250 G\n"
        "#0\n"
        "#$\n"
    )

    path = tmp_path / "stats_obj.are"
    path.write_text(content, encoding="latin-1")

    load_area_file(str(path))

    obj = obj_registry[2]
    assert obj.level == 12
    assert obj.weight == 8
    assert obj.cost == 250
    assert obj.condition == 90

    area_registry.clear()
    obj_registry.clear()


def test_object_extra_and_wear_flags_loaded(tmp_path):
    area_registry.clear()
    obj_registry.clear()

    content = (
        "#AREA\n"
        "flag_bits.are~\n"
        "Flag Bits~\n"
        "Credits~\n"
        "1 1\n"
        "#OBJECTS\n"
        "#5\n"
        "flag blade~\n"
        "a flag blade~\n"
        "A blade glows here.~\n"
        "steel~\n"
        "weapon BI AN\n"
        "0 0 0 0 0\n"
        "10 5 100 P\n"
        "#0\n"
        "#$\n"
    )

    path = tmp_path / "flag_bits.are"
    path.write_text(content, encoding="latin-1")

    load_area_file(str(path))

    obj = obj_registry[5]
    expected_extra = int(convert_flags_from_letters("BI", ExtraFlag))
    expected_wear = int(convert_flags_from_letters("AN", WearFlag))
    assert obj.extra_flags == expected_extra
    assert obj.wear_flags == expected_wear

    runtime = spawn_object(5)
    assert runtime is not None
    assert runtime.extra_flags == expected_extra
    assert runtime.wear_flags == expected_wear

    area_registry.clear()
    obj_registry.clear()


def test_mob_and_object_new_format_marked_true(tmp_path):
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()

    content = (
        "#AREA\n"
        "new_format.are~\n"
        "New Format Test~\n"
        "Credits~\n"
        "1 1\n"
        "#MOBILES\n"
        "#10\n"
        "test mob~\n"
        "a test mob~\n"
        "A test mob stands here.~\n"
        "A simple description.~\n"
        "human~\n"
        "0 0 0 0\n"
        "1 0 0 1d1+0 1d1+0 1d1+0 beating\n"
        "0 0 0 0\n"
        "0 0 0 0\n"
        "standing standing neutral 0\n"
        "0 0 medium 0\n"
        "#0\n"
        "#OBJECTS\n"
        "#20\n"
        "test blade~\n"
        "a test blade~\n"
        "A test blade rests here.~\n"
        "iron~\n"
        "weapon 0 0\n"
        "0 0 0 0 0\n"
        "1 1 0 P\n"
        "#0\n"
        "#$\n"
    )

    path = tmp_path / "new_format.are"
    path.write_text(content, encoding="latin-1")

    load_area_file(str(path))

    mob = mob_registry[10]
    obj = obj_registry[20]

    assert mob.new_format is True
    assert obj.new_format is True

    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()


def test_object_weapon_and_wand_values_match_rom(tmp_path):
    area_registry.clear()
    obj_registry.clear()

    content = (
        "#AREA\n"
        "value_items.are~\n"
        "Value Items~\n"
        "Credits~\n"
        "10 20\n"
        "#OBJECTS\n"
        "#10\n"
        "practice blade~\n"
        "a practice blade~\n"
        "A practice blade rests here.~\n"
        "steel~\n"
        "weapon 0 0\n"
        "sword 3 5 cleave AB\n"
        "35 10 150 G\n"
        "#11\n"
        "trainer wand~\n"
        "a trainer's wand~\n"
        "A training wand has been dropped here.~\n"
        "oak~\n"
        "wand 0 0\n"
        "5 5 20 'magic missile' 0\n"
        "25 2 350 P\n"
        "#0\n"
        "#$\n"
    )

    path = tmp_path / "value_items.are"
    path.write_text(content, encoding="latin-1")

    load_area_file(str(path))

    blade = obj_registry[10]
    assert blade.value[0] == int(WeaponType.SWORD)
    assert blade.value[1] == 3
    assert blade.value[2] == 5
    assert blade.value[3] == attack_lookup("cleave")
    assert blade.value[4] == int(WeaponFlag.FLAMING | WeaponFlag.FROST)

    wand = obj_registry[11]
    assert wand.value[0] == 5
    assert wand.value[1] == 5
    assert wand.value[2] == 20
    magic_index = ROM_SKILL_NAMES_BY_INDEX.index("magic missile")
    assert wand.value[3] == magic_index
    assert wand.value[4] == 0

    area_registry.clear()
    obj_registry.clear()


def test_object_potion_and_container_values(tmp_path):
    area_registry.clear()
    obj_registry.clear()

    content = (
        "#AREA\n"
        "value_more.are~\n"
        "Value More~\n"
        "Credits~\n"
        "30 40\n"
        "#OBJECTS\n"
        "#20\n"
        "detect potion~\n"
        "a potion of detection~\n"
        "A shimmering potion sits here.~\n"
        "glass~\n"
        "potion 0 0\n"
        "12 'detect invis' 'cure light' 'cure serious' 'cure critical'\n"
        "0 5 220 P\n"
        "#21\n"
        "bottle brew~\n"
        "a bottle of brew~\n"
        "A glass bottle lies here.~\n"
        "glass~\n"
        "drink 0 0\n"
        "12 12 'firebreather' 0 0\n"
        "0 6 30 P\n"
        "#22\n"
        "small chest~\n"
        "a small training chest~\n"
        "A training chest sits here.~\n"
        "iron~\n"
        "container 0 0\n"
        "100 AB 5 10 0\n"
        "0 20 100 P\n"
        "#0\n"
        "#$\n"
    )

    path = tmp_path / "value_more.are"
    path.write_text(content, encoding="latin-1")

    load_area_file(str(path))

    potion = obj_registry[20]
    assert potion.value[0] == 12
    detect_index = ROM_SKILL_NAMES_BY_INDEX.index("detect invis")
    cure_light = ROM_SKILL_NAMES_BY_INDEX.index("cure light")
    cure_serious = ROM_SKILL_NAMES_BY_INDEX.index("cure serious")
    cure_critical = ROM_SKILL_NAMES_BY_INDEX.index("cure critical")
    assert potion.value[1] == detect_index
    assert potion.value[2] == cure_light
    assert potion.value[3] == cure_serious
    assert potion.value[4] == cure_critical

    bottle = obj_registry[21]
    assert bottle.value[0] == 12
    assert bottle.value[1] == 12
    firebreather_index = next(
        idx for idx, liquid in enumerate(LIQUID_TABLE) if liquid.name == "firebreather"
    )
    assert bottle.value[2] == firebreather_index
    assert bottle.value[3] == 0
    assert bottle.value[4] == 0

    chest = obj_registry[22]
    expected_flags = int(ContainerFlag.CLOSEABLE | ContainerFlag.PICKPROOF)
    assert chest.value[0] == 100
    assert chest.value[1] == expected_flags
    assert chest.value[2] == 5
    assert chest.value[3] == 10
    assert chest.value[4] == 0

    area_registry.clear()
    obj_registry.clear()


def test_optional_room_fields_roundtrip(tmp_path):
    clear_registries()
    data = convert_area("area/midgaard.are")

    temple_room = next(room for room in data["rooms"] if room["id"] == 3054)
    assert temple_room["heal_rate"] == 110
    assert temple_room["mana_rate"] == 110

    out_file = tmp_path / "midgaard.json"
    out_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    area_registry.clear()
    room_registry.clear()
    area = load_area_from_json(str(out_file))

    loaded_room = room_registry[3054]
    assert loaded_room.heal_rate == 110
    assert loaded_room.mana_rate == 110

    assert area.age == 15
    assert area.nplayer == 0
    assert area.empty is False

    area_registry.clear()
    room_registry.clear()


def test_convert_area_preserves_clan_and_owner(tmp_path):
    content = (
        "#AREA\n"
        "tmp.are~\n"
        "Tmp Area~\n"
        "Builder~\n"
        "0 0\n"
        "#ROOMS\n"
        "#100\n"
        "Clan Room~\n"
        "A clan-owned room.\n"
        "~\n"
        "0 0 0\n"
        "H 150 M 90\n"
        "C test_clan~\n"
        "O test_owner~\n"
        "S\n"
        "#0\n"
        "#$\n"
    )
    area_path = tmp_path / "tmp.are"
    area_path.write_text(content, encoding="latin-1")

    clear_registries()
    data = convert_area(str(area_path))
    room_data = data["rooms"][0]

    assert room_data["heal_rate"] == 150
    assert room_data["mana_rate"] == 90
    assert room_data["clan"] == "test_clan"
    assert room_data["owner"] == "test_owner"

    json_path = tmp_path / "tmp.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    area_registry.clear()
    room_registry.clear()
    load_area_from_json(str(json_path))

    loaded_room = room_registry[100]
    assert loaded_room.heal_rate == 150
    assert loaded_room.mana_rate == 90
    assert loaded_room.clan == "test_clan"
    assert loaded_room.owner == "test_owner"

    area_registry.clear()
    room_registry.clear()


def test_convert_area_preserves_mobprogs(tmp_path):
    area_registry.clear()
    room_registry.clear()
    mob_registry.clear()
    clear_registered_programs()

    content = (
        "#AREA\n"
        "mprog_json.are~\n"
        "MobProg JSON Test~\n"
        "Credits~\n"
        "1 1\n"
        "#MOBILES\n"
        "#1\n"
        "testmob~\n"
        "A test mob~\n"
        "Scripted mob.~\n"
        "Simple description.~\n"
        "human~\n"
        "0 0 0 0\n"
        "1 0 0 1d1+0 1d1+0 1d1+0 beating\n"
        "0 0 0 0\n"
        "0 0 0 0\n"
        "standing standing neutral 0\n"
        "0 0 medium 0\n"
        "M GREET 6000 hello json~\n"
        "#0\n"
        "#MOBPROGS\n"
        "#6000\n"
        "say Hello JSON!\n"
        "~\n"
        "#0\n"
        "#$\n"
    )
    area_path = tmp_path / "mprog_json.are"
    area_path.write_text(content, encoding="latin-1")

    clear_registries()
    data = convert_area(str(area_path))
    assert "mob_programs" in data
    entry = data["mob_programs"][0]
    assert entry["vnum"] == 6000
    assert entry["code"] == "say Hello JSON!"
    assignment = entry["assignments"][0]
    assert assignment["mob_vnum"] == 1
    assert assignment["trigger"] == "GREET"
    assert assignment["phrase"] == "hello json"

    json_path = tmp_path / "mprog_json.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    clear_registries()
    load_area_from_json(str(json_path))

    mob = mob_registry[1]
    assert mob.mprogs
    program = mob.mprogs[0]
    assert program.vnum == 6000
    assert program.trig_phrase == "hello json"
    assert program.trig_type == int(Trigger.GREET)
    assert program.code == "say Hello JSON!"
    assert get_registered_program(6000) is program

    area_registry.clear()
    room_registry.clear()
    mob_registry.clear()
    clear_registered_programs()


def test_json_loader_applies_defaults_and_law_flag(tmp_path):
    clear_registries()
    data = convert_area("area/midgaard.are")
    json_path = tmp_path / "midgaard.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    area_registry.clear()
    room_registry.clear()
    load_area_from_json(str(json_path))

    room = room_registry[3001]
    assert room.heal_rate == 100
    assert room.mana_rate == 100
    assert room.clan == 0
    assert room.owner == ""
    assert room.room_flags & RoomFlag.ROOM_LAW

    area_registry.clear()
    room_registry.clear()


def test_midgaard_reset_validation():
    clear_registries()
    area = load_area_file("area/midgaard.are")
    errors = validate_resets(area)
    assert errors == []


def test_json_loader_populates_room_resets():
    clear_registries()
    area = load_area_from_json("data/areas/midgaard.json")
    room = room_registry[3001]
    assert room.resets, "Expected JSON load to attach resets to the owning room"
    guardian_reset = next(
        (reset for reset in area.resets if reset.command == "M" and reset.arg3 == 3001),
        None,
    )
    assert guardian_reset is not None
    assert guardian_reset in room.resets


def test_json_loader_parses_room_flag_letters(tmp_path):
    clear_registries()

    data = {
        "area": {
            "vnum": 501,
            "name": "Flag Letters",
            "filename": "flag_letters",
            "min_level": 1,
            "max_level": 1,
            "builders": "",
            "credits": "",
            "min_vnum": 6000,
            "max_vnum": 6001,
            "area_flags": 0,
            "security": 9,
        },
        "rooms": [
            {
                "id": 6000,
                "name": "Letter Room",
                "description": "",
                "sector_type": "inside",
                "flags": "AD",
                "exits": {"east": {"to_room": 6001, "flags": "0", "key": 0}},
            },
            {
                "id": 6001,
                "name": "Next",
                "description": "",
                "sector_type": "inside",
                "flags": 0,
                "exits": {},
            },
        ],
        "mobs": [],
        "objects": [],
        "mob_programs": [],
    }

    json_path = tmp_path / "flag_letters.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    load_area_from_json(str(json_path))

    room = room_registry[6000]
    expected_flags = int(RoomFlag.ROOM_DARK | RoomFlag.ROOM_INDOORS)
    assert room.room_flags == expected_flags

    area_registry.clear()
    room_registry.clear()


def test_json_loader_parses_extended_flag_letters(tmp_path):
    area_registry.clear()
    room_registry.clear()

    data = {
        "name": "Extended Flags",
        "vnum_range": {"min": 7000, "max": 7001},
        "builders": [],
        "rooms": [
            {
                "id": 7000,
                "name": "Arena",
                "description": "",
                "sector_type": "inside",
                "flags": "aB",
                "exits": {"east": {"to_room": 7001, "flags": "a", "key": 0}},
            },
            {
                "id": 7001,
                "name": "Spillway",
                "description": "",
                "sector_type": "inside",
                "flags": "0",
                "exits": {},
            },
        ],
        "mobs": [],
        "objects": [],
        "mob_programs": [],
    }

    json_path = tmp_path / "extended_flags.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    load_area_from_json(str(json_path))

    room = room_registry[7000]
    expected_room_flags = (1 << 26) | (1 << 1)
    assert room.room_flags == expected_room_flags

    exit_obj = room.exits[Direction.EAST.value]
    assert exit_obj is not None
    expected_exit_flags = 1 << 26
    assert exit_obj.exit_info == expected_exit_flags
    assert exit_obj.rs_flags == expected_exit_flags

    area_registry.clear()
    room_registry.clear()


def test_json_loader_links_exit_targets(tmp_path):
    clear_registries()

    north_flags = int(EX_ISDOOR | EX_CLOSED)
    south_flags = int(EX_ISDOOR | EX_PICKPROOF)

    data = {
        "area": {
            "vnum": 200,
            "name": "Link Test",
            "filename": "link_test",
            "min_level": 1,
            "max_level": 1,
            "builders": "",
            "credits": "",
            "min_vnum": 100,
            "max_vnum": 102,
            "area_flags": 0,
            "security": 9,
        },
        "rooms": [
            {
                "id": 100,
                "name": "North Room",
                "description": "",
                "sector_type": "inside",
                "flags": 0,
                "exits": {
                    "north": {"to_room": 101, "flags": north_flags, "description": "", "keyword": "door"}
                },
            },
            {
                "id": 101,
                "name": "South Room",
                "description": "",
                "sector_type": "inside",
                "flags": 0,
                "exits": {
                    "south": {"to_room": 100, "flags": south_flags, "description": "", "keyword": "door"}
                },
            },
            {
                "id": 102,
                "name": "Dead End",
                "description": "",
                "sector_type": "inside",
                "flags": 0,
                "exits": {},
            },
        ],
        "mobs": [],
        "objects": [],
        "resets": [],
    }

    json_path = tmp_path / "link_area.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    load_area_from_json(str(json_path))

    north_room = room_registry[100]
    south_room = room_registry[101]
    dead_end = room_registry[102]

    north_exit = north_room.exits[Direction.NORTH.value]
    south_exit = south_room.exits[Direction.SOUTH.value]

    assert north_exit is not None
    assert south_exit is not None
    assert north_exit.to_room is south_room
    assert south_exit.to_room is north_room
    assert north_exit.rs_flags == north_flags
    assert south_exit.rs_flags == south_flags
    assert dead_end.room_flags & RoomFlag.ROOM_NO_MOB

    clear_registries()


def test_json_loader_preserves_one_way_exit_flags(tmp_path):
    clear_registries()

    door_flags = int(EX_ISDOOR | EX_CLOSED)

    data = {
        "area": {
            "vnum": 300,
            "name": "One Way Door",
            "filename": "one_way",
            "min_level": 1,
            "max_level": 1,
            "builders": "",
            "credits": "",
            "min_vnum": 400,
            "max_vnum": 401,
            "area_flags": 0,
            "security": 9,
        },
        "rooms": [
            {
                "id": 400,
                "name": "Door Side",
                "description": "",
                "sector_type": "inside",
                "flags": 0,
                "exits": {
                    "north": {"to_room": 401, "flags": door_flags, "description": "", "keyword": "door"}
                },
            },
            {
                "id": 401,
                "name": "Open Side",
                "description": "",
                "sector_type": "inside",
                "flags": 0,
                "exits": {
                    "south": {"to_room": 400, "flags": 0, "description": "", "keyword": ""}
                },
            },
        ],
        "mobs": [],
        "objects": [],
        "resets": [],
    }

    json_path = tmp_path / "one_way.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    load_area_from_json(str(json_path))

    door_room = room_registry[400]
    open_room = room_registry[401]

    north_exit = door_room.exits[Direction.NORTH.value]
    south_exit = open_room.exits[Direction.SOUTH.value]

    assert north_exit is not None
    assert south_exit is not None
    assert north_exit.rs_flags == door_flags
    assert south_exit.rs_flags == 0

    clear_registries()


def test_json_loader_sets_exit_orig_door():
    clear_registries()

    area_registry.clear()
    room_registry.clear()
    load_area_from_json("data/areas/midgaard.json")

    for room in room_registry.values():
        for index, exit_obj in enumerate(room.exits):
            if exit_obj is not None:
                assert exit_obj.orig_door == index

    clear_registries()


def test_json_loader_applies_specials_to_mobs(tmp_path):
    clear_registries()

    data = {
        "area": {
            "vnum": 1,
            "name": "Spec Area",
            "filename": "spec",
            "min_level": 1,
            "max_level": 1,
            "builders": "",
            "credits": "",
            "min_vnum": 1,
            "max_vnum": 1,
            "area_flags": 0,
            "security": 9,
        },
        "rooms": [],
        "mobs": [
            {
                "id": 4200,
                "name": "Spec Mob",
                "player_name": "spec mob",
                "long_description": "",
                "description": "",
                "race": "human",
                "act_flags": "AIS",
                "affected_by": "",
                "alignment": 0,
                "group": 0,
                "level": 10,
            }
        ],
        "objects": [],
        "mob_programs": [],
        "specials": [
            {"mob_vnum": 4200, "spec": "spec_breath_fire"},
        ],
    }

    json_path = tmp_path / "spec_area.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    load_area_from_json(str(json_path))

    proto = mob_registry.get(4200)
    assert proto is not None
    assert (proto.spec_fun or "").lower() == "spec_breath_fire"

    clear_registries()
