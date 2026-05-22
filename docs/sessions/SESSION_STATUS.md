# Session Status — 2026-05-22 — `do_prompt` smash_tilde parity (PROMPT-CMD-003)

## Current State

- **Last completed**: **PROMPT-CMD-003** released as 2.8.37. `do_prompt` now runs `smash_tilde` on the custom template before storing it on `char.prompt`, matching ROM `src/act_info.c:945`. Closes the PROMPT-CMD cluster opened by 2.8.35's NANNY-SAVELOAD-002 probe.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-22_PROMPT_CMD_SMASH_TILDE.md](SESSION_SUMMARY_2026-05-22_PROMPT_CMD_SMASH_TILDE.md)
- **Earlier summaries this run**:
  - [SESSION_SUMMARY_2026-05-22_PROMPT_CMD_PARITY.md](SESSION_SUMMARY_2026-05-22_PROMPT_CMD_PARITY.md) (2.8.36)
  - [SESSION_SUMMARY_2026-05-22_NANNY_SAVELOAD_RUNTIME_PATH.md](SESSION_SUMMARY_2026-05-22_NANNY_SAVELOAD_RUNTIME_PATH.md) (2.8.35)
  - [SESSION_SUMMARY_2026-05-22_INV009_REGISTRY_DISCONNECT_CLEANUP.md](SESSION_SUMMARY_2026-05-22_INV009_REGISTRY_DISCONNECT_CLEANUP.md) (2.8.34)
  - [SESSION_SUMMARY_2026-05-22_NANNY_RECONNECT_RUNTIME_PATH_PARITY.md](SESSION_SUMMARY_2026-05-22_NANNY_RECONNECT_RUNTIME_PATH_PARITY.md) (2.8.33)
  - [SESSION_SUMMARY_2026-05-22_NANNY_CREATION_TRANSCRIPT_AND_RETRY_PARITY.md](SESSION_SUMMARY_2026-05-22_NANNY_CREATION_TRANSCRIPT_AND_RETRY_PARITY.md) (2.8.32)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.37 |
| Tests | **4609 passed, 4 skipped** (full suite, ~5m 52s) |
| Cross-file invariants | INV-001..009 (all ✅ ENFORCED) |
| `nanny.c` audit | 100% gap rows ✅ (NANNY-001..014 + NANNY-RETRY-001..006 + NANNY-RECONNECT-001..003 + NANNY-SAVELOAD-001..003) |
| `act_info.c::do_prompt` | PROMPT-CMD-001/002/003 ✅ FIXED; PROMPT-CMD-004/005 stable-IDed (corner cases) |
| Plan Task 4 (parity trust rebuild) | ✅ Complete |
| GitNexus index | stale (last analyze at `de1893f`); re-run with `npx gitnexus analyze --skip-agents-md` before next session that needs it. |

## Next Intended Task

**Plan Task 5 — `say` command audit** (`src/act_comm.c`). Per the
tracker priority order, communication is the next high-traffic
command family to re-audit, and `say` has the lowest blast radius
(no targeting). Workflow:

1. Invoke `rom-parity-audit` against `act_comm.c` (or just the
   `do_say` slice if the full file is too broad for one session) to
   produce `docs/parity/ACT_COMM_C_AUDIT.md` with stable gap IDs.
2. Gap-close per ID via `rom-gap-closer` (one test, one commit).
3. Session-handoff when the chosen scope is closed.

Optional corner-case warm-up before Plan Task 5: PROMPT-CMD-004
(50-char truncation) or PROMPT-CMD-005 (`%c`-suffix → append space).
Both are tiny and self-contained, but no behavioral payoff for
typical play — only worth it if you want another low-friction warm-up
slice before the meatier `act_comm.c` work.

## Operational follow-ups

- `log/orphaned_helps.txt` is still tracked and drifts on test runs. Consider `git rm --cached log/orphaned_helps.txt` + `.gitignore` entry in a small future hygiene commit.
- GitNexus 32 KB scope-extractor failures persist on the documented file list (see CLAUDE.md "Known GitNexus Indexing Gap"). `mud/commands/dispatcher.py` is on it — fall back to grep + full suite when `gitnexus_impact` reports clean on hot symbols there.
