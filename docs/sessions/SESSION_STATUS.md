# Session Status — 2026-05-22 — `do_say` re-audit (SAY-001/003/004) + PROMPT-CMD-003

## Current State

- **Last completed**: **PROMPT-CMD-003 → SAY-001 → SAY-004 → SAY-003** released as 2.8.37 → 2.8.40 across four commits (`2aae0fa`, `7d1c332`, `8f44ecd`, `07153fa`). The 2026-05-22 `do_say` re-audit demoted the prior "100% VERIFIED" claim and closed three of four surfaced gaps; SAY-002 deferred intentionally (see below).
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-22_SAY_CLUSTER_AND_PROMPT_TILDE.md](SESSION_SUMMARY_2026-05-22_SAY_CLUSTER_AND_PROMPT_TILDE.md)
- **Earlier summaries this run**:
  - [SESSION_SUMMARY_2026-05-22_PROMPT_CMD_PARITY.md](SESSION_SUMMARY_2026-05-22_PROMPT_CMD_PARITY.md) (2.8.36)
  - [SESSION_SUMMARY_2026-05-22_NANNY_SAVELOAD_RUNTIME_PATH.md](SESSION_SUMMARY_2026-05-22_NANNY_SAVELOAD_RUNTIME_PATH.md) (2.8.35)
  - [SESSION_SUMMARY_2026-05-22_INV009_REGISTRY_DISCONNECT_CLEANUP.md](SESSION_SUMMARY_2026-05-22_INV009_REGISTRY_DISCONNECT_CLEANUP.md) (2.8.34)
  - [SESSION_SUMMARY_2026-05-22_NANNY_RECONNECT_RUNTIME_PATH_PARITY.md](SESSION_SUMMARY_2026-05-22_NANNY_RECONNECT_RUNTIME_PATH_PARITY.md) (2.8.33)
  - [SESSION_SUMMARY_2026-05-22_NANNY_CREATION_TRANSCRIPT_AND_RETRY_PARITY.md](SESSION_SUMMARY_2026-05-22_NANNY_CREATION_TRANSCRIPT_AND_RETRY_PARITY.md) (2.8.32)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.40 |
| Tests | **4614 passed, 4 skipped** (full suite, ~6m 53s) |
| Cross-file invariants | INV-001..009 (all ✅ ENFORCED; INV-001 SINGLE-DELIVERY now has one more enforcement test — `do_say` single-delivery) |
| `nanny.c` audit | 100% gap rows ✅ |
| `act_info.c::do_prompt` | PROMPT-CMD-001/002/003 ✅ FIXED; PROMPT-CMD-004/005 stable-IDed (corner cases) |
| `act_comm.c::do_say` | SAY-001/003/004 ✅ FIXED; **SAY-002 🔄 OPEN** (needs `can_see`/`pers` helpers — see below) |
| GitNexus index | stale (last analyze at `de1893f`); re-run with `npx gitnexus analyze --skip-agents-md` before next session that needs it. |
| Local commits not pushed | 4 (`2aae0fa..07153fa`) — waiting on explicit user push approval |

## Next Intended Task

**SAY-002 — `$n` PERS substitution for invisible/hidden speakers.**
This is the deferred slice of the `do_say` re-audit. ROM `act()`
routes the speaker name through `PERS()`:

```c
#define PERS(ch, looker) (can_see (looker, ch) ? \
    (IS_NPC(ch) ? ch->short_descr : ch->name) : "someone")
```

Python hardcodes `char.name`, leaking invisible/hidden PC names when
they speak. Proper close needs:

1. New `can_see(observer, target)` helper consulting
   `AffectFlag.INVISIBLE` / `HIDDEN`, blindness, room darkness +
   detect-invis / detect-hidden / infrared affects.
2. New `pers(target, observer)` helper using `can_see`.
3. Refactor `do_say` (and likely every `act()`-shaped Python
   broadcast site) to render the message per-listener.
4. Integration tests for invisible / hidden / blind-observer / dark
   cases.

100–200 lines of new subsystem code. Likely surfaces analogous
CRITICAL gaps in `do_tell`, `do_shout`, `do_yell`, `do_emote` once
the helper exists — audit and close those in the same arc.

Alternative warm-ups if you'd rather start small:

- **PROMPT-CMD-004** — 50-char truncation on `do_prompt`. Trivial.
- **PROMPT-CMD-005** — `%c`-suffix → append trailing space on `do_prompt`. Trivial.

Both are stable-IDed in `docs/parity/ACT_INFO_C_AUDIT.md`. No
behavioural payoff for typical play.

## Operational follow-ups

- `log/orphaned_helps.txt` still tracked and drifts on test runs. Consider `git rm --cached log/orphaned_helps.txt` + `.gitignore` entry in a small future hygiene commit.
- GitNexus 32 KB scope-extractor failures persist on the documented file list (see CLAUDE.md "Known GitNexus Indexing Gap"). `mud/commands/dispatcher.py` is on it — fall back to grep + full suite when `gitnexus_impact` reports clean on hot symbols there.
