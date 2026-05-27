"""ARITH-011 / ARITH-012 regression: max_hit floor in do_berserk / do_flee.

Pins the deliberate Python divergence documented in
`docs/divergences/UB_DIVISORS.md`. ROM `src/fight.c:2310` and the matching
`src/act_move.c` do_flee compute `hp_percent = 100 * ch->hit / ch->max_hit`
raw — SIGFPE if `max_hit == 0`. The Python port floors `max_hit` to 1 at
`mud/commands/combat.py:512` (berserk) and `:636` (flee) so a single
corrupt-state character cannot crash the game loop for every other player.

NPC mob protos with degenerate `hit_dice` (e.g. `(0,0,0)`) spawn with
`max_hit == 0` via `mud/spawning/templates.py:170-172`, so do_flee is
genuinely reachable. do_berserk is PC-only and harder to reach, but is
pinned alongside for consistency.
"""

from __future__ import annotations

from unittest.mock import patch

from mud.commands.combat import do_berserk, do_flee
from mud.models.constants import Position


class TestMaxHitFloorDivergence:
    """Per docs/divergences/UB_DIVISORS.md — the floors must not be removed."""

    def test_berserk_with_zero_max_hit_does_not_raise(self, movable_char_factory):
        """ARITH-011: do_berserk on a max_hit=0 character returns a string,
        not ZeroDivisionError. Mirrors the Python floor at combat.py:512."""
        char = movable_char_factory("warrior", 3001)
        char.skills["berserk"] = 75
        char.position = Position.STANDING
        char.mana = 100
        char.move = 100
        char.hit = 0
        char.max_hit = 0  # ROM would SIGFPE on the hp_percent divide.

        with patch("mud.commands.combat.rng_mm.number_percent", return_value=50):
            result = do_berserk(char, "")

        assert isinstance(result, str)
        assert result  # non-empty: the floor produced a valid hp_percent path

    def test_flee_with_zero_max_hit_does_not_raise(self, movable_char_factory):
        """ARITH-012: do_flee on a fighting max_hit=0 character returns a
        string, not ZeroDivisionError. Mirrors the Python floor at
        combat.py:636. Reachable via degenerate NPC mob protos."""
        char = movable_char_factory("fleer", 3001)
        opponent = movable_char_factory("attacker", 3001)
        char.fighting = opponent
        char.position = Position.FIGHTING
        char.wait = 0
        char.hit = 0
        char.max_hit = 0  # ROM would SIGFPE on the hp_percent divide.

        with patch("mud.commands.combat.rng_mm.number_percent", return_value=100):
            # roll=100 > chance guarantees the "PANIC!" branch — we only
            # need to confirm hp_percent computed without crashing before
            # the chance check at combat.py:641.
            result = do_flee(char, "")

        assert isinstance(result, str)
        assert result
