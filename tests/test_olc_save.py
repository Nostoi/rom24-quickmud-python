"""
Tests for @asave command - OLC area persistence.

Mirroring ROM src/olc_save.c:918-1134 (do_asave function).
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import shutil

from mud.commands import process_command
from mud.models.area import Area
from mud.models.room import Room, Exit, ExtraDescr
from mud.models.constants import LEVEL_HERO
from mud.net.session import Session
from mud.registry import area_registry, room_registry
from mud.world import create_test_character, initialize_world


def setup_module(module):
    initialize_world("area/area.lst")


def _attach_session(char):
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    return session


def test_asave_requires_hero_trust():
    mortal = create_test_character("Mortal", 3001)
    mortal.level = 10
    mortal.is_admin = False
    session = _attach_session(mortal)

    result = process_command(mortal, "@asave changed")
    assert "huh" in result.lower() or "what" in result.lower()


def test_asave_no_args_shows_syntax():
    hero = create_test_character("Hero", 3001)
    hero.level = LEVEL_HERO
    hero.is_admin = True
    hero.pcdata.security = 9
    session = _attach_session(hero)

    result = process_command(hero, "@asave")
    assert "syntax" in result.lower()
    assert "asave <vnum>" in result.lower()
    assert "asave changed" in result.lower()
    assert "asave world" in result.lower()
    assert "asave area" in result.lower()
    assert "asave list" in result.lower()


def test_asave_invalid_arg():
    hero = create_test_character("Hero", 3001)
    hero.level = LEVEL_HERO
    hero.is_admin = True
    hero.pcdata.security = 9
    session = _attach_session(hero)

    result = process_command(hero, "@asave foobar")
    assert "invalid" in result.lower()


def test_asave_nonexistent_vnum():
    hero = create_test_character("Hero", 3001)
    hero.level = LEVEL_HERO
    hero.is_admin = True
    hero.pcdata.security = 9
    session = _attach_session(hero)

    result = process_command(hero, "@asave 99999")
    assert "does not exist" in result.lower()


def test_asave_vnum_requires_builder_rights():
    hero = create_test_character("Hero", 3001)
    hero.level = LEVEL_HERO
    hero.is_admin = True
    hero.room.area.security = 9
    hero.pcdata.security = 0
    session = _attach_session(hero)

    area_vnum = hero.room.area.vnum
    result = process_command(hero, f"@asave {area_vnum}")
    assert "not a builder" in result.lower()


def test_asave_vnum_saves_area(tmp_path):
    hero = create_test_character("Hero", 3001)
    hero.level = LEVEL_HERO
    hero.is_admin = True
    hero.room.area.security = 1
    hero.pcdata.security = 9
    session = _attach_session(hero)

    process_command(hero, "@redit")
    process_command(hero, 'name "Modified Room"')
    process_command(hero, 'desc "This room was modified by test"')
    process_command(hero, "done")

    assert hero.room.area.changed is True

    import mud.olc.save

    original_dir = "data/areas"
    test_output = str(tmp_path / "test_areas")
    Path(test_output).mkdir(parents=True, exist_ok=True)

    backup_save = mud.olc.save.save_area_to_json

    def patched_save(area, output_dir="data/areas"):
        return backup_save(area, output_dir=test_output)

    mud.olc.save.save_area_to_json = patched_save

    try:
        area_vnum = hero.room.area.vnum
        result = process_command(hero, f"@asave {area_vnum}")

        assert "saved" in result.lower()
        assert hero.room.area.changed is False

        saved_files = list(Path(test_output).glob("*.json"))
        assert len(saved_files) > 0
    finally:
        mud.olc.save.save_area_to_json = backup_save


def test_asave_list_creates_area_lst(tmp_path):
    hero = create_test_character("Hero", 3001)
    hero.level = LEVEL_HERO
    hero.is_admin = True
    hero.pcdata.security = 9
    session = _attach_session(hero)

    import mud.olc.save

    test_output = str(tmp_path / "area.lst")

    backup_save = mud.olc.save.save_area_list

    def patched_save(output_file="data/areas/area.lst"):
        return backup_save(output_file=test_output)

    mud.olc.save.save_area_list = patched_save

    try:
        result = process_command(hero, "@asave list")

        assert "saved" in result.lower() or "area list" in result.lower()
        assert Path(test_output).exists()

        content = Path(test_output).read_text()
        assert "$" in content
    finally:
        mud.olc.save.save_area_list = backup_save


def test_asave_area_requires_active_edit_session():
    hero = create_test_character("Hero", 3001)
    hero.level = LEVEL_HERO
    hero.is_admin = True
    hero.pcdata.security = 9
    session = _attach_session(hero)

    result = process_command(hero, "@asave area")
    assert "not editing" in result.lower()


def test_asave_area_saves_currently_edited_area(tmp_path):
    hero = create_test_character("Hero", 3001)
    hero.level = LEVEL_HERO
    hero.is_admin = True
    hero.room.area.security = 1
    hero.pcdata.security = 9
    session = _attach_session(hero)

    process_command(hero, "@redit")
    process_command(hero, 'name "Test Area Save"')

    assert hero.room.area.changed is True

    import mud.olc.save

    test_output = str(tmp_path / "test_areas")
    Path(test_output).mkdir(parents=True, exist_ok=True)

    backup_save = mud.olc.save.save_area_to_json

    def patched_save(area, output_dir="data/areas"):
        return backup_save(area, output_dir=test_output)

    mud.olc.save.save_area_to_json = patched_save

    try:
        result = process_command(hero, "@asave area")

        assert "saved" in result.lower()
        assert hero.room.area.changed is False
    finally:
        mud.olc.save.save_area_to_json = backup_save


def test_asave_changed_saves_only_modified_areas(tmp_path):
    hero = create_test_character("Hero", 3001)
    hero.level = LEVEL_HERO
    hero.is_admin = True
    hero.pcdata.security = 9
    session = _attach_session(hero)

    for area in area_registry.values():
        area.changed = False

    hero.room.area.security = 1
    process_command(hero, "@redit")
    process_command(hero, 'name "Changed Room"')
    process_command(hero, "done")

    assert hero.room.area.changed is True

    import mud.olc.save

    test_output = str(tmp_path / "test_areas")
    Path(test_output).mkdir(parents=True, exist_ok=True)

    backup_save = mud.olc.save.save_area_to_json
    saved_areas = []

    def patched_save(area, output_dir="data/areas"):
        saved_areas.append(area)
        return backup_save(area, output_dir=test_output)

    mud.olc.save.save_area_to_json = patched_save

    try:
        result = process_command(hero, "@asave changed")

        assert "saved zones" in result.lower() or "saved" in result.lower()
        assert len(saved_areas) >= 1
        assert hero.room.area in saved_areas
    finally:
        mud.olc.save.save_area_to_json = backup_save


def test_asave_changed_no_changes_reports_none():
    hero = create_test_character("Hero", 3001)
    hero.level = LEVEL_HERO
    hero.is_admin = True
    hero.pcdata.security = 9
    session = _attach_session(hero)

    for area in area_registry.values():
        area.changed = False

    result = process_command(hero, "@asave changed")
    assert "no changed" in result.lower() or "none" in result.lower()


def test_asave_world_saves_all_authorized_areas(tmp_path):
    hero = create_test_character("Hero", 3001)
    hero.level = LEVEL_HERO
    hero.is_admin = True
    hero.pcdata.security = 9
    session = _attach_session(hero)

    import mud.olc.save

    test_output = str(tmp_path / "test_areas")
    Path(test_output).mkdir(parents=True, exist_ok=True)

    backup_save = mud.olc.save.save_area_to_json
    saved_count = []

    def patched_save(area, output_dir="data/areas"):
        saved_count.append(area)
        return backup_save(area, output_dir=test_output)

    mud.olc.save.save_area_to_json = patched_save

    try:
        result = process_command(hero, "@asave world")

        assert "saved the world" in result.lower() or "saved" in result.lower()
        assert len(saved_count) > 0
    finally:
        mud.olc.save.save_area_to_json = backup_save


def test_asave_preserves_room_data_during_save(tmp_path):
    hero = create_test_character("Hero", 3001)
    hero.level = LEVEL_HERO
    hero.is_admin = True
    hero.room.area.security = 1
    hero.pcdata.security = 9
    session = _attach_session(hero)

    process_command(hero, "@redit")
    process_command(hero, 'name "Complex Test Room"')
    process_command(hero, 'desc "A room with complex data"')
    process_command(hero, "sector forest")
    process_command(hero, "heal 150")
    process_command(hero, "mana 75")
    process_command(hero, "ed add testkey")
    process_command(hero, 'ed desc testkey "Test extra description"')
    process_command(hero, "north create 3002")
    process_command(hero, "north flags door closed")
    process_command(hero, "done")

    import mud.olc.save

    test_output = str(tmp_path / "test_areas")
    Path(test_output).mkdir(parents=True, exist_ok=True)

    backup_save = mud.olc.save.save_area_to_json

    def patched_save(area, output_dir="data/areas"):
        return backup_save(area, output_dir=test_output)

    mud.olc.save.save_area_to_json = patched_save

    try:
        area_vnum = hero.room.area.vnum
        process_command(hero, f"@asave {area_vnum}")

        saved_files = list(Path(test_output).glob("*.json"))
        assert len(saved_files) > 0

        with open(saved_files[0], "r") as f:
            data = json.load(f)

        assert "rooms" in data
        test_room = next((r for r in data["rooms"] if r["id"] == hero.room.vnum), None)
        assert test_room is not None
        assert test_room["name"] == "Complex Test Room"
        assert "complex data" in test_room["description"]
        assert test_room["sector_type"] == "forest"
        assert test_room["heal_rate"] == 150
        assert test_room["mana_rate"] == 75
        assert len(test_room["extra_descriptions"]) >= 1
        assert "north" in test_room["exits"]
    finally:
        mud.olc.save.save_area_to_json = backup_save


def test_roundtrip_edit_save_reload_verify(tmp_path):
    from mud.loaders.json_loader import load_area_from_json
    from mud.models.constants import Direction, EX_ISDOOR, EX_CLOSED, EX_LOCKED
    
    hero = create_test_character("Hero", 3001)
    hero.level = LEVEL_HERO
    hero.is_admin = True
    hero.room.area.security = 1
    hero.pcdata.security = 9
    session = _attach_session(hero)

    original_vnum = hero.room.vnum
    original_area_vnum = hero.room.area.vnum
    
    process_command(hero, "@redit")
    process_command(hero, 'name "Roundtrip Test Room"')
    process_command(hero, 'desc "This room tests full save/load cycle"')
    process_command(hero, "sector desert")
    process_command(hero, "heal 200")
    process_command(hero, "mana 50")
    process_command(hero, "room safe dark")
    process_command(hero, 'owner TestOwner')
    process_command(hero, 'ed add sign')
    process_command(hero, 'ed desc sign "A weathered sign hangs here"')
    process_command(hero, "north create 3002")
    process_command(hero, "north key 1234")
    process_command(hero, 'north keyword "door gate"')
    process_command(hero, 'north desc "A sturdy door blocks the way"')
    process_command(hero, "north flags door closed locked")
    process_command(hero, "done")

    import mud.olc.save
    test_output = str(tmp_path / "test_areas")
    Path(test_output).mkdir(parents=True, exist_ok=True)
    
    backup_save = mud.olc.save.save_area_to_json
    
    def patched_save(area, output_dir="data/areas"):
        return backup_save(area, output_dir=test_output)
    
    mud.olc.save.save_area_to_json = patched_save

    try:
        process_command(hero, f"@asave {original_area_vnum}")
        
        saved_files = list(Path(test_output).glob("*.json"))
        assert len(saved_files) > 0
        json_file = saved_files[0]
        
        with open(json_file, 'r') as f:
            saved_data = json.load(f)
        
        room_data = next((r for r in saved_data["rooms"] if r["id"] == original_vnum), None)
        assert room_data is not None
        
        assert room_data["name"] == "Roundtrip Test Room"
        assert "save/load cycle" in room_data["description"]
        assert room_data["sector_type"] == "desert"
        assert room_data["heal_rate"] == 200
        assert room_data["mana_rate"] == 50
        assert room_data["owner"] == "TestOwner"
        
        room_flags = room_data["flags"]
        from mud.models.constants import RoomFlag
        assert room_flags & int(RoomFlag.ROOM_SAFE)
        assert room_flags & int(RoomFlag.ROOM_DARK)
        
        extras = room_data["extra_descriptions"]
        assert len(extras) >= 1
        sign_extra = next((e for e in extras if e["keyword"] == "sign"), None)
        assert sign_extra is not None
        assert "weathered" in sign_extra["description"]
        
        exits = room_data["exits"]
        assert "north" in exits
        north_exit = exits["north"]
        assert north_exit["to_room"] == 3002
        assert north_exit["key"] == 1234
        assert north_exit["keyword"] == "door gate"
        assert "sturdy door" in north_exit["description"]
        
        exit_flags = int(north_exit["flags"])
        assert exit_flags & EX_ISDOOR
        assert exit_flags & EX_CLOSED
        assert exit_flags & EX_LOCKED
        
        saved_area = load_area_from_json(json_file)
        assert saved_area is not None
        assert saved_area.name == saved_data["name"]
        
        reloaded_room = None
        for vnum in range(saved_area.min_vnum, saved_area.max_vnum + 1):
            if vnum == original_vnum:
                reloaded_room = room_registry.get(vnum)
                break
        
        if reloaded_room:
            assert reloaded_room.name == "Roundtrip Test Room"
            assert "save/load cycle" in (reloaded_room.description or "")
            assert reloaded_room.heal_rate == 200
            assert reloaded_room.mana_rate == 50
            
    finally:
        mud.olc.save.save_area_to_json = backup_save
