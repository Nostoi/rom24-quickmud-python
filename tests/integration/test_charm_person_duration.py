"""Integration test for ARITH-016 — charm person duration parity.

ROM `src/magic.c:1383` does:

    af.duration = number_fuzzy (level / 4);

with no UMAX(1, ...) guard on the `level / 4` term. The intent matters:
ROM `number_fuzzy(n)` already clamps its OWN return to `UMAX(1, n)`
(`src/db.c:3496`), so passing 0 vs 1 changes the output distribution.

For levels 0–3, ROM passes 0 to number_fuzzy; the 4 RNG branches yield
(roll=0 → -1, roll=1 → 0, roll=2 → 0, roll=3 → 1), all then clamped to 1.
**ROM duration is deterministic 1** for levels 0–3.

Pre-fix `mud/skills/handlers.py:2121` had:

    base_duration = max(1, c_div(level, 4))

so it passed 1 (not 0) to `number_fuzzy` for low levels. The 4 RNG
branches then yield (0 → 0 → 1, 1 → 1, 2 → 1, 3 → 2). Pre-fix Python
gives duration 2 in 25% of low-level charm casts (roll=3 branch).

The test mocks `rng_mm.number_fuzzy` to capture its argument and asserts
that ROM's exact `c_div(level, 4)` value is passed through — i.e. 0 for
level=3.
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.registry import room_registry
from mud.skills import handlers as skill_handlers
from mud.utils import rng_mm


def test_charm_person_passes_raw_level_div_4_to_number_fuzzy(monkeypatch):
    """ARITH-016 — ROM src/magic.c:1383 passes `level / 4` raw to
    number_fuzzy, with NO `UMAX(1, ...)` guard on the dividend. For
    level=3 ROM passes 0; pre-fix Python wrapped it in `max(1, ...)`
    and passed 1, shifting the duration distribution.
    """
    room = Room(vnum=99001, name="Charm Test Hall", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[99001] = room
    try:
        caster = Character(name="Caster", level=3, room=room, is_npc=False, position=Position.STANDING)
        caster.messages = []
        target = Character(name="Target", level=1, room=room, is_npc=True, position=Position.STANDING)
        target.messages = []
        room.people = [caster, target]

        captured: list[int] = []

        def spy_fuzzy(n: int) -> int:
            captured.append(n)
            return max(1, n)  # mirror ROM UMAX behaviour exactly

        monkeypatch.setattr(rng_mm, "number_fuzzy", spy_fuzzy)
        # The handler binds rng_mm at import; patch through the module too.
        monkeypatch.setattr(skill_handlers.rng_mm, "number_fuzzy", spy_fuzzy)

        # Force saves_spell to return False (charm lands) so we reach
        # the duration computation.
        monkeypatch.setattr(skill_handlers, "saves_spell", lambda *_a, **_kw: False)

        # Stub follower wiring — these touch global registries we don't
        # care about for this test.
        monkeypatch.setattr(skill_handlers, "add_follower", lambda *_a, **_kw: None)
        monkeypatch.setattr(skill_handlers, "stop_follower", lambda *_a, **_kw: None)

        skill_handlers.charm_person(caster, target)

        # ROM: number_fuzzy(level / 4) = number_fuzzy(0) for level=3
        assert captured == [0], f"expected number_fuzzy(0), got {captured!r}"
    finally:
        room_registry.pop(99001, None)
