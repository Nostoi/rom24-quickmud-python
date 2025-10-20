from mud.models.character import Character
from mud.models.constants import ActFlag, Direction, ItemType, LEVEL_IMMORTAL
from mud.models.room import Exit, Room
from mud.world.movement import can_carry_n, can_carry_w, move_character

def _build_rooms() -> tuple[Room, Room]:
    start = Room(vnum=1000, name="Start")
    dest = Room(vnum=1001, name="Destination")
    start.exits[Direction.NORTH.value] = Exit(to_room=dest)
    return start, dest


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


def test_container_contents_contribute_to_carry_weight(object_factory):
    ch = Character(name="Carrier")
    container = object_factory(
        {
            "vnum": 2,
            "weight": 5,
            "item_type": int(ItemType.CONTAINER),
            "value": [0, 0, 0, 0, 100],
        }
    )
    nested = object_factory({"vnum": 3, "weight": 3})
    container.contained_items.append(nested)

    ch.add_object(container)

    assert ch.carry_number == 1
    assert ch.carry_weight == 8


def test_carry_number_ignores_money_and_containers(object_factory):
    ch = Character(name="Counter")
    coins = object_factory({"vnum": 4, "weight": 1, "item_type": int(ItemType.MONEY)})
    gem = object_factory({"vnum": 5, "weight": 1, "item_type": int(ItemType.GEM)})
    trinket = object_factory({"vnum": 6, "weight": 1, "item_type": int(ItemType.TREASURE)})
    sack = object_factory(
        {
            "vnum": 7,
            "weight": 2,
            "item_type": int(ItemType.CONTAINER),
            "value": [0, 0, 0, 0, 100],
        }
    )

    sack.contained_items.extend([gem, trinket])

    ch.add_object(coins)
    assert ch.carry_number == 0

    ch.add_object(sack)
    # Container itself and gem should be ignored; only the treasure trinket counts.
    assert ch.carry_number == 1

    ch.remove_object(sack)
    assert ch.carry_number == 0


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


def test_immortal_and_pet_caps():
    immortal = Character(name="Immortal", is_npc=False, level=LEVEL_IMMORTAL)
    assert can_carry_n(immortal) == 1000
    assert can_carry_w(immortal) == 10_000_000

    pet = Character(name="Fido", is_npc=True, level=5, act=int(ActFlag.PET))
    assert can_carry_n(pet) == 0
    assert can_carry_w(pet) == 0


def test_encumbrance_movement_gating_respects_caps():
    start, dest = _build_rooms()

    pet = Character(name="Fido", is_npc=True, level=5, act=int(ActFlag.PET), move=10)
    start.add_character(pet)
    pet.carry_number = 1
    pet.carry_weight = 5
    assert move_character(pet, "north") == "You are too encumbered to move."
    assert pet.room is start

    immortal = Character(name="Immortal", is_npc=False, level=LEVEL_IMMORTAL, move=10)
    start.add_character(immortal)
    immortal.carry_number = 999
    immortal.carry_weight = 9_999_000
    assert move_character(immortal, "north") == "You walk north to Destination."
    assert immortal.room is dest


def test_coin_weight_limits_movement():
    start, dest = _build_rooms()

    hoarder = Character(name="Hoarder", move=10)
    start.add_character(hoarder)
    hoarder.gold = 1000  # 1000 * 2 / 5 = 400 weight, exceeding the 100 cap

    denial = move_character(hoarder, "north")
    assert denial == "You are too encumbered to move."
    assert hoarder.room is start

    hoarder.gold = 0
    hoarder.silver = 990  # 990 // 10 = 99 weight, under the default cap
    hoarder.move = 10

    success = move_character(hoarder, "north")
    assert success == "You walk north to Destination."
    assert hoarder.room is dest


def test_overweight_move_sets_wait_state():
    start, _ = _build_rooms()

    ch = Character(name="Burdened", move=10)
    start.add_character(ch)

    ch.carry_weight = can_carry_w(ch) + 5
    ch.carry_number = can_carry_n(ch) + 1
    ch.wait = 0

    denial = move_character(ch, "north")

    assert denial == "You are too encumbered to move."
    assert ch.room is start
    assert ch.wait >= 1
