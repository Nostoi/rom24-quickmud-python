# Session Summary — 2026-06-01 — ENTER-017 portal fade ordering

## Scope

Continued the cross-file invariant probe pass from the MOBPROG-008 session. The probe re-read ROM `src/act_enter.c` portal movement ordering against Python `mud/world/movement.py`, focusing on ENTRY/GREET trigger edges around expiring portals.

## Outcomes

### `ENTER-017` — ✅ FIXED

- **Python**: `mud/world/movement.py:move_character_through_portal`
- **ROM C**: `src/act_enter.c:200-222`
- **Gap**: one-charge portal fade/extract ran after `TRIG_ENTRY` / `mp_greet_trigger` in Python. ROM fades and extracts the portal first, then runs the mobprog trigger block.
- **Fix**: moved the existing `_portal_fade_out(...)` call above the ENTRY/GREET trigger block, after follower handling, matching ROM ordering.
- **Tests**: added `tests/integration/test_act_enter_gaps.py::TestEnter011PortalFadeOut::test_fade_happens_before_greet_trigger`.

## Files Modified

- `mud/world/movement.py` — reordered expiring portal fade before entry/greet mobprog dispatch.
- `tests/integration/test_act_enter_gaps.py` — added a red-first ordering regression.
- `docs/parity/ACT_ENTER_C_AUDIT.md` — filed and closed ENTER-017; refreshed count/status to 16 closed gaps.
- `CHANGELOG.md` — added the ENTER-017 fixed entry.
- `pyproject.toml` — bumped `2.12.25` to `2.12.26`.
- `docs/sessions/SESSION_STATUS.md` — refreshed pointer and next task.

## Test Status

- `pytest -n0 tests/integration/test_act_enter_gaps.py::TestEnter011PortalFadeOut::test_fade_happens_before_greet_trigger -q` — passed.
- `pytest -n0 tests/integration/test_act_enter_gaps.py tests/integration/test_inv025_movement_act_trigger_dispatch.py -q` — 34 passed.
- `ruff check mud/world/movement.py` — clean.
- `ruff check mud/world/movement.py tests/integration/test_act_enter_gaps.py` — not clean because `tests/integration/test_act_enter_gaps.py` has pre-existing unused imports / unused local assignments outside the ENTER-017 change.
- `gitnexus_detect_changes(scope=all)` — low risk, no affected execution flows. Scope includes prior uncommitted MOBPROG-008 changes already in the worktree; ENTER-017 production symbol touched: `mud/world/movement.py:move_character_through_portal`.

## Next Steps

Resume the cross-file invariant probe pass. Good next candidates remain:

1. Review remaining mob-script/movement trigger edges not covered by INV-025/INV-026.
2. Pick a standing candidate: affect ticks, position transitions, or group/follower chain.
3. Optionally clean the pre-existing Ruff issues in `tests/integration/test_act_enter_gaps.py` if a future branch wants targeted lint over that whole file.
