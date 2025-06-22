import pytest

from mud.models import (
    Area, Room, ExtraDescr, Exit, Reset,
    MobIndex, MobProgram,
    ObjIndex, ObjectData, Affect,
    Character, PCData,
    Direction, Sector, Position, WearLocation, Sex, Size, ItemType,
)


def test_area_room_instantiation():
    area = Area(vnum=1, name="Test Area")
    room = Room(vnum=100, name="Test Room", area=area)
    assert repr(area) == "<Area vnum=1 name='Test Area'>"
    assert repr(room) == "<Room vnum=100 name='Test Room'>"


def test_obj_instantiation():
    obj_index = ObjIndex(vnum=200, short_descr="A stick", item_type=ItemType.WEAPON)
    obj = ObjectData(item_type=ItemType.WEAPON, pIndexData=obj_index, short_descr="A stick")
    assert obj.item_type == ItemType.WEAPON
    assert obj.pIndexData is obj_index


def test_character_instantiation():
    pc = PCData(pwd="secret")
    char = Character(name="Hero", level=10, pcdata=pc)
    assert char.level == 10
    assert char.pcdata is pc

