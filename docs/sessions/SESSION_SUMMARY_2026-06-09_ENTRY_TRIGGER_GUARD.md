# Session Summary — 2026-06-09 — Entry trigger guard

## Scope

Continued from `SESSION_SUMMARY_2026-06-09_ENTER019_PORTAL_FOLLOWERS.md`.
The active mode remained divergence Class 11 / dynamic differential widening.
The prior handoff suggested `TRIG_ENTRY` ordering coverage, so this session
re-read the post-move mobprog blocks in ROM `act_move.c` and `act_enter.c` and
closed a narrow missing `HAS_TRIGGER(ch, TRIG_ENTRY)` precondition.

## Outcomes

### `MOVE-007` / `ENTER-020` — ✅ FIXED

- **Python**: `mud/world/movement.py:move_character`,
  `mud/world/movement.py:move_character_through_portal`
- **ROM C**: `src/act_move.c:240-243`, `src/act_enter.c:219-222`
- **Gap**: NPC directional and portal movement dispatched
  `mp_percent_trigger(..., TRIG_ENTRY)` even when the moving NPC had no
  `TRIG_ENTRY` bit.
- **Fix**: both post-move NPC entry dispatches now gate on
  `char.mprog_flags & Trigger.ENTRY`, preserving the separate PC-only
  `mp_greet_trigger` path.
- **Tests**: added directional and portal negative cases in
  `tests/test_movement_mobprog.py`; updated the existing positive entry-trigger
  tests to set `mprog_flags`.

## Files Modified

- `mud/world/movement.py` — added the ROM `HAS_TRIGGER(TRIG_ENTRY)` gate at
  directional and portal NPC entry trigger sites.
- `tests/test_movement_mobprog.py` — added regression coverage for NPCs without
  `TRIG_ENTRY`; positive case now declares the trigger flag.
- `tests/test_mobprog_triggers.py` — made the broad event-hook fixture declare
  `TRIG_ENTRY` before expecting an entry event.
- `docs/parity/ACT_MOVE_C_AUDIT.md` — documented `MOVE-007` as fixed.
- `docs/parity/ACT_ENTER_C_AUDIT.md` — documented `ENTER-020` as fixed.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — recorded the Class 11 probe.
- `CHANGELOG.md` — added `2.13.41` fixed entry.
- `pyproject.toml` — `2.13.40` → `2.13.41`.

## Test Status

- `PYTHONPATH=. pytest -q tests/test_movement_mobprog.py` — 3 passed.
- `PYTHONPATH=. pytest -q tests/test_movement_mobprog.py tests/test_mobprog_triggers.py tests/test_movement.py tests/test_movement_followers.py tests/test_movement_portals.py tests/test_movement_visibility.py tests/integration/test_inv025_movement_act_trigger_dispatch.py tests/integration/test_act_enter_gaps.py` — 67 passed.
- `ruff check .` — clean.
- `PYTHONPATH=. pytest -q` — 5465 passed, 5 skipped.

## Next Steps

Continue Class 11 / dynamic differential widening on another deterministic
command/watch-set surface. Good next candidates: mob entry/greet ordering with
real `mprog_flags` and a concrete observable, or a non-combat lifecycle probe
that can be compared against primary ROM source before editing. Avoid
duplicating `nuke_pets` unless a fresh ROM/Python read exposes a specific
missing contract.
