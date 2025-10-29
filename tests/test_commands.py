from mud.commands import process_command
from mud.models.constants import AffectFlag, PlayerFlag, Position
from mud.registry import room_registry
from mud.spawning.obj_spawner import spawn_object
from mud.world import create_test_character, initialize_world


def test_process_command_sequence(movable_char_factory, place_object_factory):
    initialize_world("area/area.lst")
    char = movable_char_factory("Tester", 3001)
    sword = place_object_factory(room_vnum=3001, vnum=3022)

    out1 = process_command(char, "look")
    assert "Temple" in out1

    out2 = process_command(char, "get sword")
    assert "pick up" in out2
    assert sword in char.inventory
    assert sword not in char.room.contents

    out3 = process_command(char, "north")
    assert "You walk north" in out3
    north_room = room_registry[3054]
    assert char.room is north_room

    other = create_test_character("Other", north_room.vnum)
    out4 = process_command(char, "say hello")
    assert out4 == "You say, 'hello'"
    assert f"{char.name} says, 'hello'" in other.messages


def test_equipment_command(movable_char_factory):
    initialize_world("area/area.lst")
    char = movable_char_factory("Tester", 3001)
    sword = spawn_object(3022)
    assert sword is not None
    char.add_object(sword)
    char.equip_object(sword, "wield")
    out = process_command(char, "equipment")
    assert "You are using" in out
    assert "wield" in out


def test_abbreviations_and_quotes(movable_char_factory):
    initialize_world("area/area.lst")
    char = movable_char_factory("Tester", 3001)

    out1 = process_command(char, "l")
    assert "Temple" in out1

    out2 = process_command(char, "n")
    assert "You walk north" in out2

    out3 = process_command(char, 'say "hello world"')
    assert out3 == "You say, 'hello world'"


def test_abbrev_skips_inaccessible_command():
    initialize_world("area/area.lst")
    char = create_test_character("Novice", 3001)

    explicit = process_command(char, "imc")
    abbreviated = process_command(char, "im")

    assert abbreviated == explicit


def test_apostrophe_alias_routes_to_say():
    initialize_world("area/area.lst")
    speaker = create_test_character("Speaker", 3001)
    listener = create_test_character("Listener", 3001)

    out = process_command(speaker, "'hello there")
    assert out == "You say, 'hello there'"
    assert f"{speaker.name} says, 'hello there'" in listener.messages


def test_punctuation_inputs_do_not_raise_value_error():
    initialize_world("area/area.lst")
    speaker = create_test_character("SpeakerTwo", 3001)

    out = process_command(speaker, "'   spaced words")
    assert out == "You say, 'spaced words'"

    prompt = process_command(speaker, "'")
    assert prompt == "Say what?"


def test_scan_lists_adjacent_characters_rom_style():
    initialize_world("area/area.lst")
    # Place player in temple, another to the north
    char = create_test_character("Scanner", 3001)
    north_room = room_registry[3054]
    create_test_character("Target", north_room.vnum)

    out = process_command(char, "scan")
    # ROM-style header
    assert "Looking around you see:" in out
    # Depth 1 phrasing
    assert "Target, nearby to the north." in out


def test_scan_directional_depth_rom_style():
    initialize_world("area/area.lst")
    char = create_test_character("Scanner", 3001)
    north_room = room_registry[3054]
    create_test_character("Target", north_room.vnum)

    out = process_command(char, "scan north")
    assert "Looking north you see:" in out
    assert "Target, nearby to the north." in out


def test_scan_hides_invisible_targets():
    initialize_world("area/area.lst")
    char = create_test_character("Watcher", 3001)
    north_room = room_registry[3054]
    create_test_character("Visible", north_room.vnum)
    hidden = create_test_character("Shadow", north_room.vnum)
    hidden.invis_level = char.level + 5

    out = process_command(char, "scan north")
    assert "Visible, nearby to the north." in out
    assert "Shadow" not in out

    char.trust = hidden.invis_level
    out2 = process_command(char, "scan north")
    assert "Shadow, nearby to the north." in out2


def test_scan_shows_sneaking_character_when_skill_roll_fails():
    initialize_world("area/area.lst")
    watcher = create_test_character("Watcher", 3001)
    sneaky = create_test_character("Sneaky", 3001)
    sneaky.add_affect(AffectFlag.SNEAK)

    out = process_command(watcher, "scan")
    assert "Sneaky, right here." in out


def test_look_lists_sneaking_character_when_skill_roll_fails():
    initialize_world("area/area.lst")
    viewer = create_test_character("Viewer", 3001)
    sneaky = create_test_character("Sneaky", 3001)
    sneaky.add_affect(AffectFlag.SNEAK)

    out = process_command(viewer, "look")
    assert "Sneaky" in out


def test_alias_create_expand_and_unalias():
    initialize_world("area/area.lst")
    char = create_test_character("AliasUser", 3001)

    # Initially no aliases
    out0 = process_command(char, "alias")
    assert "No aliases" in out0

    # Create alias and use it
    set_out = process_command(char, "alias lk look")
    assert "Alias set: lk -> look" in set_out
    out1 = process_command(char, "lk")
    assert "Temple" in out1  # expanded to look

    # Remove alias
    rm_out = process_command(char, "unalias lk")
    assert "Removed alias" in rm_out
    out2 = process_command(char, "lk")
    assert out2 == "Huh?"


def test_alias_persists_in_save_load(tmp_path, monkeypatch):
    initialize_world("area/area.lst")
    char = create_test_character("AliasPersist", 3001)
    process_command(char, "alias lk look")

    # Redirect players dir to tmp
    from mud import persistence as p

    monkeypatch.setattr(p, "PLAYERS_DIR", tmp_path)
    p.save_character(char)

    loaded = p.load_character("AliasPersist")
    assert loaded is not None
    out = process_command(loaded, "lk")
    assert "Temple" in out


def test_prefix_command_sets_changes_and_clears():
    initialize_world("area/area.lst")
    char = create_test_character("Prefixer", 3001)

    out1 = process_command(char, "prefix say")
    assert out1 == "Prefix set to say."
    assert char.prefix == "say"

    out2 = process_command(char, "prefix cast 'armor'")
    assert out2 == "Prefix changed to cast 'armor'."
    assert char.prefix == "cast 'armor'"

    out3 = process_command(char, "prefix")
    assert out3 == "Prefix removed."
    assert char.prefix == ""

    out4 = process_command(char, "prefix")
    assert out4 == "You have no prefix to clear."


def test_prefi_rejects_abbreviation():
    initialize_world("area/area.lst")
    char = create_test_character("Prefi", 3001)

    out = process_command(char, "prefi anything")
    assert out == "You cannot abbreviate the prefix command."


def test_prefix_macro_prepends_to_commands():
    initialize_world("area/area.lst")
    speaker = create_test_character("Speaker", 3001)
    listener = create_test_character("Listener", 3001)

    process_command(speaker, "prefix say")
    alias_output = process_command(speaker, "alias")
    assert "No aliases" in alias_output

    out = process_command(speaker, "hello there")
    assert out == "You say, 'hello there'"
    assert f"{speaker.name} says, 'hello there'" in listener.messages


def test_command_execution_breaks_hide():
    initialize_world("area/area.lst")
    char = create_test_character("Sneak", 3001)
    char.add_affect(AffectFlag.HIDE)
    assert char.has_affect(AffectFlag.HIDE) is True

    out = process_command(char, "look")
    assert "Temple" in out
    assert char.has_affect(AffectFlag.HIDE) is False


def test_look_hides_invisible_targets():
    initialize_world("area/area.lst")
    viewer = create_test_character("Watcher", 3001)
    visible = create_test_character("Visible", 3001)
    hidden = create_test_character("Shadow", 3001)
    hidden.invis_level = viewer.level + 5

    out = process_command(viewer, "look")
    assert "Visible" in out
    assert "Shadow" not in out

    viewer.trust = hidden.invis_level
    out2 = process_command(viewer, "look")
    assert "Shadow" in out2


def test_frozen_player_cannot_run_commands():
    initialize_world("area/area.lst")
    char = create_test_character("Icicle", 3001)
    char.act = int(PlayerFlag.FREEZE)

    out = process_command(char, "look")

    assert out == "You're totally frozen!"


def test_commands_lists_accessible_commands():
    initialize_world("area/area.lst")
    char = create_test_character("Lister", 3001)

    output = process_command(char, "commands")
    assert output.endswith("\n\r")

    lines = [line for line in output.split("\n\r") if line]

    from mud.commands.dispatcher import COMMANDS
    from mud.models.constants import LEVEL_HERO

    trust = char.trust if getattr(char, "trust", 0) > 0 else getattr(char, "level", 0)
    expected = [
        cmd.name
        for cmd in COMMANDS
        if cmd.show and cmd.min_trust < LEVEL_HERO and cmd.min_trust <= trust
    ]

    flattened: list[str] = []
    for line in lines:
        for start in range(0, len(line), 12):
            name = line[start : start + 12].strip()
            if name:
                flattened.append(name)

    assert flattened == expected
    assert "@teleport" not in output
    assert "wizlock" not in output
    assert "immtalk" not in output
    assert "prefi" not in flattened
    assert "north" not in flattened


def test_wizhelp_denied_to_mortals():
    initialize_world("area/area.lst")
    char = create_test_character("Novice", 3001)

    output = process_command(char, "wizhelp")

    assert output == "Huh?"


def test_wizhelp_lists_immortal_commands():
    initialize_world("area/area.lst")
    char = create_test_character("Immortal", 3001)
    from mud.models.constants import LEVEL_HERO

    char.level = LEVEL_HERO

    output = process_command(char, "wizhelp")
    assert output.endswith("\n\r")

    lines = [line for line in output.split("\n\r") if line]

    from mud.commands.dispatcher import COMMANDS

    trust = char.trust if getattr(char, "trust", 0) > 0 else getattr(char, "level", 0)
    expected = [
        cmd.name
        for cmd in COMMANDS
        if cmd.show and cmd.min_trust >= LEVEL_HERO and cmd.min_trust <= trust
    ]

    flattened: list[str] = []
    for line in lines:
        for start in range(0, len(line), 12):
            name = line[start : start + 12].strip()
            if name:
                flattened.append(name)

    assert flattened == expected
    assert "commands" not in output
    assert "wizhelp" in output
    assert "@teleport" in output
    assert "prefi" not in flattened


def test_wizlist_displays_help_topic():
    initialize_world("area/area.lst")
    char = create_test_character("Curious", 3001)

    from mud.commands.help import do_help

    expected = do_help(char, "wizlist")
    output = process_command(char, "wizlist")

    assert output == expected


def test_help_admin_command_hidden_from_mortals():
    initialize_world("area/area.lst")
    char = create_test_character("Curious", 3001)

    from mud.commands.help import do_help

    output = do_help(char, "@teleport")

    lines = [line for line in output.split("\r\n") if line]
    assert lines == ["No help on that word."]


def test_help_admin_command_visible_to_admins():
    initialize_world("area/area.lst")
    char = create_test_character("Archon", 3001)

    from mud.commands.help import _generate_command_help, do_help
    from mud.models.constants import LEVEL_HERO

    char.level = LEVEL_HERO
    char.is_admin = True

    expected = _generate_command_help(char, "@teleport")
    output = do_help(char, "@teleport")

    assert expected is not None
    assert output == expected
    assert "Command: @teleport" in output
    assert "Immortal-only command (admin flag required)." in output


def test_position_gating_sleeping_blocks_look_allows_scan():
    initialize_world("area/area.lst")
    char = create_test_character("Sleeper", 3001)
    # Force sleeping state
    char.position = Position.SLEEPING

    out1 = process_command(char, "look")
    assert out1 == "In your dreams, or what?"

    out2 = process_command(char, "scan")
    assert "Looking around you see:" in out2


def test_position_gating_resting_blocks_movement():
    initialize_world("area/area.lst")
    char = create_test_character("Repose", 3001)
    here = char.room
    # Force resting state
    char.position = Position.RESTING

    out = process_command(char, "north")
    assert out == "Nah... You feel too relaxed..."
    # Ensure no movement occurred
    assert char.room is here
