from mud.commands import process_command
from mud.net.session import Session
from mud.world import create_test_character, initialize_world


def setup_module(module):
    initialize_world("area/area.lst")


def _attach_session(char):
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    return session


def test_redit_requires_builder_security_and_marks_area():
    builder = create_test_character("Builder", 3001)
    builder.is_admin = True
    builder.room.area.security = 9
    builder.pcdata.security = 0
    session = _attach_session(builder)

    denied = process_command(builder, "@redit")
    assert "builder rights" in denied.lower()
    assert session.editor is None

    builder.pcdata.security = 9
    accepted = process_command(builder, "@redit")
    assert "room editor activated" in accepted.lower()
    assert session.editor == "redit"

    renamed = process_command(builder, 'name "New Room"')
    assert "room name set" in renamed.lower()
    assert builder.room.name == "New Room"
    assert builder.room.area.changed is True

    described = process_command(builder, 'desc "A test room"')
    assert "description updated" in described.lower()
    assert builder.room.description == "A test room"

    shown = process_command(builder, "show")
    assert "new room" in shown.lower()

    exited = process_command(builder, "done")
    assert "exiting room editor" in exited.lower()
    assert session.editor is None

    look = process_command(builder, "look")
    assert look
