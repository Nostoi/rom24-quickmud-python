"""FIGHT-053 — check_assist target selection increments `number` unconditionally.

ROM src/fight.c:155-170 check_assist NPC-assist target-selection loop:

    number = 0;
    for (vch = ch->in_room->people; vch; vch = vch->next)
    {
        if (can_see (rch, vch)
                && is_same_group (vch, victim)
                && number_range (0, number) == 0)
        {
            target = vch;
            number++;          /* ← increments ONLY on selection */
        }
    }

Python check_assist (mud/combat/assist.py) incremented `number` unconditionally
after each matching group member, regardless of whether that member was chosen:

    if rng_mm.number_range(0, number) == 0:
        target = vch
    number += 1   # ← unconditional — BUG

With 3 visible group members where the 2nd is NOT chosen (number_range returns
non-zero), ROM makes the 3rd call as number_range(0, 1) because number stayed at 1.
Python made the call as number_range(0, 2) because number was incremented anyway.
This desynchronises the shared MM RNG stream for all subsequent combat events.
"""

from __future__ import annotations

import pytest

import mud.combat.assist as _assist_module
from mud.combat.assist import check_assist
from mud.models.character import Character
from mud.models.constants import OffFlag
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world

_PLAIN_ROOM = 2300


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def _make_pc(name: str) -> Character:
    ch = create_test_character(name, _PLAIN_ROOM)
    ch.is_npc = False
    ch.level = 20
    ch.act = 0
    ch.affected_by = 0
    ch.master = None
    ch.fighting = None
    ch.leader = None
    return ch


def _make_npc(name: str) -> Character:
    ch = create_test_character(name, _PLAIN_ROOM)
    ch.is_npc = True
    ch.level = 20
    ch.act = 0
    ch.off_flags = 0
    ch.affected_by = 0
    ch.master = None
    ch.fighting = None
    ch.leader = None
    ch.group = 0
    ch.race = 0
    return ch


def test_fight053_check_assist_number_increments_on_selection_only(monkeypatch) -> None:
    """number++ inside the selection if-block, not unconditionally — ROM src/fight.c:165.

    When the 2nd group member is NOT selected (number_range returns != 0),
    ROM keeps number=1 so the 3rd call uses number_range(0, 1).
    Pre-fix Python gave number_range(0, 2) because number was always incremented.
    """
    # ch = attacker (NPC, fighting victim_a); rch = assister (NPC+ASSIST_ALL)
    attacker = _make_npc("Troll")
    assister = _make_npc("Goblin")
    assister.off_flags = int(OffFlag.ASSIST_ALL)

    # victim_a is group leader; victim_b and victim_c follow
    victim_a = _make_pc("Alice")
    victim_b = _make_pc("Bob")
    victim_c = _make_pc("Carol")
    victim_b.leader = victim_a
    victim_c.leader = victim_a

    attacker.fighting = victim_a

    # Record every (low, high) pair passed to number_range
    recorded_ranges: list[tuple[int, int]] = []
    call_idx = [0]
    # Return sequence: 0 (1st selected), high (2nd skipped), 0 (3rd selected)
    # Using `high` for the 2nd ensures it's always non-zero regardless of range.

    def mock_number_range(low: int, high: int) -> int:
        recorded_ranges.append((low, high))
        idx = call_idx[0]
        call_idx[0] += 1
        if idx == 0:
            return 0  # 1st group member selected
        if idx == 1:
            return high  # 2nd group member NOT selected (non-zero)
        return 0  # 3rd group member selected

    # Bypass vision check — test focuses on RNG sequence, not the vision system.
    # Room 2300 is FOREST sector so darkness depends on time_info.sunlight;
    # patching avoids fragility from that global state.
    monkeypatch.setattr(_assist_module, "can_see_character", lambda _o, _t: True)

    # Pass the 50% skip guard — mirroring ROM src/fight.c:156-157
    monkeypatch.setattr(rng_mm, "number_bits", lambda _: 1)
    monkeypatch.setattr(rng_mm, "number_range", mock_number_range)

    check_assist(attacker, victim_a)

    # At least 3 number_range calls: one per group member from target selection.
    # Extra calls beyond 3 come from mob_hit's unconditional off-skill draws
    # (number_range(0,2) spell-cast check + number_range(0,8) off-flag dispatch)
    # which fire after the assist triggers multi_hit — those are correct ROM draws
    # and are not the subject of this test.
    assert len(recorded_ranges) >= 3, (
        f"Expected at least 3 number_range calls (one per visible group member); "
        f"got {len(recorded_ranges)}: {recorded_ranges}"
    )
    assert recorded_ranges[0] == (0, 0), "1st call: first group member, number=0"
    assert recorded_ranges[1] == (0, 1), "2nd call: second group member, number=1 (first was selected)"
    # mirrors ROM src/fight.c:165 — number only increments on selection.
    # After 2nd member is skipped, number stays at 1, so 3rd gets (0, 1).
    assert recorded_ranges[2] == (0, 1), (
        f"3rd call should be (0, 1) — ROM src/fight.c:165 increments number "
        f"ONLY when a target is selected; 2nd was skipped so number stays 1. "
        f"Got {recorded_ranges[2]}. Pre-fix Python gave (0, 2) because number "
        f"was incremented unconditionally after each visible group member."
    )
