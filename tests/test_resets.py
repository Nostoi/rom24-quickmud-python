from mud.game_loop import game_tick
from mud.registry import room_registry
from mud.spawning.templates import MobInstance
from mud.world import initialize_world


def test_execution_cycle(monkeypatch):
    initialize_world("area/area.lst")

    bakery = room_registry[3001]
    donation = room_registry[3054]
    area = bakery.area
    assert area is not None

    bakery.people = [p for p in bakery.people if not isinstance(p, MobInstance)]
    donation.contents.clear()

    area.age = 2
    area.empty = False

    monkeypatch.setattr("mud.game_loop._area_counter", 1)

    game_tick()

    assert any(isinstance(p, MobInstance) for p in bakery.people)
    assert any(getattr(getattr(o, "prototype", None), "vnum", None) == 3010 for o in donation.contents)
