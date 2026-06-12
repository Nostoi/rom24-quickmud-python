"""FIGHT-060 — check_assist NPC elif chain misses ASSIST_ALIGN/ASSIST_VNUM
when ASSIST_RACE flag is set but race doesn't match.

ROM src/fight.c:137-178 check_assist NPC-assist block uses a flat || OR chain:

    if ((IS_NPC(rch) && IS_SET(rch->off_flags, ASSIST_ALL))
        || (IS_NPC(rch) && rch->group && rch->group == ch->group)
        || (IS_NPC(rch) && rch->race == ch->race
                && IS_SET(rch->off_flags, ASSIST_RACE))          /* cond3 */
        || (IS_NPC(rch) && IS_SET(rch->off_flags, ASSIST_ALIGN)  /* cond4 */
                && ((IS_GOOD(rch) && IS_GOOD(ch)) || ...))
        || ...)

C's || is evaluated condition-by-condition; if cond3 is FALSE (race mismatch),
cond4 (ASSIST_ALIGN) is still evaluated.

Python's elif chain entered the ASSIST_RACE branch (flag set), found no race
match, left should_assist=False — and skipped the elif ASSIST_ALIGN branch
entirely.  A mob with ASSIST_RACE|ASSIST_ALIGN of a different race but same
alignment never assisted, desyncing the MM RNG stream.
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


def _make_npc(name: str, *, race: int = 0, alignment: int = 0) -> Character:
    ch = create_test_character(name, _PLAIN_ROOM)
    ch.is_npc = True
    ch.level = 20
    ch.act = 0
    ch.off_flags = 0
    ch.affected_by = 0
    ch.alignment = alignment
    ch.race = race
    ch.master = None
    ch.fighting = None
    ch.leader = None
    ch.group = 0
    return ch


def test_fight060_assist_align_fires_when_race_flag_set_but_race_differs(monkeypatch) -> None:
    """ASSIST_ALIGN must trigger even when ASSIST_RACE flag is set but race doesn't match.

    ROM src/fight.c:139-178 — all NPC assist conditions are evaluated as a single ||
    chain; a non-matching ASSIST_RACE does not prevent ASSIST_ALIGN from being checked.
    """
    # ch = NPC attacker (race=1/elf, good alignment)
    attacker = _make_npc("Elf", race=1, alignment=500)

    # rch = NPC bystander (race=0/human — DIFFERENT from attacker)
    # but GOOD alignment (SAME as attacker) → ASSIST_ALIGN should fire
    assister = _make_npc("Goblin", race=0, alignment=500)
    assister.off_flags = int(OffFlag.ASSIST_RACE | OffFlag.ASSIST_ALIGN)

    # victim = target ch is attacking (PC-like, different room not needed here)
    victim = _make_npc("Victim", race=0, alignment=0)
    victim.is_npc = False

    attacker.fighting = victim

    # multi_hit call recorder — we assert it fires for the assister
    multi_hit_calls: list[tuple] = []

    def mock_multi_hit(ch, v, dt):
        multi_hit_calls.append((ch, v, dt))

    monkeypatch.setattr(_assist_module, "multi_hit", mock_multi_hit)

    # Bypass vision check — focuses on assist logic, not lighting/invis system
    monkeypatch.setattr(_assist_module, "can_see_character", lambda _o, _t: True)

    # Bypass is_safe — we're testing assist logic, not safety
    monkeypatch.setattr(_assist_module, "is_safe", lambda _a, _v: False)

    # Pass the 50% skip guard — mirroring ROM src/fight.c:156-157
    monkeypatch.setattr(rng_mm, "number_bits", lambda _: 1)

    # Target-selection: first call returns 0 so victim is chosen as target
    monkeypatch.setattr(rng_mm, "number_range", lambda lo, hi: 0)

    check_assist(attacker, victim)

    # mirroring ROM src/fight.c:173-175 — ASSIST_ALIGN should cause rch to assist
    assert multi_hit_calls, (
        "Expected assister to call multi_hit via ASSIST_ALIGN "
        "(ASSIST_RACE flag set but race differs — ROM falls through to ASSIST_ALIGN; "
        "Python's elif chain skips it). "
        f"off_flags={assister.off_flags!r}, attacker.race={attacker.race}, "
        f"assister.race={assister.race}, alignment={assister.alignment}"
    )
    assert multi_hit_calls[0][0] is assister, "assister (Goblin) should be the one attacking"
    assert multi_hit_calls[0][1] is victim, "victim should be the target"


def test_fight060_assist_vnum_fires_when_race_flag_set_but_race_differs(monkeypatch) -> None:
    """ASSIST_VNUM must trigger even when ASSIST_RACE flag is set but race doesn't match.

    Mirrors the same || fallthrough: cond3 false (race mismatch) → cond5 (ASSIST_VNUM) checked.
    """
    attacker = _make_npc("Troll", race=2, alignment=0)
    attacker.vnum = 100

    assister = _make_npc("Clone", race=0, alignment=0)  # different race
    assister.off_flags = int(OffFlag.ASSIST_RACE | OffFlag.ASSIST_VNUM)
    assister.vnum = 100  # same vnum as attacker

    victim = _make_npc("Victim", race=0, alignment=0)
    victim.is_npc = False
    attacker.fighting = victim

    multi_hit_calls: list[tuple] = []

    def mock_multi_hit(ch, v, dt):
        multi_hit_calls.append((ch, v, dt))

    monkeypatch.setattr(_assist_module, "multi_hit", mock_multi_hit)
    monkeypatch.setattr(_assist_module, "can_see_character", lambda _o, _t: True)
    monkeypatch.setattr(_assist_module, "is_safe", lambda _a, _v: False)
    monkeypatch.setattr(rng_mm, "number_bits", lambda _: 1)
    monkeypatch.setattr(rng_mm, "number_range", lambda lo, hi: 0)

    check_assist(attacker, victim)

    # mirroring ROM src/fight.c:149-150 — ASSIST_VNUM should cause rch to assist
    assert multi_hit_calls, (
        "Expected assister to call multi_hit via ASSIST_VNUM "
        "(ASSIST_RACE flag set but race differs — ROM falls through to ASSIST_VNUM). "
        f"off_flags={assister.off_flags!r}, attacker.vnum={attacker.vnum}, "
        f"assister.vnum={assister.vnum}"
    )
