from pathlib import Path
from pathlib import Path

from types import SimpleNamespace

from mud.commands.dispatcher import process_command
from mud.loaders.help_loader import load_help_file
from mud.models.character import Character
from mud.models.constants import OHELPS_FILE
from mud.models.help import HelpEntry, help_registry, register_help
from mud.models.room import Room
from mud.net.connection import _resolve_help_text


def setup_function(_):
    help_registry.clear()


def test_load_help_file_populates_registry():
    load_help_file("data/help.json")
    assert "murder" in help_registry


def test_help_command_returns_topic_text():
    load_help_file("data/help.json")
    ch = Character(name="Tester")
    result = process_command(ch, "help murder")
    assert "Murder is a terrible crime." in result


def test_help_defaults_to_summary_topic():
    load_help_file("data/help.json")
    ch = Character(name="Tester")
    result = process_command(ch, "help")
    assert "MOVEMENT" in result


def test_help_respects_trust_levels():
    load_help_file("data/help.json")
    mortal = Character(name="Newbie", level=1, trust=0)
    assert process_command(mortal, "help wizhelp") == "No help on that word."

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
    assert result == "No help on that word."


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

    assert "Basics." in result
    assert "Advanced tips." in result
    assert result.count("============================================================") == 1


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
    assert result == "No help on that word."


def test_help_overlong_request_rebukes_and_skips_logging(monkeypatch, tmp_path, caplog):
    monkeypatch.chdir(tmp_path)
    help_path = Path(__file__).resolve().parent.parent / "data" / "help.json"
    load_help_file(help_path)
    ch = Character(name="Researcher", is_npc=False)

    topic = "".join("a" for _ in range(55))
    with caplog.at_level("WARNING"):
        result = process_command(ch, f"help {topic}")

    assert "That was rude!" in result
    assert "No help on that word." in result
    assert any("Excessive help request length" in record.message for record in caplog.records)
    log_path = Path("log") / OHELPS_FILE
    assert not log_path.exists()


def test_help_generates_command_topic_when_missing():
    load_help_file("data/help.json")
    ch = Character(name="Tester")
    result = process_command(ch, "help unalias")
    assert "Command: unalias" in result
    assert "Minimum position" in result


def test_help_missing_topic_suggests_commands():
    load_help_file("data/help.json")
    ch = Character(name="Tester")
    result = process_command(ch, "help unknown")
    assert "Try:" in result
    assert "unban" in result or "unalias" in result


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
