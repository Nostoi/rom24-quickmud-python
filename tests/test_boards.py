import mud.notes as notes
from mud.commands.dispatcher import process_command
from mud.world import initialize_world, create_test_character


def test_note_persistence(tmp_path):
    notes.BOARDS_DIR = tmp_path
    notes.load_boards()
    initialize_world('area/area.lst')
    char = create_test_character('Author', 3001)
    output = process_command(char, 'note post Hello|This is a test')
    assert 'posted' in output.lower()
    list_output = process_command(char, 'note list')
    assert 'hello' in list_output.lower()
    notes.board_registry.clear()
    notes.load_boards()
    list_output2 = process_command(char, 'note list')
    assert 'hello' in list_output2.lower()
