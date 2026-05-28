"""LOOK-004 — room object listing must use the ROM ground `description`, not
the object's short_descr/name.

ROM `do_look` renders room contents via `show_list_to_char(..., fShort=FALSE)` →
`format_obj_to_char(obj, ch, FALSE)` (`src/act_info.c`), which emits the object's
**`description`** (the long ground line, e.g. "A pit for sacrifices is in front of
the altar.") and skips any object whose description is empty. The Python port
listed `obj.short_descr` ("the donation pit"), the object analog of LOOK-001.
Surfaced by the differential harness (FINDING-004).
"""

from __future__ import annotations

from mud.commands.dispatcher import process_command
from mud.world import create_test_character, initialize_world


def test_room_lists_object_by_ground_description_not_short_descr():
    initialize_world()
    char = create_test_character("Looker", 3054)  # By the Temple Altar — has the donation pit

    result = process_command(char, "look")

    # ROM format_obj_to_char(fShort=FALSE) emits obj->description for ground items.
    assert "A pit for sacrifices is in front of the altar." in result
    # The short_descr ("the donation pit") is NOT the room-listing line in ROM.
    assert "the donation pit" not in result
