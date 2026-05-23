# Session Status — 2026-05-23 — channel-message re-audit arc COMPLETE (SHOUT-001..003, YELL-001)

## Current State

- **Last completed**: **SHOUT-001 → SHOUT-002 → SHOUT-003 → YELL-001** released as 2.8.49 → 2.8.52 across four commits (`21f1b80`, `9e55e1a`, `78ad2cb`, `5e9e7fc`). With this slice the entire 5-command channel-message re-audit arc (`do_say`, `do_emote`, `do_tell`, `do_shout`, `do_yell`) is **COMPLETE** — every `$n` substitution routes through `pers()`, every wording matches ROM-exact, every channel that uses ROM colour codes wraps them.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-23_SHOUT_YELL_CLUSTER.md](SESSION_SUMMARY_2026-05-23_SHOUT_YELL_CLUSTER.md)
- **Earlier summaries this run**:
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
| Version | 2.8.52 |
| Tests | **4629 passed, 4 skipped** (full suite, ~6m 15s) |
| Cross-file invariants | INV-001..009 (all ✅ ENFORCED) |
| `nanny.c` audit | 100% gap rows ✅ |
| `act_info.c::do_prompt` | PROMPT-CMD-001/002/003 ✅; 004/005 stable-IDed (corner cases) |
| `act_comm.c::do_say` | ✅ 100% RE-AUDITED (SAY-001/002/003/004) |
| `act_comm.c::do_emote` | EMOTE-001/002 ✅; PMOTE-001 ❌ MISSING (stable-IDed) |
| `act_comm.c::do_tell` | TELL-001/002/003/004/005 ✅; TELL-006 deferred (MINOR cosmetic) |
| `act_comm.c::do_shout` | ✅ 100% RE-AUDITED (SHOUT-001/002/003) |
| `act_comm.c::do_yell` | ✅ 100% RE-AUDITED (YELL-001) |
| Shared visibility helper | `mud/world/vision.py:pers` used by all 5 channel commands |
| GitNexus index | stale (last analyze at `de1893f`); re-run with `npx gitnexus analyze --skip-agents-md` before next session that needs it. |
| Local commits not pushed | 4 (`21f1b80..5e9e7fc`) — waiting on explicit user push approval. |

## Next Intended Task

The 5-command channel-message re-audit arc (say / tell / emote /
shout / yell) is **COMPLETE**. Four reasonable continuations:

1. **PMOTE-001** — `do_pmote` greenfield port. ROM ~50 lines of C
   per-recipient second-person name substitution with apostrophe /
   possessive handling. Larger; its own session.
2. **TELL-006** — uppercase first char of buffered tells. ~5 min
   warm-up.
3. **PROMPT-CMD-004 / PROMPT-CMD-005** — corner-case `do_prompt`
   warm-ups (50-char truncation, `%c`-suffix → append trailing
   space).
4. **New audit target** — outside `act_comm.c`. Tracker priorities:
   healer / shop / train / practice (`act_obj.c` / `act_wiz.c`
   transactional commands), or combat death messaging (which
   likely contains analogous PERS gaps now that `pers()` is
   broadly used).

Recommendation: a **new audit target** (#4) — the act_comm.c
channel arc is fully cleaned up; combat-message `$n` PERS bugs
will be exactly the same pattern as the channel ones and benefit
from the warm helper. Alternatively close the small warm-ups as a
hygiene pass first.

## Operational follow-ups

- `log/orphaned_helps.txt` still tracked and drifts on test runs. Consider `git rm --cached log/orphaned_helps.txt` + `.gitignore` entry in a small future hygiene commit.
- GitNexus 32 KB scope-extractor failures persist on the documented file list (see CLAUDE.md "Known GitNexus Indexing Gap").
