# Session Summary — 2026-06-09 — ENTER-019 portal followers

## Scope

Continued from `SESSION_SUMMARY_2026-06-09_FINDING026_ROOM_PEOPLE_ORDER.md`.
The active mode remained divergence Class 11 / dynamic differential widening.
The prior handoff listed `nuke_pets` lifecycle probing and `TRIG_ENTRY` call-site
coverage as candidates; this session re-read ROM portal/directional follower
contracts in `act_enter.c` and `act_move.c` and closed a narrow portal follower
visibility divergence.

## Outcomes

### `ENTER-019` — ✅ FIXED

- **Python**: `mud/world/movement.py:_move_followers`,
  `move_character`, `move_character_through_portal`
- **ROM C**: `src/act_enter.c:177-198`, compared with
  `src/act_move.c:216-219`
- **Gap**: `ENTER-019` — portal followers were silently pre-skipped by the
  directional follower `can_see_room` gate.
- **Fix**: `_move_followers` now takes `require_destination_visibility`.
  Directional movement passes `True`, preserving ROM `act_move.c:218`;
  portal movement passes `False`, matching ROM `act_enter.c:190-196` where
  followers attempt recursive `do_enter` before their own destination visibility
  check can reject the portal.
- **Tests**: added
  `tests/integration/test_act_enter_gaps.py::TestEnter012FollowerMessages::test_follower_attempts_portal_before_destination_visibility_gate`
  (locks the observable distinction: portal followers attempt recursive
  `do_enter`, then receive the portal "doesn't seem to go anywhere" rejection
  from their own destination visibility check).

## Files Modified

- `mud/world/movement.py` — split directional vs portal follower destination
  visibility gating.
- `tests/integration/test_act_enter_gaps.py` — added `ENTER-019` regression.
- `docs/parity/ACT_ENTER_C_AUDIT.md` — documented `ENTER-019` as fixed.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — recorded the portal follower probe
  under Class 11 dynamic widening.
- `CHANGELOG.md` — added `2.13.40` fixed entry.
- `pyproject.toml` — `2.13.39` → `2.13.40`.

## Test Status

- `PYTHONPATH=. pytest -q tests/integration/test_act_enter_gaps.py::TestEnter012FollowerMessages::test_follower_attempts_portal_before_destination_visibility_gate tests/test_movement_visibility.py::test_follower_requires_visibility` — 2 passed.
- `PYTHONPATH=. pytest -q tests/integration/test_act_enter_gaps.py tests/test_movement_visibility.py tests/test_movement_followers.py tests/test_movement.py tests/test_movement_portals.py` — 47 passed.
- `ruff check .` — clean.
- `PYTHONPATH=. pytest -q` — 5463 passed, 5 skipped.
- `gitnexus_detect_changes(scope="all")` — low risk, no affected execution flows.

## Next Steps

Continue Class 11 / dynamic differential widening with another deterministic
command/watch-set surface. Good candidates remain `TRIG_ENTRY` ordering coverage
for mob entry paths and non-combat lifecycle probes; `nuke_pets` already has
substantial INV-020/INV-025 coverage, so prefer a source-read probe that can
identify a specific missing observable before editing.
