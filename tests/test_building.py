from mud.world import initialize_world, create_test_character
from mud.commands import process_command


def setup_module(module):
    initialize_world('area/area.lst')


def test_redit_edits_room_fields():
    admin = create_test_character('Admin', 3001)
    admin.is_admin = True
    assert admin.room.name != 'New Room'
    out = process_command(admin, '@redit name "New Room"')
    assert 'Room name set' in out
    assert admin.room.name == 'New Room'

    out = process_command(admin, '@redit desc "A test room"')
    assert 'description updated' in out.lower()
    assert admin.room.description == 'A test room'
