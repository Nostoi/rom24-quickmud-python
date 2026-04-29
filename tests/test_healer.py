from mud.commands.dispatcher import process_command
from mud.registry import mob_registry
from mud.spawning.mob_spawner import spawn_mob
from mud.world import create_test_character, initialize_world


def place_healer(ch):
    # Use an existing mob prototype and mark it as healer via spec_fun
    proto = mob_registry.get(3000)
    assert proto is not None, "expected stock mob prototype 3000"
    proto.spec_fun = "spec_healer"
    mob = spawn_mob(3000)
    ch.room.add_mob(mob)
    return mob


def test_healer_lists_services_and_prices():
    initialize_world("area/area.lst")
    ch = create_test_character("Buyer", 3001)
    place_healer(ch)
    out = process_command(ch, "heal")
    assert "refresh: restore movement      5 gold" in out
    assert "heal: healing spell          50 gold" in out


def test_healer_refresh_and_heal_effects_and_pricing():
    initialize_world("area/area.lst")
    ch = create_test_character("Buyer", 3001)
    place_healer(ch)
    ch.gold = 60
    ch.max_move = 100
    ch.move = 10
    ch.max_hit = 100
    ch.hit = 20

    out1 = process_command(ch, "heal refresh")
    assert out1 == "You feel less tired."
    assert 10 < ch.move < 100
    assert ch.gold == 55

    out2 = process_command(ch, "heal heal")
    assert out2 == "A warm feeling fills your body."
    assert ch.hit == 100
    assert ch.gold == 5


def test_healer_denies_when_insufficient_gold():
    initialize_world("area/area.lst")
    ch = create_test_character("Buyer", 3001)
    place_healer(ch)
    ch.gold = 0
    out = process_command(ch, "heal heal")
    assert out == "You do not have enough gold for my services."
