"""FIGHT-025 — combat act() output capitalizes its first rendered character.

ROM `act_new` (`src/comm.c:2373-2379`) capitalizes the first character of every
rendered act() line, accounting for a leading colour code::

    if (buf[0] == 123)        /* '{' */
        buf[2] = UPPER (buf[2]);
    else
        buf[0] = UPPER (buf[0]);

So ``{4the drunk's beating hits you.{x`` is sent as ``{4The drunk's beating
hits you.{x``. Python's combat render chokepoint `render_for` (which "mirrors
ROM's act() macro") substituted the PERS placeholders but never capitalized, so
an NPC-initiated swing rendered lowercase ("the drunk's ...") — FINDING-009
facet 4 (the last step-5 render diff in the `combat_melee_rounds` differential).

These tests pin the ROM `act_new` capitalization at `render_for`: the char after
a leading ``{X`` colour code (index 2) is upper-cased, else index 0.
"""

from __future__ import annotations

from mud.combat.messages import render_for
from mud.spawning.mob_spawner import spawn_mob
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world


def _drunk_and_victim():
    rng_mm.seed_mm(777)
    drunk = spawn_mob(3064)  # PERS → "the drunk"
    assert drunk is not None
    victim = create_test_character("Victim", 3008)
    victim.room.add_character(drunk)
    return drunk, victim


def test_render_for_capitalizes_char_after_leading_color_code():
    initialize_world()
    drunk, victim = _drunk_and_victim()

    # The dam_message TO_VICT template opens with a doubled colour code ({{4 ->
    # {4 after .format), so ROM capitalizes index 2 (the first letter of PERS).
    out = render_for("{{4{attacker}'s beating hits you.{{x", drunk, victim, victim)
    assert out.startswith("{4The drunk's beating hits you."), out
    assert "the drunk's beating" not in out  # no leftover lowercase opener


def test_render_for_capitalizes_first_char_without_color_code():
    initialize_world()
    drunk, victim = _drunk_and_victim()

    # No leading colour code → ROM capitalizes index 0.
    out = render_for("{attacker} hits you.", drunk, victim, victim)
    assert out.startswith("The drunk hits you."), out


def test_render_for_leaves_already_capital_opener_unchanged():
    initialize_world()
    drunk, victim = _drunk_and_victim()

    # "You ..." (the TO_CHAR perspective) is already capital — capitalization is
    # a no-op, never a corruption.
    out = render_for("{{2You miss {victim}.{{x", drunk, victim, drunk)
    assert out.startswith("{2You miss "), out
