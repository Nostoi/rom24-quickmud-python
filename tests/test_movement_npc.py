from mud.models.character import Character
from mud.models.constants import Direction, Sector
from mud.models.room import Exit, Room
from mud.world.movement import move_character


def test_npc_moves_without_boat_or_move_cost() -> None:
    start = Room(vnum=4000, name="Dock", sector_type=int(Sector.WATER_NOSWIM))
    target = Room(vnum=4001, name="Lake", sector_type=int(Sector.WATER_NOSWIM))
    start.exits[Direction.NORTH.value] = Exit(to_room=target, keyword="waterway")

    npc = Character(name="Guard", is_npc=True, move=0)
    start.add_character(npc)

    result = move_character(npc, "north")

    assert "You walk north" in result
    assert npc.room is target
    assert npc.move == 0
    assert npc.wait == 0
