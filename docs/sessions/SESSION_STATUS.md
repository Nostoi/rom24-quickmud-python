# Session Status — 2026-05-23 — `fight.c` weapon-proc PERS sweep closed (FIGHT-009..013)

## Current State

- **Last completed**: **FIGHT-009..013** (weapon-proc TO_ROOM broadcasts) released as 2.8.61 → 2.8.65 across five TDD commits. Both PERS surfaces in `mud/combat/engine.py` — position-change broadcasts (FIGHT-004..008) and weapon-proc broadcasts (FIGHT-009..013) — are now ROM-faithful. The `_broadcast_pos_change` helper powers 9 broadcast sites and accepts arbitrary `**extra` template kwargs (used for `{weapon}` substitution on ROM `$p`).
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-23_FIGHT_C_WEAPON_PROC_PERS_SWEEP.md](SESSION_SUMMARY_2026-05-23_FIGHT_C_WEAPON_PROC_PERS_SWEEP.md)
- **Earlier summaries this run**:
  - [SESSION_SUMMARY_2026-05-23_FIGHT_C_PERS_SWEEP.md](SESSION_SUMMARY_2026-05-23_FIGHT_C_PERS_SWEEP.md) (2.8.55-2.8.60)
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
| Version | 2.8.65 |
| Tests | **4637 passed, 4 skipped** (full suite, ~6m 20s) |
| Cross-file invariants | INV-001..009 (all ✅ ENFORCED) |
| `nanny.c` audit | 100% gap rows ✅ |
| `act_info.c::do_prompt` | ✅ PROMPT-CMD-001..005 all FIXED |
| `act_comm.c::do_say` | ✅ 100% RE-AUDITED (SAY-001..004) |
| `act_comm.c::do_emote` | EMOTE-001/002 ✅; PMOTE-001 ❌ MISSING (stable-IDed) |
| `act_comm.c::do_tell` | ✅ 100% RE-AUDITED (TELL-001..005 FIXED, TELL-006 ANALYZED-INERT) |
| `act_comm.c::do_shout` | ✅ 100% RE-AUDITED (SHOUT-001..003) |
| `act_comm.c::do_yell` | ✅ 100% RE-AUDITED (YELL-001) |
| `fight.c::_position_change_message` | ✅ FIGHT-004..008 all FIXED |
| `fight.c` weapon procs | ✅ FIGHT-009..013 all FIXED |
| Shared visibility helper | `mud/world/vision.py:pers` used by all 5 channel commands + `_broadcast_pos_change` helper in `mud/combat/engine.py` (9 broadcast sites) |
| GitNexus index | stale (last analyze at `de1893f`); re-run with `npx gitnexus analyze --skip-agents-md` before next session that needs it. |
| Local commits not pushed | 5 (`59655b1..d93a88a`) + this handoff — waiting on explicit user push approval. |

## Next Intended Task

Both major combat-message PERS surfaces in `mud/combat/engine.py`
are cleaned up. Three reasonable continuations:

1. **`dam_message`** (`mud/combat/messages.py` / `mud/combat/engine.py:252`)
   — ROM `src/fight.c:2035-2233`. Per-hit damage-tier broadcast
   surface (hundreds of `act()` lines). Highest-volume PERS leak
   remaining in combat. **Likely a multi-session arc.** Best
   started fresh.
2. **FIGHT-014 — `do_sacrifice` PERS** (`mud/combat/engine.py:956`,
   single `_broadcast_room` call with `expand_placeholders`-rendered
   `"$n sacrifices $N to Mota."`). 10-minute warm-up; PERS gap on
   attacker. Could close before opening dam_message.
3. **PMOTE-001** — `do_pmote` greenfield port (~50 lines of C on
   the `act_comm.c` shelf, per-recipient second-person substitution
   with apostrophe/possessive handling).

Recommendation: **FIGHT-014** as a warm-up, then open `dam_message`
as a fresh session.

## Operational follow-ups

- `log/orphaned_helps.txt` still tracked and drifts on test runs. Consider `git rm --cached log/orphaned_helps.txt` + `.gitignore` entry in a small future hygiene commit.
- GitNexus 32 KB scope-extractor failures persist on the documented file list (see CLAUDE.md "Known GitNexus Indexing Gap").
