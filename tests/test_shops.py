from mud.world import initialize_world, create_test_character
from mud.commands.dispatcher import process_command
from mud.registry import shop_registry


def test_buy_from_grocer():
    initialize_world('area/area.lst')
    assert 3002 in shop_registry
    char = create_test_character('Buyer', 3010)
    char.gold = 100
    list_output = process_command(char, 'list')
    assert 'hooded brass lantern' in list_output
    assert '40 gold' in list_output
    buy_output = process_command(char, 'buy lantern')
    assert 'buy a hooded brass lantern' in buy_output.lower()
    assert char.gold == 60
    assert any((obj.short_descr or '').lower().startswith('a hooded brass lantern') for obj in char.inventory)
