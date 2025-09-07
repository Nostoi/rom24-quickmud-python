from mud.models.character import Character
from mud.models.obj import ObjIndex
from mud.models.object import Object


def test_carry_weight_updates_on_pickup_equip_drop():
    ch = Character(name="Tester")
    proto = ObjIndex(vnum=1, weight=5)
    obj = Object(instance_id=None, prototype=proto)

    ch.add_object(obj)
    assert ch.carry_number == 1
    assert ch.carry_weight == 5

    ch.equip_object(obj, "hold")
    assert ch.carry_number == 1
    assert ch.carry_weight == 5

    ch.remove_object(obj)
    assert ch.carry_number == 0
    assert ch.carry_weight == 0
