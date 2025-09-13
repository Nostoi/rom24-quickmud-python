from mud.models.character import Character
from mud.world.movement import can_carry_w, can_carry_n


def test_carry_weight_updates_on_pickup_equip_drop(object_factory):
    ch = Character(name="Tester")
    obj = object_factory({"vnum": 1, "weight": 5})

    ch.add_object(obj)
    assert ch.carry_number == 1
    assert ch.carry_weight == 5

    ch.equip_object(obj, "hold")
    assert ch.carry_number == 1
    assert ch.carry_weight == 5

    ch.remove_object(obj)
    assert ch.carry_number == 0
    assert ch.carry_weight == 0


def test_stat_based_carry_caps_monotonic():
    ch = Character(name="StatTester", level=10)
    # No stats → legacy fixed caps preserved
    assert can_carry_w(ch) == 100
    assert can_carry_n(ch) == 30

    # Provide STR/DEX; ensure monotonic increase as stats rise
    # perm_stat index 0: STR, 1: DEX (ROM order)
    ch.perm_stat = [10, 10]
    base_w = can_carry_w(ch)
    base_n = can_carry_n(ch)
    ch.perm_stat = [15, 10]
    assert can_carry_w(ch) > base_w
    ch.perm_stat = [15, 12]
    assert can_carry_n(ch) > base_n
