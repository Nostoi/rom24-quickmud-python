"""MOVE-003 — directional movement must show the destination room, not a
non-ROM "You walk <dir> to <room>." line.

ROM `src/act_move.c:204` ends move_char with `do_function(ch, &do_look, "auto")`:
the mover sees the destination room description. ROM sends NO "you walk" line to
the mover (others get "$n leaves"/"$n has arrived"). The Python port previously
returned `"You walk {dir} to {room}."`, which the dispatcher delivered to the
player as an extra, non-ROM line. Surfaced by the differential harness
(FINDING-003).
"""

from __future__ import annotations

from mud.commands.dispatcher import process_command
from mud.world import create_test_character, initialize_world


def test_directional_move_emits_room_description_not_walk_line():
    initialize_world()
    char = create_test_character("Mover", 3001)
    char.move = 100

    result = process_command(char, "north")

    # The move succeeded (left room 3001).
    assert char.room is not None and char.room.vnum != 3001
    # ROM mover output is the destination room, not a "You walk ..." line.
    assert "You walk" not in result  # mirrors ROM src/act_move.c:204 (do_look "auto")
    assert char.room.name in result
