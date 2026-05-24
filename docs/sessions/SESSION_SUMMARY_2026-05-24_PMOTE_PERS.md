# Session Summary — 2026-05-24 — `do_pmote` PERS + NPC-viewer parity (PMOTE-002/003)

## Scope

Closed the two follow-up `do_pmote` gaps identified during the PMOTE-001 re-check:

- `PMOTE-002` — per-viewer `$N` prefix in `do_pmote` now routes through `PERS(ch, vch)` so invisible actors render as `"someone"` to unaided viewers, matching ROM `src/act_comm.c:1136,1188`.
- `PMOTE-003` — pmote/smote viewer loops now skip all `desc == NULL` observers, excluding NPCs exactly like ROM `src/act_comm.c:1130` and `src/act_wiz.c:392-393`.

Two commits landed, one gap per commit:

1. `cdf53dd` — `fix(parity): act_comm:PMOTE-002 — PERS-render pmote actor`
2. `822dcb0` — `fix(parity): act_comm:PMOTE-003 — skip NPC pmote viewers`

## Gaps closed

| ID | ROM ref | Behavior | Test |
|----|---------|----------|------|
| `PMOTE-002` | `src/act_comm.c:1136,1188` | viewer-facing pmote prefix now uses `pers(char, viewer)` instead of leaking `char.name` | `tests/integration/test_act_comm_gaps.py::TestPmoteGaps::test_pmote_002_invisible_actor_renders_as_someone_to_unaided_viewer` |
| `PMOTE-003` | `src/act_comm.c:1130`; `src/act_wiz.c:392-393` | pmote/smote loops now skip any non-self viewer with `desc is None`, excluding NPCs | `tests/integration/test_act_comm_gaps.py::TestPmoteGaps::test_pmote_003_npc_viewers_do_not_receive_pmote_or_smote` |

## Implementation

- `mud/commands/imm_emote.py`
  - `do_pmote` now PERS-renders the actor prefix per recipient with `mud.world.vision.pers`, mirroring ROM's `act("$N $t", ...)` behavior for TO_CHAR delivery.
  - `do_pmote` and `do_smote` now both skip any non-self viewer whose `desc` is `None`, restoring ROM's unconditional `vch->desc == NULL` guard.
- `tests/integration/test_act_comm_gaps.py`
  - Added a failing-first invisible-actor regression for `PMOTE-002`.
  - Added a failing-first NPC-viewer regression covering both `do_pmote` and `do_smote` for `PMOTE-003`.
- `docs/parity/ACT_COMM_C_AUDIT.md`
  - Marked `PMOTE-002` and `PMOTE-003` as `✅ FIXED` with version references and locking tests.
- `CHANGELOG.md`
  - Added `2.8.69` (`PMOTE-002`) and `2.8.70` (`PMOTE-003`) fixed entries.
- `pyproject.toml`
  - Bumped `2.8.68 → 2.8.69 → 2.8.70`.

## Verification

- `pytest tests/integration/test_act_comm_gaps.py -v` ✅ after each gap and after the final slice (29 passed).
- `ruff check .` ❌ unchanged pre-existing repo-wide lint failures outside this worktree slice (notably `.claude/skills/*`, `diagnostic_test.py`, and legacy test modules). No new lint issue introduced by the PMOTE patches.
- `mcp__gitnexus__.detect_changes(scope=\"all\")` ✅ low-risk/local before each commit.

## Files touched

- `mud/commands/imm_emote.py`
- `tests/integration/test_act_comm_gaps.py`
- `docs/parity/ACT_COMM_C_AUDIT.md`
- `CHANGELOG.md`
- `pyproject.toml`

## Next intended task

Reasonable continuations from the current `act_comm.c` shelf:

1. Re-open `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` and pick the next `⚠️ Partial` / `❌ Not Audited` row.
2. If staying on messaging parity, continue scanning `docs/parity/ACT_COMM_C_AUDIT.md` for remaining open channel-command gaps beyond pmote.
3. If a push is desired, ask first — local `master` is ahead and the user explicitly said not to push without approval.
