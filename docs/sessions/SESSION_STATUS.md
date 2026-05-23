# Session Status — 2026-05-22 — `do_tell` re-audit (TELL-001..005 closed; TELL-006 deferred)

## Current State

- **Last completed**: **TELL-001 → TELL-002 → TELL-003 → TELL-004 → TELL-005** released as 2.8.44 → 2.8.48 across five commits (`4ff037a`, `c4cb39b`, `c2f9aa8`, `3aabbe8`, `7f64764`). The 2026-05-22 `do_tell` re-audit demoted another "100% VERIFIED" claim and closed five of six surfaced gaps; TELL-006 (MINOR cosmetic — uppercase first char of buffered tells) deferred.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-22_TELL_CLUSTER.md](SESSION_SUMMARY_2026-05-22_TELL_CLUSTER.md)
- **Earlier summaries this run**:
  - [SESSION_SUMMARY_2026-05-22_EMOTE_CLUSTER.md](SESSION_SUMMARY_2026-05-22_EMOTE_CLUSTER.md) (2.8.42-2.8.43)
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
| Version | 2.8.48 |
| Tests | **4625 passed, 4 skipped** (full suite, ~6m 38s) |
| Cross-file invariants | INV-001..009 (all ✅ ENFORCED) |
| `nanny.c` audit | 100% gap rows ✅ |
| `act_info.c::do_prompt` | PROMPT-CMD-001/002/003 ✅; 004/005 stable-IDed (corner cases) |
| `act_comm.c::do_say` | ✅ 100% RE-AUDITED (SAY-001/002/003/004) |
| `act_comm.c::do_emote` | EMOTE-001/002 ✅; PMOTE-001 ❌ MISSING (stable-IDed) |
| `act_comm.c::do_tell` | TELL-001/002/003/004/005 ✅; TELL-006 deferred (MINOR cosmetic) |
| Shared visibility helper | `mud/world/vision.py:pers` now used by 4 commands (do_say, do_emote, do_tell TO_CHAR, do_tell TO_VICT) |
| GitNexus index | stale (last analyze at `de1893f`); re-run with `npx gitnexus analyze --skip-agents-md` before next session that needs it. |
| Local commits not pushed | 5 (`4ff037a..7f64764`) — waiting on explicit user push approval. |

## Next Intended Task

Four channel-command audits this run: `do_say` ✅, `do_emote` ✅,
`do_tell` ✅, and the still-open broadcast channels. Four natural
next directions, in order of recommendation:

1. **`do_shout` / `do_yell` re-audit** — last two channel commands.
   Likely same audit-doc inflation; expect SHOUT-NNN / YELL-NNN
   gaps for wording, colour, PERS. Completes the major
   channel-command quartet (say/tell/emote/shout/yell).
2. **PMOTE-001** — greenfield port of ROM `do_pmote` (~50 lines C
   with per-recipient second-person name substitution). Larger;
   own session.
3. **TELL-006** — uppercase first char of buffered tells. Quick
   warm-up.
4. **PROMPT-CMD-004 / PROMPT-CMD-005** — corner-case `do_prompt`
   warm-ups still stable-IDed.

## Operational follow-ups

- `log/orphaned_helps.txt` still tracked and drifts on test runs. Consider `git rm --cached log/orphaned_helps.txt` + `.gitignore` entry in a small future hygiene commit.
- GitNexus 32 KB scope-extractor failures persist on the documented file list (see CLAUDE.md "Known GitNexus Indexing Gap").
