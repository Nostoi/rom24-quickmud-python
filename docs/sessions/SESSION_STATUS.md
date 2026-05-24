# Session Status — 2026-05-23 — `fight.c` PERS sweep closed (FIGHT-004..008)

## Current State

- **Last completed**: **FIGHT-004..008** (position-change broadcast surface in `_position_change_message`) released as 2.8.55 → 2.8.59 across five TDD commits, plus a small PROMPT-CMD-005 legacy-test mop-up at 2.8.60. With this slice the entire position-change-broadcast surface in `mud/combat/engine.py` routes `$n` through `pers()` and emits ROM-exact wording / colour codes. The same channel-arc PERS pattern now covers say / tell / emote / shout / yell / position-change.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-23_FIGHT_C_PERS_SWEEP.md](SESSION_SUMMARY_2026-05-23_FIGHT_C_PERS_SWEEP.md)
- **Earlier summaries this run**:
  - [SESSION_SUMMARY_2026-05-23_TELL_006_AND_PROMPT_CMD_HYGIENE.md](SESSION_SUMMARY_2026-05-23_TELL_006_AND_PROMPT_CMD_HYGIENE.md) (2.8.53-2.8.54)
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
| Version | 2.8.60 |
| Tests | **4632 passed, 4 skipped** (full suite, ~7m 30s) |
| Cross-file invariants | INV-001..009 (all ✅ ENFORCED) |
| `nanny.c` audit | 100% gap rows ✅ |
| `act_info.c::do_prompt` | ✅ PROMPT-CMD-001..005 all FIXED |
| `act_comm.c::do_say` | ✅ 100% RE-AUDITED (SAY-001..004) |
| `act_comm.c::do_emote` | EMOTE-001/002 ✅; PMOTE-001 ❌ MISSING (stable-IDed) |
| `act_comm.c::do_tell` | ✅ 100% RE-AUDITED (TELL-001..005 FIXED, TELL-006 ANALYZED-INERT) |
| `act_comm.c::do_shout` | ✅ 100% RE-AUDITED (SHOUT-001..003) |
| `act_comm.c::do_yell` | ✅ 100% RE-AUDITED (YELL-001) |
| `fight.c::_position_change_message` | ✅ FIGHT-004..008 all FIXED; FIGHT-009..013 reserved for weapon-proc PERS follow-up |
| Shared visibility helper | `mud/world/vision.py:pers` used by all 5 channel commands + `_broadcast_pos_change` helper in `mud/combat/engine.py` |
| GitNexus index | stale (last analyze at `de1893f`); re-run with `npx gitnexus analyze --skip-agents-md` before next session that needs it. |
| Local commits not pushed | 6 (`40c0879..895c6d8`) + this handoff — waiting on explicit user push approval. |

## Next Intended Task

Position-change broadcast surface fully cleaned up. Three reasonable
continuations:

1. **FIGHT-009..013 weapon-proc PERS sweep** (recommended). Same
   pattern, same helper (`_broadcast_pos_change` can be renamed
   `_broadcast_act_n` if generalized, or a thin sibling helper
   added). `mud/combat/engine.py` lines 1496 (poison), 1510
   (vampiric), 1531 (flaming), 1541 (frost), 1551 (shocking). Some
   also have wording divergences vs ROM `src/fight.c:614-675`.
2. **`dam_message`** — ROM `src/fight.c:2035-2233` is the per-hit
   damage broadcast surface (hundreds of damage-tier messages,
   each with `act()` lines needing PERS). Larger surface, but the
   highest-volume PERS leak in combat by far.
3. **PMOTE-001** — `do_pmote` greenfield port. Still on the
   `act_comm.c` shelf, ~50 lines of C with per-recipient
   second-person substitution.

Recommendation: **FIGHT-009..013** as the natural continuation —
same helper, same test class, hands-off pattern.

## Operational follow-ups

- `log/orphaned_helps.txt` still tracked and drifts on test runs. Consider `git rm --cached log/orphaned_helps.txt` + `.gitignore` entry in a small future hygiene commit.
- GitNexus 32 KB scope-extractor failures persist on the documented file list (see CLAUDE.md "Known GitNexus Indexing Gap").
