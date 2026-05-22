# Session Status — 2026-05-22 — `nanny.c` / `save.c` save → reload runtime-path parity

## Current State

- **Last completed**: **NANNY-SAVELOAD-001/002/003** released as 2.8.35. Three Mode-B round-trip tests on the live websocket path lock in `wimpy`, custom prompt template, and per-character aliases against drift. Plan Task 4 (parity trust rebuild) is **complete**.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-22_NANNY_SAVELOAD_RUNTIME_PATH.md](SESSION_SUMMARY_2026-05-22_NANNY_SAVELOAD_RUNTIME_PATH.md)
- **Earlier summaries this run**:
  - [SESSION_SUMMARY_2026-05-22_INV009_REGISTRY_DISCONNECT_CLEANUP.md](SESSION_SUMMARY_2026-05-22_INV009_REGISTRY_DISCONNECT_CLEANUP.md) (2.8.34)
  - [SESSION_SUMMARY_2026-05-22_NANNY_RECONNECT_RUNTIME_PATH_PARITY.md](SESSION_SUMMARY_2026-05-22_NANNY_RECONNECT_RUNTIME_PATH_PARITY.md) (2.8.33)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.35 |
| Tests | **4606 passed, 4 skipped** (full suite, ~7m 26s) |
| Cross-file invariants | INV-001..009 (all ✅ ENFORCED) |
| `nanny.c` audit | 100% gap rows ✅ (NANNY-001..014 + NANNY-RETRY-001..006 + NANNY-RECONNECT-001..003 + NANNY-SAVELOAD-001..003) |
| Plan Task 4 (`docs/superpowers/plans/2026-05-21-parity-trust-rebuild-reaudit.md`) | ✅ Complete |
| GitNexus index | stale (last analyze at `de1893f`); re-run with `npx gitnexus analyze --skip-agents-md` before next session that needs it. |

## Next Intended Task

Two solid candidates:

1. **Plan Task 5 — re-audit a high-risk user-visible command family.**
   Tracker priority order: healer / shop / train / practice → communication (`say` / `tell` / `emote` / `pose` / `pmote`) → notes / boards → combat death messaging. Pick one and convert weak smoke tests to Mode-B transcript-parity assertions, same pattern as the NANNY-RECONNECT / NANNY-SAVELOAD slices.

2. **PROMPT-CMD parity slice** (surfaced by NANNY-SAVELOAD-002 probe):
   - **PROMPT-CMD-001** — `do_prompt` argument-parsing parity: the dispatcher strips trailing whitespace from `prompt <template>` before `do_prompt` sees the arg. ROM `src/act_info.c:944` preserves it via raw `argument`.
   - **PROMPT-CMD-002** — `do_prompt` success-reply parity: Python emits `"Prompt set."`; ROM emits `"Prompt set to <template>\n\r"` (`src/act_info.c:953-954`) which echoes the stored template back to the player.
   Small, contained, one-test-each, good warm-up.

## Operational follow-ups

- `log/orphaned_helps.txt` is still tracked and drifts on test runs. Consider `git rm --cached log/orphaned_helps.txt` + `.gitignore` entry in a small future hygiene commit.
- GitNexus 32 KB scope-extractor failures persist on the documented file list (see CLAUDE.md "Known GitNexus Indexing Gap"). `mud/account/account_manager.py` and `mud/net/connection.py` are both on it — fall back to grep + full suite when `gitnexus_impact` reports clean on hot symbols in those files.
