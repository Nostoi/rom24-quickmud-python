from mud.commands.dispatcher import process_command
from mud.world import create_test_character, initialize_world


def test_enter_closed_portal_denied(portal_factory):
    initialize_world("area/area.lst")
    ch = create_test_character("Traveler", 3001)
    portal_factory(3001, to_vnum=3054, closed=True)
    out = process_command(ch, "enter portal")
    assert out == "The portal is closed."
    assert ch.room.vnum == 3001


def test_enter_open_portal_moves_character(portal_factory):
    initialize_world("area/area.lst")
    ch = create_test_character("Traveler", 3001)
    portal_factory(3001, to_vnum=3054, closed=False)
    out = process_command(ch, "enter portal")
    assert out == "You walk through a shimmering portal and find yourself somewhere else..."
    assert ch.room.vnum == 3054
