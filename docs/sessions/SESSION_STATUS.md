# Session Status — 2026-05-22 — INV-009 REGISTRY-DISCONNECT-CLEANUP

## Current State

- **Active focus**: cross-file invariants surfaced during NANNY-RECONNECT trust rebuild.
- **Last completed**: **INV-009 REGISTRY-DISCONNECT-CLEANUP** (released as 2.8.34). Two root causes fixed in one commit: (a) `load_character` now dedupes by name on append, eliminating the level=0 bare-row → level=1 promoted-row duplicate inside a single creation flow; (b) websocket + telnet disconnect cleanup now removes the Character from `character_registry`, eliminating the cross-session leak. New enforcement test + invariant row.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-22_INV009_REGISTRY_DISCONNECT_CLEANUP.md](SESSION_SUMMARY_2026-05-22_INV009_REGISTRY_DISCONNECT_CLEANUP.md)
- **Prior summary in this run**: [SESSION_SUMMARY_2026-05-22_NANNY_RECONNECT_RUNTIME_PATH_PARITY.md](SESSION_SUMMARY_2026-05-22_NANNY_RECONNECT_RUNTIME_PATH_PARITY.md) (2.8.33).

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.34 |
| Tests | **4603 passed, 4 skipped** (full suite, ~6m 10s) |
| Cross-file invariants | INV-001..009 (all ✅ ENFORCED) |
| `nanny.c` audit | 100% gap rows ✅ (NANNY-001..014 + NANNY-RETRY-001..006 + NANNY-RECONNECT-001..003) |
| GitNexus index | re-indexed at start of session; 32 KB scope-extractor failures persist on documented file list — `load_character` and disconnect path are on it, so `gitnexus_impact` cannot be trusted on those symbols. |

## Next Intended Task

1. **Plan Task 4 — save → reload → retained state on the live websocket reconnect path.** Pattern follows the NANNY-RECONNECT trio in 2.8.33: change state mid-session (wimpy / prompt template / equipment), disconnect, reconnect, assert live state on first command matches what was set pre-disconnect.

2. **Optional follow-on**: add a dedicated INV-009-on-telnet enforcement test (the patch covers both paths via identical edits, but only the websocket path has a direct regression). Low priority — full telnet suite is green.

3. **Repo hygiene**: `log/orphaned_helps.txt` is still tracked and keeps drifting on test runs. Consider `git rm --cached log/orphaned_helps.txt` + `.gitignore` entry in a small future commit.
