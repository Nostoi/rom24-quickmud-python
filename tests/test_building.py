from mud.commands import process_command
from mud.models.constants import Direction, EX_CLOSED, EX_ISDOOR, EX_LOCKED
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


def test_redit_can_create_exit_and_set_flags():
    builder = create_test_character("Builder", 3001)
    builder.is_admin = True
    builder.room.area.security = 1
    builder.pcdata.security = 1
    session = _attach_session(builder)

    start = process_command(builder, "@redit")
    assert "room editor activated" in start.lower()

    created = process_command(builder, "@redit north create 3002")
    assert "leads to room 3002" in created.lower()

    exit_obj = builder.room.exits[Direction.NORTH.value]
    assert exit_obj is not None
    assert exit_obj.vnum == 3002
    assert builder.room.area.changed is True

    flagged = process_command(builder, "@redit north flags door closed locked")
    assert "flags set" in flagged.lower()
    assert exit_obj.exit_info == EX_ISDOOR | EX_CLOSED | EX_LOCKED

    keyed = process_command(builder, "@redit north key 1023")
    assert "key set" in keyed.lower()
    assert exit_obj.key == 1023

    described = process_command(builder, "@redit north desc A solid oak door")
    assert "description updated" in described.lower()
    assert exit_obj.description == "A solid oak door"

    summary = process_command(builder, "@redit north")
    assert "oak door" in summary.lower()
    assert "flags" in summary.lower()

    done = process_command(builder, "@redit done")
    assert "exiting" in done.lower()
    assert session.editor is None


def test_redit_ed_adds_and_updates_extra_description():
    builder = create_test_character("Builder", 3001)
    builder.is_admin = True
    builder.room.area.security = 1
    builder.pcdata.security = 1
    session = _attach_session(builder)

    process_command(builder, "@redit")

    added = process_command(builder, "@redit ed add plaque")
    assert "extra description 'plaque' created" in added.lower()

    updated = process_command(builder, "@redit ed desc plaque A burnished brass plaque")
    assert "updated" in updated.lower()

    extras = [extra for extra in builder.room.extra_descr if extra.keyword == "plaque"]
    assert extras
    assert extras[0].description == "A burnished brass plaque"
    assert builder.room.area.changed is True

    listing = process_command(builder, "@redit ed list")
    assert "plaque" in listing.lower()

    removed = process_command(builder, "@redit ed delete plaque")
    assert "removed" in removed.lower()
    assert not any(extra.keyword == "plaque" for extra in builder.room.extra_descr)

    process_command(builder, "@redit done")
    assert session.editor is None
