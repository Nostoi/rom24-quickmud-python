# Session Status — 2026-05-24 — `do_pmote` PERS + NPC-viewer parity (PMOTE-002/003)

## Current State

- **Last completed**: **PMOTE-002/003** — `mud/commands/imm_emote.py` now matches ROM on the remaining documented pmote follow-ups. `do_pmote` routes the actor prefix through `PERS(ch, vch)` per recipient, so invisible actors render as `"someone"` to viewers without `DETECT_INVIS`; both `do_pmote` and `do_smote` now skip all `desc == NULL` observers, excluding NPCs exactly like ROM. Released locally as **2.8.70**.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-24_PMOTE_PERS.md](SESSION_SUMMARY_2026-05-24_PMOTE_PERS.md).
- **Earlier summaries this run**:
  - [SESSION_SUMMARY_2026-05-24_DAM_MESSAGE_PERS.md](SESSION_SUMMARY_2026-05-24_DAM_MESSAGE_PERS.md) (`DAMMSG-001/002/003`, 2.8.67)
  - [SESSION_SUMMARY_2026-05-23_FIGHT_C_WEAPON_PROC_PERS_SWEEP.md](SESSION_SUMMARY_2026-05-23_FIGHT_C_WEAPON_PROC_PERS_SWEEP.md) (`FIGHT-009..014`, 2.8.61-2.8.66)
  - [SESSION_SUMMARY_2026-05-23_FIGHT_C_PERS_SWEEP.md](SESSION_SUMMARY_2026-05-23_FIGHT_C_PERS_SWEEP.md) (`FIGHT-004..008`, 2.8.55-2.8.60)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.70 |
| Tests | `tests/integration/test_act_comm_gaps.py` passes (29/29) after PMOTE-002/003 |
| Cross-file invariants | INV-001..009 (all ✅ ENFORCED) |
| `act_comm.c::do_pmote` | ✅ PMOTE-001/002/003 all FIXED |
| `act_wiz.c::do_smote` | ✅ viewer-loop parity restored for `desc == NULL` skip |
| Shared visibility helper | `mud/world/vision.py::pers` now covers pmote viewer prefixes too |
| GitNexus index | usable for this slice; `detect_changes` stayed low-risk/local |
| Local commits not pushed | 3 on `master` (`ad8fdf5` PMOTE-001, `cdf53dd` PMOTE-002, `822dcb0` PMOTE-003) — waiting on explicit user push approval |

## Next Intended Task

`do_pmote`'s documented parity surface is now closed. Reasonable continuations:

1. Pick the next `⚠️ Partial` / `❌ Not Audited` row from `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`.
2. Continue `act_comm.c` gap closure work if new open rows remain after the PMOTE sweep.
3. If the user wants these three local parity commits published, ask before pushing.

## Operational follow-ups

- `ruff check .` still fails on many pre-existing unrelated files outside this slice (notably `.claude/skills/*`, `diagnostic_test.py`, and several legacy test modules). No attempt was made to fix unrelated repo-wide lint debt.
- `log/orphaned_helps.txt` remains the tracked artifact previously called out in earlier summaries; hygiene follow-up is still optional and separate from parity work.
