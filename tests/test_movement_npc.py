from mud.models.character import Character
from mud.models.constants import Direction, Sector
from mud.models.room import Exit, Room
from mud.world.movement import move_character


def test_npc_moves_without_boat_or_move_cost() -> None:
    start = Room(vnum=4000, name="Dock", sector_type=int(Sector.WATER_NOSWIM))
    target = Room(vnum=4001, name="Lake", sector_type=int(Sector.WATER_NOSWIM))
    # Light both rooms so room_is_dark() is deterministically False. These are
    # outdoor WATER_NOSWIM sectors, so without an explicit light room_is_dark()
    # falls through to the global time_info.sunlight state — making the test
    # order-dependent (passes only when a prior test left it daytime). Lighting
    # is incidental to this test's intent (NPC moves with no boat / no move cost).
    start.light = 1
    target.light = 1
    start.exits[Direction.NORTH.value] = Exit(to_room=target, keyword="waterway")

    npc = Character(name="Guard", is_npc=True, move=0)
    start.add_character(npc)

    result = move_character(npc, "north")

    assert result and "You walk" not in result  # ROM act_move.c:204 — mover sees room, no walk-line
    assert npc.room is target
    assert npc.move == 0
    assert npc.wait == 0
