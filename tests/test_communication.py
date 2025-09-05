from mud.world import initialize_world, create_test_character
from mud.commands import process_command
from mud.models.character import character_registry
from mud.registry import (
    room_registry,
    mob_registry,
    obj_registry,
    area_registry,
)


def setup_function(function):
    room_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    area_registry.clear()
    character_registry.clear()
    initialize_world('area/area.lst')


def test_tell_command():
    alice = create_test_character('Alice', 3001)
    bob = create_test_character('Bob', 3001)
    out = process_command(alice, 'tell Bob hello')
    assert out == "You tell Bob, 'hello'"
    assert "Alice tells you, 'hello'" in bob.messages


def test_shout_respects_mute_and_ban():
    alice = create_test_character('Alice', 3001)
    bob = create_test_character('Bob', 3001)
    cara = create_test_character('Cara', 3001)
    bob.muted_channels.add('shout')
    out = process_command(alice, 'shout hello')
    assert out == "You shout, 'hello'"
    assert "Alice shouts, 'hello'" in cara.messages
    assert all('hello' not in m for m in bob.messages)
    alice.banned_channels.add('shout')
    out = process_command(alice, 'shout again')
    assert out == "You are banned from shout."
    assert all('again' not in m for m in cara.messages)


def test_tell_respects_mute_and_ban():
    alice = create_test_character('Alice', 3001)
    bob = create_test_character('Bob', 3001)
    bob.muted_channels.add('tell')
    out = process_command(alice, 'tell Bob hi')
    assert out == "They aren't listening."
    assert not bob.messages
    alice.banned_channels.add('tell')
    out = process_command(alice, 'tell Bob hi')
    assert out == "You are banned from tell."
