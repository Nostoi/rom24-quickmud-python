"""GROUPS-001 — `do_groups` (no arg) must list known groups, not crash.

ROM `do_groups` (`src/skills.c`) lists the groups a player knows. Python stores
`pcdata.group_known` as a `tuple[str, ...]` of known group NAMES
(`mud/models/character.py:213`), but the no-arg branch treated it as a dict —
`sorted(group_known.keys())` / `group_known[name]` — which raises
`AttributeError: 'tuple' object has no attribute 'keys'` for any player who
actually knows a group.
"""

from __future__ import annotations

from mud.commands.remaining_rom import do_groups
from mud.models.character import Character, PCData


def test_do_groups_lists_known_groups_without_crashing() -> None:
    char = Character(name="Learner", level=10, is_npc=False)
    char.pcdata = PCData()
    char.pcdata.group_known = ("attack", "mage basics")

    out = do_groups(char, "")

    assert "Your known groups" in out
    assert "attack" in out
    assert "mage basics" in out


def test_do_groups_no_known_groups_shows_none() -> None:
    char = Character(name="Learner", level=10, is_npc=False)
    char.pcdata = PCData()
    char.pcdata.group_known = ()

    out = do_groups(char, "")

    assert "Your known groups" in out
    assert "(none)" in out
