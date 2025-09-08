from mud.world import initialize_world, create_test_character
from mud.spawning.obj_spawner import spawn_object
from mud.commands import process_command
from mud.registry import room_registry


def test_process_command_sequence():
    initialize_world('area/area.lst')
    char = create_test_character('Tester', 3001)
    sword = spawn_object(3022)
    assert sword is not None
    char.room.add_object(sword)

    out1 = process_command(char, 'look')
    assert 'Temple' in out1

    out2 = process_command(char, 'get sword')
    assert 'pick up' in out2
    assert sword in char.inventory
    assert sword not in char.room.contents

    out3 = process_command(char, 'north')
    assert 'You walk north' in out3
    north_room = room_registry[3054]
    assert char.room is north_room

    other = create_test_character('Other', north_room.vnum)
    out4 = process_command(char, 'say hello')
    assert out4 == "You say, 'hello'"
    assert f"{char.name} says, 'hello'" in other.messages


def test_equipment_command():
    initialize_world('area/area.lst')
    char = create_test_character('Tester', 3001)
    sword = spawn_object(3022)
    assert sword is not None
    char.add_object(sword)
    char.equip_object(sword, 'wield')
    out = process_command(char, 'equipment')
    assert 'You are using' in out
    assert 'wield' in out


def test_abbreviations_and_quotes():
    initialize_world('area/area.lst')
    char = create_test_character('Tester', 3001)

    out1 = process_command(char, 'l')
    assert 'Temple' in out1

    out2 = process_command(char, 'n')
    assert 'You walk north' in out2

    out3 = process_command(char, 'say "hello world"')
    assert out3 == "You say, 'hello world'"


def test_scan_lists_adjacent_characters():
    initialize_world('area/area.lst')
    # Place player in temple, another to the north
    char = create_test_character('Scanner', 3001)
    north_room = room_registry[3054]
    other = create_test_character('Target', north_room.vnum)

    out = process_command(char, 'scan')
    assert 'You scan for life signs' in out
    # Should list Target under north (possibly with other names)
    assert 'north:' in out and 'Target' in out


def test_alias_create_expand_and_unalias():
    initialize_world('area/area.lst')
    char = create_test_character('AliasUser', 3001)

    # Initially no aliases
    out0 = process_command(char, 'alias')
    assert 'No aliases' in out0

    # Create alias and use it
    set_out = process_command(char, 'alias lk look')
    assert 'Alias set: lk -> look' in set_out
    out1 = process_command(char, 'lk')
    assert 'Temple' in out1  # expanded to look

    # Remove alias
    rm_out = process_command(char, 'unalias lk')
    assert 'Removed alias' in rm_out
    out2 = process_command(char, 'lk')
    assert out2 == 'Huh?'


def test_alias_persists_in_save_load(tmp_path, monkeypatch):
    initialize_world('area/area.lst')
    char = create_test_character('AliasPersist', 3001)
    process_command(char, 'alias lk look')

    # Redirect players dir to tmp
    from mud import persistence as p
    monkeypatch.setattr(p, 'PLAYERS_DIR', tmp_path)
    p.save_character(char)

    loaded = p.load_character('AliasPersist')
    assert loaded is not None
    out = process_command(loaded, 'lk')
    assert 'Temple' in out
