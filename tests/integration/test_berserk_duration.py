"""Integration test for ARITH-015 — berserk duration parity.

ROM `src/fight.c:2333`:

    af.duration = number_fuzzy (ch->level / 8);

raw, with NO UMAX(1, ...) guard on the dividend. `number_fuzzy` itself
already clamps to `UMAX(1, n)` (`src/db.c:3496`), so passing 0 vs 1
changes the OUTPUT distribution.

For levels 0–7, ROM passes 0 to number_fuzzy and gets a deterministic
duration of 1. Pre-fix `mud/skills/handlers.py:1445` wrapped the
dividend in `max(1, ...)` and passed 1, giving duration 2 in 25% of
low-level berserks.
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Position
from mud.skills import handlers as skill_handlers
from mud.utils import rng_mm


def test_berserk_passes_raw_level_div_8_to_number_fuzzy(monkeypatch):
    """ARITH-015 — ROM `src/fight.c:2333` passes `ch->level / 8` raw to
    number_fuzzy. For level=4 ROM passes 0; pre-fix Python wrapped it in
    `max(1, ...)` and passed 1.
    """
    caster = Character(
        name="Berserker",
        level=4,
        is_npc=False,
        position=Position.FIGHTING,
    )
    caster.messages = []

    captured: list[int] = []

    def spy_fuzzy(n: int) -> int:
        captured.append(n)
        return max(1, n)  # mirror ROM UMAX(1, n) behaviour

    monkeypatch.setattr(rng_mm, "number_fuzzy", spy_fuzzy)
    monkeypatch.setattr(skill_handlers.rng_mm, "number_fuzzy", spy_fuzzy)

    skill_handlers.berserk(caster)

    # ROM: number_fuzzy(level / 8) = number_fuzzy(0) for level=4
    assert captured == [0], f"expected number_fuzzy(0), got {captured!r}"
