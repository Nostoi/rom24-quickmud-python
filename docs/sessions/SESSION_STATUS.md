# Session Status — 2026-05-22 — `do_prompt` command-side parity (PROMPT-CMD-001/002)

## Current State

- **Last completed**: **PROMPT-CMD-001 + PROMPT-CMD-002** released as 2.8.36. `do_prompt` now preserves trailing whitespace in custom templates (dispatcher + handler) and the success reply echoes the stored template ROM-exact. Surfaced by 2.8.35's NANNY-SAVELOAD-002 probe; fixed in the same session as a contained warm-up.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-22_PROMPT_CMD_PARITY.md](SESSION_SUMMARY_2026-05-22_PROMPT_CMD_PARITY.md)
- **Earlier summaries this run**:
  - [SESSION_SUMMARY_2026-05-22_NANNY_SAVELOAD_RUNTIME_PATH.md](SESSION_SUMMARY_2026-05-22_NANNY_SAVELOAD_RUNTIME_PATH.md) (2.8.35)
  - [SESSION_SUMMARY_2026-05-22_INV009_REGISTRY_DISCONNECT_CLEANUP.md](SESSION_SUMMARY_2026-05-22_INV009_REGISTRY_DISCONNECT_CLEANUP.md) (2.8.34)
  - [SESSION_SUMMARY_2026-05-22_NANNY_RECONNECT_RUNTIME_PATH_PARITY.md](SESSION_SUMMARY_2026-05-22_NANNY_RECONNECT_RUNTIME_PATH_PARITY.md) (2.8.33)
  - [SESSION_SUMMARY_2026-05-22_NANNY_CREATION_TRANSCRIPT_AND_RETRY_PARITY.md](SESSION_SUMMARY_2026-05-22_NANNY_CREATION_TRANSCRIPT_AND_RETRY_PARITY.md) (2.8.32)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.36 |
| Tests | **4608 passed, 4 skipped** (full suite, ~6m 25s) |
| Cross-file invariants | INV-001..009 (all ✅ ENFORCED) |
| `nanny.c` audit | 100% gap rows ✅ (NANNY-001..014 + NANNY-RETRY-001..006 + NANNY-RECONNECT-001..003 + NANNY-SAVELOAD-001..003) |
| Plan Task 4 (parity trust rebuild) | ✅ Complete |
| GitNexus index | stale (last analyze at `de1893f`); re-run with `npx gitnexus analyze --skip-agents-md` before next session that needs it. |

## Next Intended Task

The 2.8.33 → 2.8.36 arc closes a clean trust-rebuild loop on `nanny.c`
+ `save.c` reconnect / save-reload / prompt-command surfaces. Two
natural next directions:

1. **Plan Task 5 — re-audit a high-risk command family.** Tracker
   priority order: healer / shop / train / practice → communication
   (`say` / `tell` / `emote` / `pose` / `pmote`) → notes / boards →
   combat death messaging. Recommendation: start with `say` (lowest
   blast radius — no targeting) and walk `src/act_comm.c` end-to-end
   with Mode-B transcript-parity tests for self-message and
   room-broadcast wording.

2. **PROMPT-CMD-003 (`smash_tilde` on the prompt template)** as one
   more contained warm-up. ROM `src/act_info.c:945` runs `smash_tilde`
   before storing `ch->prompt`. Python's `do_prompt` doesn't. Low
   stakes — only matters if the template contains `~`, which is the
   ROM pfile delimiter — but cheap to add.

## Operational follow-ups

- `log/orphaned_helps.txt` is still tracked and drifts on test runs. Consider `git rm --cached log/orphaned_helps.txt` + `.gitignore` entry in a small future hygiene commit.
- GitNexus 32 KB scope-extractor failures persist on the documented file list (see CLAUDE.md "Known GitNexus Indexing Gap"). `mud/commands/dispatcher.py` is on it — fall back to grep + full suite when `gitnexus_impact` reports clean on hot symbols there.
