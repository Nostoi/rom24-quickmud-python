from pathlib import Path

from types import SimpleNamespace

from mud.commands.dispatcher import process_command
from mud.loaders.help_loader import load_help_file
from mud.models.character import Character
from mud.models.constants import OHELPS_FILE
from mud.models.help import HelpEntry, clear_help_registry, help_registry, register_help
from mud.models.room import Room
from mud.net.connection import _resolve_help_text


def setup_function(_):
    clear_help_registry()


def test_load_help_file_populates_registry():
    load_help_file("data/help.json")
    assert "dwarf" in help_registry


def test_help_command_returns_topic_text():
    load_help_file("data/help.json")
    ch = Character(name="Tester")
    result = process_command(ch, "help dwarf")
    assert "Dwarves are short" in result


def test_help_defaults_to_summary_topic():
    load_help_file("data/help.json")
    ch = Character(name="Tester")
    result = process_command(ch, "help")
    assert "MOVEMENT" in result


def test_help_respects_trust_levels():
    load_help_file("data/help.json")
    mortal = Character(name="Newbie", level=1, trust=0)
    assert process_command(mortal, "help wizhelp") == "No help on that word.\r\n"

    immortal = Character(name="Imm", level=60)
    result = process_command(immortal, "help wizhelp")
    assert "Syntax: wizhelp" in result


def test_help_restricted_topic_logs_request(monkeypatch, tmp_path):
    help_path = Path(__file__).resolve().parent.parent / "data" / "help.json"
    monkeypatch.chdir(tmp_path)
    load_help_file(help_path)

    ch = Character(name="Newbie", level=1, trust=0, is_npc=False)
    ch.room = Room(vnum=3001)

    result = process_command(ch, "help wizhelp")

    log_path = Path("log") / OHELPS_FILE
    assert log_path.exists()
    assert "[ 3001] Newbie: wizhelp" in log_path.read_text(encoding="utf-8")
    assert result == "No help on that word.\r\n"


def test_help_reconstructs_multi_word_keywords():
    load_help_file("data/help.json")
    entry = HelpEntry(keywords=["ARMOR CLASS", "ARMOR"], text="Armor class overview")
    register_help(entry)

    ch = Character(name="Tester")
    result = process_command(ch, "help armor class")
    assert "Armor class overview" in result


def test_help_combines_matching_entries_with_separator():
    first = HelpEntry(keywords=["ARMOR"], text="Basics.\n")
    second = HelpEntry(keywords=["ARMOR IMMORTAL"], text="Advanced tips.\n")
    register_help(first)
    register_help(second)

    ch = Character(name="Tester")
    result = process_command(ch, "help armor")

    expected = (
        "ARMOR\r\n"
        "Basics.\r\n"
        "\r\n============================================================\r\n\r\n"
        "ARMOR IMMORTAL\r\n"
        "Advanced tips.\r\n"
    )

    assert result == expected


def test_help_returns_all_matching_entries_when_keywords_collide():
    command_entry = HelpEntry(keywords=["STEAL"], text="Command synopsis.\n")
    skill_entry = HelpEntry(keywords=["STEAL"], text="Skill description.\n")
    register_help(command_entry)
    register_help(skill_entry)

    ch = Character(name="Thief")
    result = process_command(ch, "help steal")

    expected = (
        "STEAL\r\n"
        "Command synopsis.\r\n"
        "\r\n============================================================\r\n\r\n"
        "STEAL\r\n"
        "Skill description.\r\n"
    )

    assert result == expected


def test_help_partial_tokens_match_multi_word_keywords():
    entry = HelpEntry(keywords=["ARMOR CLASS"], text="Armor class overview")
    register_help(entry)

    ch = Character(name="Tester")
    result = process_command(ch, "help a c")

    assert "Armor class overview" in result


def test_help_missing_topic_logs_request(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    help_path = Path(__file__).resolve().parent.parent / "data" / "help.json"
    load_help_file(help_path)
    ch = Character(name="Researcher", is_npc=False)
    ch.room = Room(vnum=3001)

    result = process_command(ch, "help planar theory")

    log_path = Path("log") / OHELPS_FILE
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "[ 3001] Researcher: planar theory" in content
    assert result == "No help on that word.\r\n"


def test_help_overlong_request_rebukes_and_skips_logging(monkeypatch, tmp_path, caplog):
    monkeypatch.chdir(tmp_path)
    help_path = Path(__file__).resolve().parent.parent / "data" / "help.json"
    load_help_file(help_path)
    ch = Character(name="Researcher", is_npc=False)

    topic = "".join("a" for _ in range(55))
    with caplog.at_level("WARNING"):
        result = process_command(ch, f"help {topic}")

    assert result == "No help on that word.\r\nThat was rude!\r\n"
    assert any("Excessive help request length" in record.message for record in caplog.records)
    log_path = Path("log") / OHELPS_FILE
    assert not log_path.exists()


def test_help_generates_command_topic_when_missing(monkeypatch, tmp_path):
    help_path = Path(__file__).resolve().parent.parent / "data" / "help.json"
    monkeypatch.chdir(tmp_path)
    load_help_file(help_path)
    ch = Character(name="Tester", is_npc=False)
    ch.room = Room(vnum=3001)
    result = process_command(ch, "help unalias")
    expected = "Command: unalias\r\nAliases: None\r\nMinimum position: Dead\r\nAvailable to mortals.\r\n"
    log_path = Path("log") / OHELPS_FILE
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "[ 3001] Tester: unalias" in content
    assert result == expected


def test_help_cast_fallback_includes_usage(monkeypatch, tmp_path):
    from mud.commands import dispatcher

    monkeypatch.chdir(tmp_path)
    clear_help_registry()

    cast_command = dispatcher.Command("cast", dispatcher.do_commands)
    commands = dispatcher.COMMANDS + [cast_command]
    index = dict(dispatcher.COMMAND_INDEX)
    index[cast_command.name] = cast_command
    monkeypatch.setattr(dispatcher, "COMMANDS", commands, raising=False)
    monkeypatch.setattr(dispatcher, "COMMAND_INDEX", index, raising=False)

    ch = Character(name="Caster", is_npc=False)
    ch.room = Room(vnum=3001)

    result = process_command(ch, "help cast")

    expected = (
        "Command: cast\r\n"
        "Aliases: None\r\n"
        "Minimum position: Dead\r\n"
        "Available to mortals.\r\n"
        "Usage: cast '<spell>' [target]\r\n"
        "Casting a learned spell consumes mana based on the spell level.\r\n"
    )

    log_path = Path("log") / OHELPS_FILE
    assert log_path.exists()
    assert "Caster: cast" in log_path.read_text(encoding="utf-8")
    assert result == expected


def test_help_hidden_command_returns_no_help(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    clear_help_registry()

    ch = Character(name="Player", level=1, trust=0, is_npc=False)
    ch.room = Room(vnum=3001)

    result = process_command(ch, "help prefi")

    assert result.startswith("No help on that word.")
    assert "Command: prefi" not in result
    if "Try:" in result:
        lines = [line for line in result.split("\r\n") if line]
        suggestions_line = next((line for line in lines if line.startswith("Try: ")), "")
        suggestions = [entry.strip() for entry in suggestions_line[5:].split(",") if entry.strip()]
        assert "prefi" not in suggestions
    log_path = Path("log") / OHELPS_FILE
    assert log_path.exists()
    assert "Player: prefi" in log_path.read_text(encoding="utf-8")


def test_help_missing_topic_suggests_commands():
    load_help_file("data/help.json")
    ch = Character(name="Tester")
    result = process_command(ch, "help unknown")
    assert result.startswith("No help on that word.\r\nTry: ")
    assert result.endswith("\r\n")
    assert "unban" in result or "unalias" in result


def test_help_suggestions_limit_to_five(monkeypatch, tmp_path):
    from mud.commands import dispatcher

    monkeypatch.chdir(tmp_path)
    clear_help_registry()

    new_commands = [
        dispatcher.Command("help", dispatcher.do_help),
        dispatcher.Command("albatross", dispatcher.do_commands),
        dispatcher.Command("alchemist", dispatcher.do_commands, aliases=("alch",)),
        dispatcher.Command("alert", dispatcher.do_commands),
        dispatcher.Command("alias", dispatcher.do_commands),
        dispatcher.Command("align", dispatcher.do_commands),
        dispatcher.Command("alley", dispatcher.do_commands),
        dispatcher.Command("alpha", dispatcher.do_commands),
    ]
    new_index: dict[str, dispatcher.Command] = {}
    for cmd in new_commands:
        new_index[cmd.name] = cmd
        for alias in cmd.aliases:
            new_index[alias] = cmd

    monkeypatch.setattr(dispatcher, "COMMANDS", new_commands, raising=False)
    monkeypatch.setattr(dispatcher, "COMMAND_INDEX", new_index, raising=False)

    ch = Character(name="Tester", is_npc=False)
    ch.room = Room(vnum=3001)

    result = process_command(ch, "help alz")

    lines = result.split("\r\n")
    assert lines[0] == "No help on that word."
    suggestions_line = lines[1]
    assert suggestions_line.startswith("Try: ")
    suggestions = [entry.strip() for entry in suggestions_line[5:].split(",") if entry.strip()]
    assert suggestions == ["albatross", "alchemist", "alert", "alias", "align"]
    assert len(suggestions) == 5


def test_help_suggestions_skip_hidden_commands(monkeypatch, tmp_path):
    from mud.commands import dispatcher

    monkeypatch.chdir(tmp_path)
    clear_help_registry()

    help_command = dispatcher.Command("help", dispatcher.do_help)
    visible = dispatcher.Command("prefix", dispatcher.do_commands)
    hidden = dispatcher.Command("prefi", dispatcher.do_commands, show=False)
    commands = [help_command, hidden, visible]
    index: dict[str, dispatcher.Command] = {}
    for cmd in commands:
        index[cmd.name] = cmd
        for alias in cmd.aliases:
            index[alias] = cmd

    monkeypatch.setattr(dispatcher, "COMMANDS", commands, raising=False)
    monkeypatch.setattr(dispatcher, "COMMAND_INDEX", index, raising=False)

    ch = Character(name="Player", level=1, trust=0, is_npc=False)
    ch.room = Room(vnum=3001)

    result = process_command(ch, "help pref")

    lines = result.split("\r\n")
    assert lines[0] == "No help on that word."
    suggestions_line = lines[1]
    assert suggestions_line.startswith("Try: ")
    suggestions = [entry.strip() for entry in suggestions_line[5:].split(",") if entry.strip()]
    assert suggestions == ["prefix"]


def test_help_preserves_duplicate_entries_with_identical_payloads():
    duplicate_one = HelpEntry(keywords=["STEAL"], text="Duplicate synopsis.\n")
    duplicate_two = HelpEntry(keywords=["STEAL"], text="Duplicate synopsis.\n")
    register_help(duplicate_one)
    register_help(duplicate_two)

    ch = Character(name="Thief")
    result = process_command(ch, "help steal")

    expected = (
        "STEAL\r\n"
        "Duplicate synopsis.\r\n"
        "\r\n============================================================\r\n\r\n"
        "STEAL\r\n"
        "Duplicate synopsis.\r\n"
    )

    assert result == expected


def test_help_handles_quoted_topics():
    entry = HelpEntry(keywords=["ARMOR CLASS"], text="Armor class overview")
    register_help(entry)

    ch = Character(name="Tester")
    unquoted = process_command(ch, "help armor class")
    single_quoted = process_command(ch, "help 'armor class'")
    double_quoted = process_command(ch, 'help "armor class"')

    assert unquoted == single_quoted == double_quoted


def test_help_creation_flow_limits_to_first_entry():
    mortal_entry = HelpEntry(keywords=["RACE"], text="Base race overview.")
    immortal_entry = HelpEntry(keywords=["RACE IMMORTAL"], text="Immortal race lore.")
    register_help(mortal_entry)
    register_help(immortal_entry)

    helper = SimpleNamespace(name="Preview", trust=0, level=0, is_npc=False, room=None)
    creation_text = _resolve_help_text(helper, "race", limit_first=True)

    assert creation_text is not None
    assert "Base race overview." in creation_text
    assert "Immortal race lore." not in creation_text

    live_player = Character(name="Explorer")
    combined = process_command(live_player, "help race")

    assert "Base race overview." in combined
    assert "Immortal race lore." in combined
