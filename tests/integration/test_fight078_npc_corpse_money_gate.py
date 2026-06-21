"""FIGHT-078 — NPC corpse money is gated on gold > 0 (ROM src/fight.c:1473).

ROM `make_corpse` for an NPC creates the corpse money object only inside
`if (ch->gold > 0)`; a mob carrying silver but zero gold therefore drops NO
money object and the silver is lost on extraction. Python previously used a
unified `gold > 0 or silver > 0` gate, dropping phantom silver into the corpse.

Surfaced by the `death_corpse_loot_sacrifice` differential scenario
(tools/diff_harness/FINDINGS.md FINDING-038).
"""

from __future__ import annotations

from mud.combat.death import make_corpse
from mud.models.character import Character, character_registry
from mud.models.constants import ItemType
from mud.world import create_test_character, initialize_world


def _money_objects(corpse) -> list:
    return [obj for obj in corpse.contained_items if int(getattr(obj, "item_type", 0)) == int(ItemType.MONEY)]


def _make_npc(room, *, gold: int, silver: int) -> Character:
    victim = Character(name="janitor", is_npc=True, level=1)
    victim.short_descr = "the janitor"
    victim.hit = victim.max_hit = 1
    victim.gold = gold
    victim.silver = silver
    room.add_character(victim)
    return victim


def test_fight078_silver_only_npc_corpse_has_no_money() -> None:
    """gold == 0, silver > 0 → ROM creates no money object (fight.c:1473)."""
    initialize_world("area/area.lst")
    character_registry.clear()
    driver = create_test_character("Tester", 3001)
    room = driver.room
    assert room is not None

    victim = _make_npc(room, gold=0, silver=17)
    corpse = make_corpse(victim)
    assert corpse is not None

    # ROM make_corpse NPC branch only mints money when ch->gold > 0; the 17
    # silver is lost, NOT dropped into the corpse.
    assert _money_objects(corpse) == []


def test_fight078_gold_bearing_npc_corpse_keeps_money() -> None:
    """gold > 0 → ROM mints a money object carrying full gold + silver (regression guard)."""
    initialize_world("area/area.lst")
    character_registry.clear()
    driver = create_test_character("Tester", 3001)
    room = driver.room
    assert room is not None

    victim = _make_npc(room, gold=5, silver=17)
    corpse = make_corpse(victim)
    assert corpse is not None

    money = _money_objects(corpse)
    assert len(money) == 1
    # ROM create_money(gold, silver): value[1]=gold, value[0]=silver.
    assert money[0].value[1] == 5
    assert money[0].value[0] == 17
