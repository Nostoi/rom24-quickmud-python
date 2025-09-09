from mud.world import initialize_world, create_test_character
from mud.registry import room_registry
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.constants import ItemType, EX_CLOSED
from mud.commands.dispatcher import process_command


def make_portal(vnum_from: int, vnum_to: int, *, closed: bool = False) -> None:
    room = room_registry[vnum_from]
    flags = EX_CLOSED if closed else 0
    proto = ObjIndex(vnum=9998, name="shimmering portal", short_descr="a shimmering portal", item_type=int(ItemType.PORTAL))
    proto.value = [1, flags, 0, vnum_to, 0]
    obj = Object(instance_id=None, prototype=proto)
    room.add_object(obj)


def test_enter_closed_portal_denied():
    initialize_world('area/area.lst')
    ch = create_test_character('Traveler', 3001)
    make_portal(3001, 3054, closed=True)
    out = process_command(ch, 'enter portal')
    assert out == 'The portal is closed.'
    assert ch.room.vnum == 3001


def test_enter_open_portal_moves_character():
    initialize_world('area/area.lst')
    ch = create_test_character('Traveler', 3001)
    make_portal(3001, 3054, closed=False)
    out = process_command(ch, 'enter portal')
    assert 'arrive' in out
    assert ch.room.vnum == 3054

