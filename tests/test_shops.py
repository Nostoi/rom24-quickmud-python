from mud.world import initialize_world, create_test_character
from mud.commands.dispatcher import process_command
from mud.registry import shop_registry
from mud.spawning.obj_spawner import spawn_object
from mud.spawning.mob_spawner import spawn_mob
from mud.models.constants import ItemType, AffectFlag
from mud.time import time_info


def test_buy_from_grocer():
    initialize_world('area/area.lst')
    assert 3002 in shop_registry
    char = create_test_character('Buyer', 3010)
    char.gold = 100
    keeper = next(
        (p for p in char.room.people if getattr(p, 'prototype', None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)
    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        # Ensure grocer has at least one lantern in stock for this test
        if not any(((obj.short_descr or '').lower().startswith('a hooded brass lantern') for obj in keeper.inventory)):
            lantern = spawn_object(3031)
            assert lantern is not None
            lantern.prototype.short_descr = 'a hooded brass lantern'
            keeper.inventory.append(lantern)
        list_output = process_command(char, 'list')
        assert 'hooded brass lantern' in list_output
        assert '60 gold' in list_output
        buy_output = process_command(char, 'buy lantern')
        assert 'buy a hooded brass lantern' in buy_output.lower()
        assert char.gold == 40
        assert any((obj.short_descr or '').lower().startswith('a hooded brass lantern') for obj in char.inventory)
    finally:
        time_info.hour = previous_hour


def test_list_price_matches_buy_price():
    initialize_world('area/area.lst')
    assert 3002 in shop_registry
    char = create_test_character('Buyer', 3010)
    char.gold = 100
    keeper = next(
        (p for p in char.room.people if getattr(p, 'prototype', None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)
    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        if not any(((obj.short_descr or '').lower().startswith('a hooded brass lantern') for obj in keeper.inventory)):
            lantern = spawn_object(3031)
            assert lantern is not None
            lantern.prototype.short_descr = 'a hooded brass lantern'
            keeper.inventory.append(lantern)
        out = process_command(char, 'list')
        # Extract first price number from list output
        import re

        m = re.search(r"hooded brass lantern (\d+) gold", out)
        assert m
        price = int(m.group(1))
        before = char.gold
        out2 = process_command(char, 'buy lantern')
        assert char.gold == before - price
    finally:
        time_info.hour = previous_hour


def test_sell_to_grocer():
    initialize_world('area/area.lst')
    char = create_test_character('Seller', 3010)
    char.gold = 0
    keeper = next(
        (p for p in char.room.people if getattr(p, 'prototype', None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)
    keeper.inventory = [
        obj
        for obj in getattr(keeper, 'inventory', [])
        if 'lantern' not in (getattr(obj.prototype, 'short_descr', '') or '').lower()
    ]
    lantern = spawn_object(3031)
    assert lantern is not None
    lantern.prototype.item_type = 1
    char.add_object(lantern)
    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        sell_output = process_command(char, 'sell lantern')
        assert 'sell a hooded brass lantern' in sell_output.lower()
        assert char.gold == 16
        keeper = next(
            p for p in char.room.people if getattr(p, 'prototype', None) and p.prototype.vnum in shop_registry
        )
        assert any(
            (obj.short_descr or '').lower().startswith('a hooded brass lantern') for obj in keeper.inventory
        )
    finally:
        time_info.hour = previous_hour


def test_wand_staff_price_scales_with_charges_and_inventory_discount():
    from mud.spawning.obj_spawner import spawn_object
    from mud.spawning.mob_spawner import spawn_mob
    from mud.models.constants import ItemType
    initialize_world('area/area.lst')
    # Move to a room and spawn an alchemist-type shopkeeper who buys wands
    ch = create_test_character('Seller', 3001)
    keeper = spawn_mob(3000)
    assert keeper is not None
    keeper.move_to_room(ch.room)

    # Create a wand with partial charges: total=10, remaining=5
    wand = spawn_object(3031)
    assert wand is not None
    wand.prototype.short_descr = 'a test wand'
    wand.prototype.item_type = int(ItemType.WAND)
    wand.prototype.cost = 100
    vals = wand.prototype.value
    vals[1] = 10  # total
    vals[2] = 5   # remaining
    ch.add_object(wand)

    # Shop profit_sell for keeper 3000 is 15%; base sell price = 100*15/100 = 15
    # With 5/10 charges remaining → 15 * 5 / 10 = 7 (integer division)
    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        out = process_command(ch, 'sell wand')
        assert out.endswith('7 gold.')

        # If shop already has an inventory copy of the same wand, price halves
        copy = spawn_object(3031)
        assert copy is not None
        copy.prototype.short_descr = 'a test wand'
        copy.prototype.item_type = int(ItemType.WAND)
        copy.prototype.cost = 100
        copy.prototype.value[1] = 10
        copy.prototype.value[2] = 5
        # Mark as ITEM_INVENTORY using the port's bit (1<<18)
        copy.prototype.extra_flags |= (1 << 18)
        keeper.inventory.append(copy)

        wand2 = spawn_object(3031)
        wand2.prototype.short_descr = 'a test wand'
        wand2.prototype.item_type = int(ItemType.WAND)
        wand2.prototype.cost = 100
        wand2.prototype.value[1] = 10
        wand2.prototype.value[2] = 5
        ch.add_object(wand2)
        out2 = process_command(ch, 'sell wand')
        # Base 15 → charge scaling 7 → inventory half → 3
        assert out2.endswith('3 gold.')
    finally:
        time_info.hour = previous_hour


def test_shop_respects_open_hours():
    initialize_world('area/area.lst')
    char = create_test_character('Captain patron', 3001)
    char.gold = 500
    keeper = spawn_mob(3006)
    assert keeper is not None
    keeper.move_to_room(char.room)

    raft = spawn_object(3050)
    assert raft is not None
    raft.prototype.short_descr = 'a small river raft'
    raft.prototype.item_type = int(ItemType.BOAT)
    raft.prototype.cost = 200
    keeper.inventory.append(raft)

    canoe = spawn_object(3051)
    assert canoe is not None
    canoe.prototype.short_descr = 'a spare canoe'
    canoe.prototype.item_type = int(ItemType.BOAT)
    canoe.prototype.cost = 180
    char.add_object(canoe)

    previous_hour = time_info.hour
    try:
        time_info.hour = 3
        closed_list = process_command(char, 'list')
        assert closed_list == 'Sorry, I am closed. Come back later.'
        assert process_command(char, 'buy raft') == 'Sorry, I am closed. Come back later.'
        assert process_command(char, 'sell canoe') == 'Sorry, I am closed. Come back later.'

        time_info.hour = 23
        closed_list_night = process_command(char, 'list')
        assert closed_list_night == 'Sorry, I am closed. Come back tomorrow.'
        assert process_command(char, 'buy raft') == 'Sorry, I am closed. Come back tomorrow.'
        assert process_command(char, 'sell canoe') == 'Sorry, I am closed. Come back tomorrow.'

        time_info.hour = 10
        listing = process_command(char, 'list')
        assert 'small river raft' in listing
        before_gold = char.gold
        buy_msg = process_command(char, 'buy raft')
        assert 'buy a small river raft' in buy_msg.lower()
        assert char.gold < before_gold

        after_buy_gold = char.gold
        sell_msg = process_command(char, 'sell canoe')
        assert 'sell a spare canoe' in sell_msg.lower()
        assert char.gold > after_buy_gold
    finally:
        time_info.hour = previous_hour


def test_shop_refuses_invisible_customers():
    initialize_world('area/area.lst')
    char = create_test_character('Sneaky patron', 3001)
    char.gold = 500
    char.add_affect(AffectFlag.INVISIBLE)
    keeper = spawn_mob(3006)
    assert keeper is not None
    keeper.move_to_room(char.room)

    raft = spawn_object(3050)
    assert raft is not None
    raft.prototype.short_descr = 'a small river raft'
    raft.prototype.item_type = int(ItemType.BOAT)
    raft.prototype.cost = 200
    keeper.inventory.append(raft)

    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        denied = process_command(char, 'list')
        assert denied == "I don't trade with folks I can't see."

        keeper.affected_by = getattr(keeper, 'affected_by', 0) | int(AffectFlag.DETECT_INVIS)
        allowed = process_command(char, 'list')
        assert 'small river raft' in allowed
    finally:
        time_info.hour = previous_hour


def test_shop_respects_keeper_wealth():
    initialize_world('area/area.lst')
    char = create_test_character('Consigner', 3001)
    char.gold = 0
    keeper = spawn_mob(3006)
    assert keeper is not None
    keeper.move_to_room(char.room)

    canoe = spawn_object(3051)
    assert canoe is not None
    canoe.prototype.short_descr = 'a spare canoe'
    canoe.prototype.item_type = int(ItemType.BOAT)
    canoe.prototype.cost = 180
    char.add_object(canoe)

    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        keeper.gold = 1
        keeper.silver = 0
        denied = process_command(char, 'sell canoe')
        assert denied == "I'm afraid I don't have enough wealth to buy that."
        assert char.gold == 0
        assert canoe in char.inventory
        assert canoe not in keeper.inventory

        keeper.gold = 2
        keeper.silver = 0
        accepted = process_command(char, 'sell canoe')
        assert accepted.endswith('162 gold.')
        assert char.gold == 162
        assert canoe not in char.inventory
        assert canoe in keeper.inventory
        assert keeper.gold == 0
        assert keeper.silver == 38
    finally:
        time_info.hour = previous_hour
