# Session Status — 2026-05-22 — `nanny.c` reconnect runtime-path parity

## Current State

- **Active audit**: `nanny.c` trust-rebuild (Plan Task 4 — runtime-path verification of post-reconnect first-command transcripts on the live websocket path).
- **Last completed**:
  - `NANNY-RECONNECT-001` (commit `ba79d82`) — `score` after reconnect: ROM-exact title / race / sex / class / resources lines locked in.
  - `NANNY-RECONNECT-002` (commit `6622775`) — `look` after reconnect: room name and description match live registry, not stale snapshot.
  - `NANNY-RECONNECT-003` (commit `600d9d5`) — first in-game prompt after reconnect renders live hp/mana/move (self-consistent with `score`); reset_char confirmed via `hit == max_hit`.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-22_NANNY_RECONNECT_RUNTIME_PATH_PARITY.md](SESSION_SUMMARY_2026-05-22_NANNY_RECONNECT_RUNTIME_PATH_PARITY.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.33 |
| Tests | **4602 passed, 4 skipped** (full suite, ~5m 26s) |
| `nanny.c` audit | 100% gap rows ✅ (NANNY-001..014 + NANNY-RETRY-001..006 + NANNY-RECONNECT-001..003) |
| Ruff on touched files | clean (no new errors vs baseline) |
| GitNexus index | **stale** — last indexed at `0dd803e`; re-run `npx gitnexus analyze --skip-agents-md` |

## Next Intended Task

Two threads, pick either:

1. **Plan Task 4 — save → reload → retained state on real server paths.**
   Still open. Helper tests cover this in isolation; the remaining bullet
   is a Mode-B/Mode-C reconnect-with-state-change test on the live
   websocket path (e.g. change wimpy / prompt / equipment between
   sessions, then verify the reload reflects it on the first command).

2. **Investigate `character_registry` reconnect duplication.** During
   NANNY-RECONNECT-003 debugging, name lookup in `character_registry`
   returned a stale pre-reconnect Character (hp=20) while the live
   reconnect session rendered hp=100. Likely the pre-disconnect entry is
   never removed when the new reconnect session loads a fresh Character
   from DB. Worth a dedicated slice; possibly a new
   "REGISTRY-RECONNECT-DEDUP" cross-file invariant.

Operational follow-ups before pushing:

- Re-run `npx gitnexus analyze --skip-agents-md` so the GitNexus index
  reflects commits `ba79d82`, `6622775`, `600d9d5`, and the handoff
  commit.
- `log/orphaned_helps.txt` is still a tracked file that keeps drifting
  during test runs. Consider `git rm --cached log/orphaned_helps.txt`
  followed by a `.gitignore` entry in a small repo-hygiene commit.
