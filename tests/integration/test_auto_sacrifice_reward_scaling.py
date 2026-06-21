"""Regression guard — AUTOSAC silver reward scales with corpse level.

ROM `src/act_obj.c:1822` computes the sacrifice reward as::

    silver = UMAX (1, obj->level * 3);

and the corpse inherits the dead mob's level via
`src/fight.c:1504` ``corpse->level = ch->level``. So a level-1 NPC
corpse yields ``max(1, 1*3) == 3`` silver, a level-2 corpse 6, and a
level-0 corpse the ``UMAX`` floor of 1.

`mud/combat/engine.py:_auto_sacrifice` reproduces this with
``max(1, corpse_level * 3)``. This guard pins the per-level reward so a
future regression that drops ``corpse.level`` back to 0 (the symptom
that surfaced live: a level-1 "wimpy monster" paying only 1 silver
because its corpse came through level 0) fails loudly here instead of
shipping silently — the manual `do_sacrifice` path was covered, but the
AUTOSAC reward amount was previously unguarded (only the flag toggles
and the TO_ROOM broadcast had tests).
"""

from __future__ import annotations

import pytest

from mud.combat.engine import _auto_sacrifice
from mud.models.character import character_registry
from mud.models.constants import ItemType, PlayerFlag, WearFlag
from mud.models.room import Room
from mud.registry import room_registry
from mud.world.world_state import create_test_character


class _MockCorpse:
    """Minimal NPC corpse stand-in satisfying _auto_sacrifice's gates."""

    def __init__(self, level: int, *, room) -> None:
        self.short_descr = "the corpse of a wimpy monster"
        self.name = "corpse"
        self.item_type = int(ItemType.CORPSE_NPC)
        self.wear_flags = int(WearFlag.TAKE)
        self.level = level
        self.contained_items: list = []
        self.location = room
        self.prototype = None


@pytest.mark.parametrize(
    ("corpse_level", "expected_silver", "expected_phrase"),
    [
        (0, 1, "one silver coin"),  # UMAX floor — level-0 snail
        (1, 3, "3 silver coins"),  # the wimpy monster (vnum 3703)
        (2, 6, "6 silver coins"),  # the big creature (vnum 3706)
        (5, 15, "15 silver coins"),  # the beast (vnum 3714)
    ],
)
def test_auto_sacrifice_reward_scales_with_corpse_level(corpse_level, expected_silver, expected_phrase):
    """AUTOSAC pays ``max(1, corpse.level * 3)`` silver — ROM act_obj.c:1822."""
    test_room = Room(vnum=2100, name="Test Room", description="A test room.", room_flags=0, sector_type=0)
    test_room.people = []
    test_room.contents = []
    room_registry[2100] = test_room

    try:
        attacker = create_test_character("Saccer", 2100)
        attacker.level = 1
        attacker.silver = 0
        attacker.act = (getattr(attacker, "act", 0) or 0) | int(PlayerFlag.AUTOSAC)
        attacker.messages = []

        corpse = _MockCorpse(corpse_level, room=test_room)
        _auto_sacrifice(attacker, corpse)

        assert attacker.silver == expected_silver, (
            f"level-{corpse_level} corpse paid {attacker.silver} silver, expected {expected_silver}"
        )
        joined = "\n".join(attacker.messages).lower()
        assert expected_phrase in joined, f"reward message missing '{expected_phrase}': {attacker.messages!r}"

    finally:
        room_registry.pop(2100, None)
        character_registry.clear()
