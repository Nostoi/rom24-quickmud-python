# Session Status — 2026-05-24 — `dam_message` PERS parity (DAMMSG-001/002/003)

## Current State

- **Last completed**: **DAMMSG-001/002/003** — the per-hit
  damage-tier broadcast surface in `mud/combat/` now PERS-renders
  per recipient, closing the highest-volume PERS leak remaining in
  combat. `dam_message` returns `{attacker}` / `{victim}` templates;
  the renamed `_broadcast_damage_messages` iterates `room.people`
  for TO_NOTVICT and calls a new `render_for` helper per observer.
  Released as 2.8.67.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-24_DAM_MESSAGE_PERS.md](SESSION_SUMMARY_2026-05-24_DAM_MESSAGE_PERS.md).
- **Earlier summaries this run**:
  - [SESSION_SUMMARY_2026-05-23_FIGHT_C_WEAPON_PROC_PERS_SWEEP.md](SESSION_SUMMARY_2026-05-23_FIGHT_C_WEAPON_PROC_PERS_SWEEP.md) (FIGHT-009..014, 2.8.61-2.8.66)
  - [SESSION_SUMMARY_2026-05-23_FIGHT_C_PERS_SWEEP.md](SESSION_SUMMARY_2026-05-23_FIGHT_C_PERS_SWEEP.md) (FIGHT-004..008, 2.8.55-2.8.60)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.67 |
| Tests | combat suites + new DAMMSG tests pass; full-suite verification pending background run |
| Cross-file invariants | INV-001..009 (all ✅ ENFORCED) |
| `fight.c::dam_message` | ✅ DAMMSG-001/002/003 all FIXED — per-recipient PERS rendering via `render_for` |
| `fight.c::_position_change_message` | ✅ FIGHT-004..008 all FIXED |
| `fight.c` weapon procs | ✅ FIGHT-009..013 all FIXED |
| `fight.c` autosac broadcast | ✅ FIGHT-014 FIXED (FIGHT-015 reserved for structural divergence) |
| Shared visibility helper | `mud/world/vision.py::pers` now used by all 5 channel commands, `_broadcast_pos_change` (10 sites), and the new `render_for` in `mud/combat/messages.py` |
| GitNexus index | stale (last analyze at `de1893f`); re-run with `npx gitnexus analyze --skip-agents-md` before next session that needs it |
| Local commits not pushed | 1 (this slice — DAMMSG sweep + STATUS refresh) — waiting on explicit user push approval |

## Next Intended Task

All PERS surfaces in `mud/combat/engine.py` are now ROM-faithful.
Reasonable continuations:

1. **PMOTE-001** — `do_pmote` greenfield port (~50 lines of C on
   the `act_comm.c` shelf, per-recipient second-person substitution
   with apostrophe/possessive handling).
2. **FIGHT-015** — refactor `_auto_sacrifice` to dispatch to
   `do_sacrifice` like ROM does at `src/fight.c:970` (structural
   parity, no behavior change).
3. Pick the next ⚠️ Partial row from
   `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`.

## Operational follow-ups

- `log/orphaned_helps.txt` still tracked and drifts on test runs.
  Consider `git rm --cached log/orphaned_helps.txt` + `.gitignore`
  entry in a small hygiene commit.
- GitNexus 32 KB scope-extractor failures persist on the documented
  file list (see CLAUDE.md "Known GitNexus Indexing Gap"); the new
  `render_for` helper lives in `mud/combat/messages.py` which is
  *not* on the failure list, but `mud/combat/engine.py` is — so
  impact-analysis queries against `_broadcast_damage_messages` will
  be unreliable until re-index.
