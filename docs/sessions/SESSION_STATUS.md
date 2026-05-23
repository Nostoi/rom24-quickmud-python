# Session Status — 2026-05-22 — `do_say` re-audit complete (SAY-001..004)

## Current State

- **Last completed**: **SAY-002** released as 2.8.41 (`7465ac0`). `do_say` now substitutes `$n` per-listener through a ROM-faithful `PERS()` helper (`mud/world/vision.py:pers`), so invisible/hidden speakers render as `"someone"` to unaided listeners. Closes the four-gap `do_say` re-audit cluster (SAY-001/002/003/004 all ✅).
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-22_SAY_002_PERS.md](SESSION_SUMMARY_2026-05-22_SAY_002_PERS.md)
- **Earlier summaries this run**:
  - [SESSION_SUMMARY_2026-05-22_SAY_CLUSTER_AND_PROMPT_TILDE.md](SESSION_SUMMARY_2026-05-22_SAY_CLUSTER_AND_PROMPT_TILDE.md) (2.8.37-2.8.40)
  - [SESSION_SUMMARY_2026-05-22_PROMPT_CMD_PARITY.md](SESSION_SUMMARY_2026-05-22_PROMPT_CMD_PARITY.md) (2.8.36)
  - [SESSION_SUMMARY_2026-05-22_NANNY_SAVELOAD_RUNTIME_PATH.md](SESSION_SUMMARY_2026-05-22_NANNY_SAVELOAD_RUNTIME_PATH.md) (2.8.35)
  - [SESSION_SUMMARY_2026-05-22_INV009_REGISTRY_DISCONNECT_CLEANUP.md](SESSION_SUMMARY_2026-05-22_INV009_REGISTRY_DISCONNECT_CLEANUP.md) (2.8.34)
  - [SESSION_SUMMARY_2026-05-22_NANNY_RECONNECT_RUNTIME_PATH_PARITY.md](SESSION_SUMMARY_2026-05-22_NANNY_RECONNECT_RUNTIME_PATH_PARITY.md) (2.8.33)
  - [SESSION_SUMMARY_2026-05-22_NANNY_CREATION_TRANSCRIPT_AND_RETRY_PARITY.md](SESSION_SUMMARY_2026-05-22_NANNY_CREATION_TRANSCRIPT_AND_RETRY_PARITY.md) (2.8.32)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.41 |
| Tests | **4616 passed, 4 skipped** (full suite, ~7m 35s) |
| Cross-file invariants | INV-001..009 (all ✅ ENFORCED; INV-001 SINGLE-DELIVERY enforcement strengthened by `do_say` single-delivery test) |
| `nanny.c` audit | 100% gap rows ✅ |
| `act_info.c::do_prompt` | PROMPT-CMD-001/002/003 ✅ FIXED; PROMPT-CMD-004/005 stable-IDed (corner cases) |
| `act_comm.c::do_say` | ✅ 100% RE-AUDITED (SAY-001/002/003/004 all ✅ FIXED) |
| New shared helper | `mud/world/vision.py:pers(target, observer)` mirrors ROM `PERS()`; usable for `do_tell`/`do_emote`/`do_shout`/etc. |
| GitNexus index | stale (last analyze at `de1893f`); re-run with `npx gitnexus analyze --skip-agents-md` before next session that needs it. |
| Local commits not pushed | 1 (`7465ac0`) — waiting on explicit user push approval. |

## Next Intended Task

The `do_say` re-audit cluster is done and the reusable `pers()`
helper is now in place. Three natural next directions:

1. **`do_emote` / `do_pose` / `do_pmote` re-audit** —
   structurally identical to `do_say` and likely to have the same
   PERS-divergence + colour-code + wording bugs. Fast cluster to
   close now that the helper exists.
2. **`do_tell` re-audit** — high-traffic; PERS impact may be
   limited (recipient receives by direct lookup) but worth
   verifying broadcast wording and any sibling `act()` paths.
3. **`do_shout` / `do_yell` channels** — per-listener PERS cost
   is higher (global broadcast) but ROM does it. Verify single
   delivery (INV-001) and PERS substitution.

Lower-priority warm-ups still stable-IDed: PROMPT-CMD-004
(50-char truncation), PROMPT-CMD-005 (`%c`-suffix → append
trailing space).

## Operational follow-ups

- `log/orphaned_helps.txt` still tracked and drifts on test runs. Consider `git rm --cached log/orphaned_helps.txt` + `.gitignore` entry in a small future hygiene commit.
- GitNexus 32 KB scope-extractor failures persist on the documented file list (see CLAUDE.md "Known GitNexus Indexing Gap").
