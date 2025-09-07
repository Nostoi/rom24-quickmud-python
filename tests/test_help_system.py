from mud.loaders.help_loader import load_help_file
from mud.models.help import help_registry
from mud.commands.dispatcher import process_command
from mud.models.character import Character


def setup_function(_):
    help_registry.clear()


def test_load_help_file_populates_registry():
    load_help_file('data/help.json')
    assert 'murder' in help_registry


def test_help_command_returns_topic_text():
    load_help_file('data/help.json')
    ch = Character(name='Tester')
    result = process_command(ch, 'help murder')
    assert 'Murder is a terrible crime.' in result
