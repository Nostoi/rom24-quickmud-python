# Session Status — 2026-05-23 — TELL-006 + PROMPT-CMD-004/005 closed (hygiene pass)

## Current State

- **Last completed**: **TELL-006 (analyzed-inert)** released as 2.8.53 (`bd21cba`), then **PROMPT-CMD-004 + PROMPT-CMD-005** released jointly as 2.8.54 (`e9f026c`). With these the channel-message arc (`act_comm.c`) and the `do_prompt` warm-up shelf (`act_info.c`) are both fully closed. PMOTE-001 (`do_pmote` greenfield port) is the only open item on the act_comm.c file.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-23_TELL_006_AND_PROMPT_CMD_HYGIENE.md](SESSION_SUMMARY_2026-05-23_TELL_006_AND_PROMPT_CMD_HYGIENE.md)
- **Earlier summaries this run**:
  - [SESSION_SUMMARY_2026-05-23_SHOUT_YELL_CLUSTER.md](SESSION_SUMMARY_2026-05-23_SHOUT_YELL_CLUSTER.md) (2.8.49-2.8.52)
  - [SESSION_SUMMARY_2026-05-22_TELL_CLUSTER.md](SESSION_SUMMARY_2026-05-22_TELL_CLUSTER.md) (2.8.44-2.8.48)
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
| Version | 2.8.54 |
| Tests | **4631 passed, 4 skipped** (full suite, ~6m 10s) |
| Cross-file invariants | INV-001..009 (all ✅ ENFORCED) |
| `nanny.c` audit | 100% gap rows ✅ |
| `act_info.c::do_prompt` | ✅ PROMPT-CMD-001/002/003/004/005 all FIXED |
| `act_comm.c::do_say` | ✅ 100% RE-AUDITED (SAY-001/002/003/004) |
| `act_comm.c::do_emote` | EMOTE-001/002 ✅; PMOTE-001 ❌ MISSING (stable-IDed) |
| `act_comm.c::do_tell` | ✅ 100% RE-AUDITED (TELL-001..005 FIXED, TELL-006 ANALYZED-INERT) |
| `act_comm.c::do_shout` | ✅ 100% RE-AUDITED (SHOUT-001/002/003) |
| `act_comm.c::do_yell` | ✅ 100% RE-AUDITED (YELL-001) |
| Shared visibility helper | `mud/world/vision.py:pers` used by all 5 channel commands |
| GitNexus index | stale (last analyze at `de1893f`); re-run with `npx gitnexus analyze --skip-agents-md` before next session that needs it. |
| Local commits not pushed | 2 (`bd21cba`, `e9f026c`) + this handoff — waiting on explicit user push approval. |

## Next Intended Task

Channel-message arc + do_prompt warm-up shelf both complete. Three
reasonable continuations:

1. **Combat death messaging** (recommended). Same PERS gap pattern
   the channel arc just normalized; `pers()` helper is warm;
   integration test fixtures already in-hand. Likely cluster of
   IDs around `mud/combat/engine.py` and
   `mud/handler.py:extract_obj/raw_kill` against `src/fight.c`'s
   `dam_message` / `raw_kill` act() lines.
2. **PMOTE-001** — `do_pmote` greenfield port (~50 lines of ROM C
   with per-recipient second-person name substitution +
   apostrophe/possessive handling). Larger; its own session.
3. **New audit target outside act_comm.c / act_info.c**. Tracker
   priorities: healer / shop / train / practice transactional
   commands (`act_obj.c` / `act_wiz.c`).

## Operational follow-ups

- `log/orphaned_helps.txt` still tracked and drifts on test runs. Consider `git rm --cached log/orphaned_helps.txt` + `.gitignore` entry in a small future hygiene commit.
- GitNexus 32 KB scope-extractor failures persist on the documented file list (see CLAUDE.md "Known GitNexus Indexing Gap").
