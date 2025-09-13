from mud.world import initialize_world, create_test_character
from mud.commands.dispatcher import process_command
from mud.registry import shop_registry
from mud.spawning.obj_spawner import spawn_object


def test_buy_from_grocer():
    initialize_world('area/area.lst')
    assert 3002 in shop_registry
    char = create_test_character('Buyer', 3010)
    char.gold = 100
    # Ensure grocer has at least one lantern in stock for this test
    keeper = next((p for p in char.room.people if getattr(p, 'prototype', None) and p.prototype.vnum in shop_registry), None)
    if keeper is not None and not any(((obj.short_descr or '').lower().startswith('a hooded brass lantern') for obj in keeper.inventory)):
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


def test_list_price_matches_buy_price():
    initialize_world('area/area.lst')
    assert 3002 in shop_registry
    char = create_test_character('Buyer', 3010)
    char.gold = 100
    out = process_command(char, 'list')
    # Extract first price number from list output
    import re
    m = re.search(r"(\d+) gold", out)
    assert m
    price = int(m.group(1))
    before = char.gold
    name = 'lantern' if 'lantern' in out.lower() else out.split(':')[-1].split()[0]
    out2 = process_command(char, f'buy {name}')
    assert char.gold == before - price


def test_sell_to_grocer():
    initialize_world('area/area.lst')
    char = create_test_character('Seller', 3010)
    char.gold = 0
    lantern = spawn_object(3031)
    assert lantern is not None
    lantern.prototype.item_type = 1
    char.add_object(lantern)
    sell_output = process_command(char, 'sell lantern')
    assert 'sell a hooded brass lantern' in sell_output.lower()
    assert char.gold == 16
    keeper = next(
        p for p in char.room.people if getattr(p, 'prototype', None) and p.prototype.vnum in shop_registry
    )
    assert any(
        (obj.short_descr or '').lower().startswith('a hooded brass lantern') for obj in keeper.inventory
    )


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
