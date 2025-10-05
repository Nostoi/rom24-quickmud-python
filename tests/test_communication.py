from mud.commands import process_command
from mud.models.character import character_registry
from mud.models.constants import CommFlag
from mud.registry import (
    area_registry,
    mob_registry,
    obj_registry,
    room_registry,
)
from mud.world import create_test_character, initialize_world


def setup_function(function):
    room_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    area_registry.clear()
    character_registry.clear()
    initialize_world("area/area.lst")


def test_tell_command():
    alice = create_test_character("Alice", 3001)
    bob = create_test_character("Bob", 3001)
    out = process_command(alice, "tell Bob hello")
    assert out == "You tell Bob, 'hello'"
    assert "Alice tells you, 'hello'" in bob.messages


def test_shout_respects_mute_and_ban():
    alice = create_test_character("Alice", 3001)
    bob = create_test_character("Bob", 3001)
    cara = create_test_character("Cara", 3001)
    bob.muted_channels.add("shout")
    out = process_command(alice, "shout hello")
    assert out == "You shout, 'hello'"
    assert "Alice shouts, 'hello'" in cara.messages
    assert all("hello" not in m for m in bob.messages)
    alice.banned_channels.add("shout")
    out = process_command(alice, "shout again")
    assert out == "You are banned from shout."
    assert all("again" not in m for m in cara.messages)


def test_tell_respects_mute_and_ban():
    alice = create_test_character("Alice", 3001)
    bob = create_test_character("Bob", 3001)
    bob.muted_channels.add("tell")
    out = process_command(alice, "tell Bob hi")
    assert out == "They aren't listening."
    assert not bob.messages
    alice.banned_channels.add("tell")
    out = process_command(alice, "tell Bob hi")
    assert out == "You are banned from tell."


def test_shout_and_tell_respect_comm_flags():
    alice = create_test_character("Alice", 3001)
    bob = create_test_character("Bob", 3001)

    out = process_command(alice, "shout")
    assert out == "You will no longer hear shouts."
    assert alice.has_comm_flag(CommFlag.SHOUTSOFF)

    bob.messages.clear()
    out = process_command(alice, "shout hello")
    assert out == "You must turn shouts back on first."
    assert not bob.messages

    out = process_command(alice, "shout")
    assert out == "You can hear shouts again."
    assert not alice.has_comm_flag(CommFlag.SHOUTSOFF)

    alice.set_comm_flag(CommFlag.QUIET)
    out = process_command(alice, "shout hi")
    assert out == "You must turn off quiet mode first."
    alice.clear_comm_flag(CommFlag.QUIET)

    bob.messages.clear()
    out = process_command(alice, "shout hi")
    assert out == "You shout, 'hi'"
    assert alice.wait == 12
    assert "Alice shouts, 'hi'" in bob.messages

    alice.set_comm_flag(CommFlag.NOTELL)
    bob.messages.clear()
    out = process_command(alice, "tell Bob hi")
    assert out == "Your message didn't get through."
    assert not bob.messages

    alice.clear_comm_flag(CommFlag.NOTELL)
    alice.set_comm_flag(CommFlag.QUIET)
    out = process_command(alice, "tell Bob hi")
    assert out == "You must turn off quiet mode first."
    alice.clear_comm_flag(CommFlag.QUIET)

    bob.set_comm_flag(CommFlag.QUIET)
    out = process_command(alice, "tell Bob hi")
    assert out == "Bob is not receiving tells."
    assert not bob.messages
