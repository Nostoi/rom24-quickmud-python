from mud.world import initialize_world, create_test_character
from mud.commands.dispatcher import process_command
from mud.registry import shop_registry
from mud.spawning.obj_spawner import spawn_object


def test_buy_from_grocer():
    initialize_world('area/area.lst')
    assert 3002 in shop_registry
    char = create_test_character('Buyer', 3010)
    char.gold = 100
    list_output = process_command(char, 'list')
    assert 'hooded brass lantern' in list_output
    assert '60 gold' in list_output
    buy_output = process_command(char, 'buy lantern')
    assert 'buy a hooded brass lantern' in buy_output.lower()
    assert char.gold == 40
    assert any((obj.short_descr or '').lower().startswith('a hooded brass lantern') for obj in char.inventory)


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
