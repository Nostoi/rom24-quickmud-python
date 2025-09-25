from __future__ import annotations

from mud.commands import process_command
from mud.world import create_test_character, initialize_world


def setup_function(_):
    initialize_world("area/area.lst")


def test_ex_abbreviation_resolves_to_exits_command():
    ch = create_test_character("Tester", 3001)
    out = process_command(ch, "ex")
    assert out.lower().startswith("obvious exits:")
    # Midgaard temple starting room usually has at least one exit
    assert any(d in out.lower() for d in ("north", "east", "south", "west", "up", "down"))


def test_prefix_tie_breaker_uses_first_in_table_order_for_say():
    ch = create_test_character("Tester", 3001)
    out = process_command(ch, "sa hello")
    assert out == "You say, 'hello'"
