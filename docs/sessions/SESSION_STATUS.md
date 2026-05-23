# Session Status — 2026-05-22 — `do_emote` re-audit (EMOTE-001/002 closed; PMOTE-001 stable-IDed)

## Current State

- **Last completed**: **EMOTE-001 + EMOTE-002** released as 2.8.42 (`4c61270`) and 2.8.43 (`e10aa0f`). Same PERS substitution + TO_CHAR-"You" pattern as the `do_say` cluster, closed in two TDD commits. PMOTE-001 (`do_pmote` not implemented in Python) stable-IDed as ❌ MISSING for a future session.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-22_EMOTE_CLUSTER.md](SESSION_SUMMARY_2026-05-22_EMOTE_CLUSTER.md)
- **Earlier summaries this run**:
  - [SESSION_SUMMARY_2026-05-22_SAY_002_PERS.md](SESSION_SUMMARY_2026-05-22_SAY_002_PERS.md) (2.8.41)
  - [SESSION_SUMMARY_2026-05-22_SAY_CLUSTER_AND_PROMPT_TILDE.md](SESSION_SUMMARY_2026-05-22_SAY_CLUSTER_AND_PROMPT_TILDE.md) (2.8.37-2.8.40)
  - [SESSION_SUMMARY_2026-05-22_PROMPT_CMD_PARITY.md](SESSION_SUMMARY_2026-05-22_PROMPT_CMD_PARITY.md) (2.8.36)
  - [SESSION_SUMMARY_2026-05-22_NANNY_SAVELOAD_RUNTIME_PATH.md](SESSION_SUMMARY_2026-05-22_NANNY_SAVELOAD_RUNTIME_PATH.md) (2.8.35)
  - [SESSION_SUMMARY_2026-05-22_INV009_REGISTRY_DISCONNECT_CLEANUP.md](SESSION_SUMMARY_2026-05-22_INV009_REGISTRY_DISCONNECT_CLEANUP.md) (2.8.34)
  - [SESSION_SUMMARY_2026-05-22_NANNY_RECONNECT_RUNTIME_PATH_PARITY.md](SESSION_SUMMARY_2026-05-22_NANNY_RECONNECT_RUNTIME_PATH_PARITY.md) (2.8.33)
  - [SESSION_SUMMARY_2026-05-22_NANNY_CREATION_TRANSCRIPT_AND_RETRY_PARITY.md](SESSION_SUMMARY_2026-05-22_NANNY_CREATION_TRANSCRIPT_AND_RETRY_PARITY.md) (2.8.32)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.43 |
| Tests | **4619 passed, 4 skipped** (full suite, ~6m 28s) |
| Cross-file invariants | INV-001..009 (all ✅ ENFORCED) |
| `nanny.c` audit | 100% gap rows ✅ |
| `act_info.c::do_prompt` | PROMPT-CMD-001/002/003 ✅; 004/005 stable-IDed (corner cases) |
| `act_comm.c::do_say` | ✅ 100% RE-AUDITED (SAY-001/002/003/004) |
| `act_comm.c::do_emote` | EMOTE-001/002 ✅ FIXED; PMOTE-001 ❌ MISSING (stable-IDed) |
| Shared visibility helpers | `mud/world/vision.py:pers` + `can_see_character` cover SAY-002, EMOTE-001, and any future act()-shaped channel |
| GitNexus index | stale (last analyze at `de1893f`); re-run with `npx gitnexus analyze --skip-agents-md` before next session that needs it. |
| Local commits not pushed | 2 (`4c61270`, `e10aa0f`) — waiting on explicit user push approval. |

## Next Intended Task

`do_say` ✅ done. `do_emote` ✅ done (modulo PMOTE-001 stub). Three
natural next directions, listed in increasing complexity:

1. **`do_tell` re-audit** — verify TO_CHAR / TO_VICT wording and
   PERS for the `"$N tells you '$t'"` line. High-traffic, well-bounded.
2. **`do_shout` / `do_yell` channels** — global broadcasts; per-listener
   PERS cost higher but ROM does it. Verify INV-001 single-delivery.
3. **PMOTE-001** — greenfield port of ROM `do_pmote` (~50 lines C with
   per-recipient second-person name substitution). Larger; its own
   session.

Plus corner-case warm-ups still on the shelf: PROMPT-CMD-004
(50-char truncation), PROMPT-CMD-005 (`%c`-suffix → append trailing
space).

## Operational follow-ups

- `log/orphaned_helps.txt` still tracked and drifts on test runs. Consider `git rm --cached log/orphaned_helps.txt` + `.gitignore` entry in a small future hygiene commit.
- GitNexus 32 KB scope-extractor failures persist on the documented file list (see CLAUDE.md "Known GitNexus Indexing Gap").
