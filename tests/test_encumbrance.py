from mud.commands.inventory import do_get
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


def test_do_get_blocked_by_weight_limit(object_factory):
    """Test ROM src/act_obj.c:do_get weight limit enforcement."""
    room = Room(vnum=2000, name="Test Room")
    ch = Character(name="Weak", level=1)
    room.add_character(ch)

    ch.carry_weight = can_carry_w(ch)

    heavy_obj = object_factory({"vnum": 100, "short_descr": "a heavy stone", "weight": 5})
    room.add_object(heavy_obj)

    result = do_get(ch, "stone")

    assert "can't carry that much weight" in result
    assert heavy_obj in room.contents
    assert heavy_obj not in ch.inventory


def test_do_get_blocked_by_item_count_limit(object_factory):
    """Test ROM src/act_obj.c:do_get item count limit enforcement."""
    room = Room(vnum=2001, name="Test Room")
    ch = Character(name="Full Hands", level=1)
    room.add_character(ch)

    ch.carry_number = can_carry_n(ch)

    light_obj = object_factory({"vnum": 101, "short_descr": "a feather", "weight": 1})
    room.add_object(light_obj)

    result = do_get(ch, "feather")

    assert "can't carry that many items" in result
    assert light_obj in room.contents
    assert light_obj not in ch.inventory


def test_do_get_succeeds_when_under_limits(object_factory):
    """Test successful get when under both weight and item limits."""
    room = Room(vnum=2002, name="Test Room")
    ch = Character(name="Free Hands", level=1)
    room.add_character(ch)

    ch.carry_number = 0
    ch.carry_weight = 0

    obj = object_factory({"vnum": 102, "short_descr": "a small gem", "weight": 1})
    room.add_object(obj)

    result = do_get(ch, "gem")

    assert "You pick up" in result
    assert obj not in room.contents
    assert obj in ch.inventory
    assert ch.carry_number == 1
    assert ch.carry_weight == 1


def test_obj_to_obj_updates_carrier_weight(object_factory):
    """Test ROM handler.c:1978-1986 - obj_to_obj updates carrier weight.

    Bug Discovery: January 2, 2026 - handler.c audit
    ROM C: handler.c:1968-1989 obj_to_obj
    """
    from mud.game_loop import _obj_to_obj

    ch = Character(name="Carrier")
    ch.carry_number = 0
    ch.carry_weight = 0

    # Create container with 50% weight reduction (value[4] = 50)
    container = object_factory(
        {
            "vnum": 100,
            "weight": 5,
            "item_type": int(ItemType.CONTAINER),
            "value": [10, 0, 0, 0, 50],  # value[4] = 50 (50% weight multiplier)
        }
    )

    # Create item to put in container (10 lbs)
    item = object_factory({"vnum": 101, "weight": 10})

    # Character picks up empty container
    ch.add_object(container)
    container.carried_by = ch  # Manually set carried_by for _obj_to_obj to find carrier
    assert ch.carry_number == 0  # Containers don't count
    assert ch.carry_weight == 5  # Just container base weight

    # Put item in container (ROM C should add: 10 * 50 / 100 = 5 lbs)
    _obj_to_obj(item, container)

    # Verify carrier weight increased by (item_weight * container_mult / 100)
    assert ch.carry_number == 1  # Item counts
    assert ch.carry_weight == 10  # 5 (container) + 5 (item at 50%)


def test_obj_from_obj_decreases_carrier_weight(object_factory):
    """Test ROM handler.c:2033-2041 - obj_from_obj decreases carrier weight.

    Bug Discovery: January 2, 2026 - handler.c audit
    ROM C: handler.c:1996-2044 obj_from_obj
    """
    from mud.game_loop import _obj_to_obj, _obj_from_obj

    ch = Character(name="Carrier")
    ch.carry_number = 0
    ch.carry_weight = 0

    # Container with 80% weight (value[4] = 80)
    container = object_factory(
        {
            "vnum": 200,
            "weight": 2,
            "item_type": int(ItemType.CONTAINER),
            "value": [10, 0, 0, 0, 80],  # 80% weight multiplier
        }
    )

    # Heavy item (20 lbs)
    item = object_factory({"vnum": 201, "weight": 20})

    # Setup: carrier holds container with item
    ch.add_object(container)
    container.carried_by = ch  # Manually set carried_by for _obj_to_obj to find carrier
    _obj_to_obj(item, container)

    # Verify weight after adding: 2 + (20 * 80 / 100) = 18
    assert ch.carry_weight == 18
    assert ch.carry_number == 1

    # Remove item from container
    _obj_from_obj(item)

    # Verify weight decreased back to just container
    assert ch.carry_weight == 2
    assert ch.carry_number == 0


def test_nested_containers_update_all_carriers(object_factory):
    """Test ROM handler.c:1978-1986 nested container weight updates.

    Bug Discovery: January 2, 2026 - handler.c audit
    ROM C: The for loop in obj_to_obj walks up container hierarchy
    """
    from mud.game_loop import _obj_to_obj, _obj_from_obj

    ch = Character(name="Carrier")
    ch.carry_number = 0
    ch.carry_weight = 0

    # Outer bag (100% weight)
    outer_bag = object_factory(
        {
            "vnum": 300,
            "weight": 1,
            "item_type": int(ItemType.CONTAINER),
            "value": [20, 0, 0, 0, 100],  # 100% weight (no reduction)
        }
    )

    # Inner bag (50% weight)
    inner_bag = object_factory(
        {
            "vnum": 301,
            "weight": 1,
            "item_type": int(ItemType.CONTAINER),
            "value": [10, 0, 0, 0, 50],  # 50% weight reduction
        }
    )

    # Item (10 lbs)
    item = object_factory({"vnum": 302, "weight": 10})

    # Setup: carrier holds outer_bag containing inner_bag
    ch.add_object(outer_bag)
    outer_bag.carried_by = ch  # Manually set carried_by for _obj_to_obj to find carrier
    _obj_to_obj(inner_bag, outer_bag)

    # Verify: outer=1, inner=1, total=2
    assert ch.carry_weight == 2

    # Put item in inner bag
    # ROM C behavior: Walks up to outer_bag, adds get_obj_weight(item) * WEIGHT_MULT(outer_bag) / 100
    #   = 10 * 100 / 100 = 10 lbs
    # NOTE: This does NOT apply inner_bag's 50% multiplier during obj_to_obj()!
    # The multiplier is only applied when get_obj_weight(inner_bag) is called.
    # Total: 2 (initial) + 10 (item through outer_bag) = 12
    _obj_to_obj(item, inner_bag)

    assert ch.carry_weight == 12  # ROM C parity: multipliers not cumulative in obj_to_obj
    assert ch.carry_number == 1  # Only item counts

    # Remove item
    _obj_from_obj(item)

    assert ch.carry_weight == 2  # Back to just bags
    assert ch.carry_number == 0


def test_container_weight_multiplier_applied(object_factory):
    """Test container weight multipliers work correctly (0%, 50%, 100%).

    Bug Discovery: January 2, 2026 - handler.c audit
    ROM C: WEIGHT_MULT macro returns value[4] for containers
    """
    from mud.game_loop import _obj_to_obj

    ch = Character(name="Carrier")

    # Test 0% weight (weightless bag of holding)
    weightless_bag = object_factory(
        {
            "vnum": 400,
            "weight": 5,
            "item_type": int(ItemType.CONTAINER),
            "value": [50, 0, 0, 0, 0],  # 0% weight multiplier
        }
    )
    item = object_factory({"vnum": 401, "weight": 100})

    ch.carry_weight = 0
    ch.add_object(weightless_bag)
    weightless_bag.carried_by = ch  # Manually set carried_by for _obj_to_obj to find carrier
    _obj_to_obj(item, weightless_bag)

    # Expected: 5 (bag) + 0 (100 * 0 / 100) = 5
    assert ch.carry_weight == 5

    # Test 100% weight (no reduction)
    ch.remove_object(weightless_bag)
    full_weight_bag = object_factory(
        {
            "vnum": 402,
            "weight": 3,
            "item_type": int(ItemType.CONTAINER),
            "value": [50, 0, 0, 0, 100],  # 100% weight (default)
        }
    )
    item2 = object_factory({"vnum": 403, "weight": 20})

    ch.carry_weight = 0
    ch.add_object(full_weight_bag)
    full_weight_bag.carried_by = ch  # Manually set carried_by for _obj_to_obj to find carrier
    _obj_to_obj(item2, full_weight_bag)

    # Expected: 3 (bag) + 20 (20 * 100 / 100) = 23
    assert ch.carry_weight == 23
