# Session Status — 2026-06-09 — Diff-harness C-oracle for TRIG_KILL and TRIG_DEATH (2.13.58)

## Current State

- **Active mode**: divergence Class 11 / dynamic differential widening
  (per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **`__instant_kill` meta-command** added to C shim (`diffmain.c`) and Python replay
    (`pyreplay.py`). Calls `damage(ch, mob, mob->hit+1, TYPE_HIT, DAM_BASH, TRUE)` / `apply_damage`
    to exercise the full ROM death path deterministically.
  - **TRIG_KILL C-oracle ground truth.** `mob_kill_trigger.json` confirms `mp_kill_trigger`
    fires on the first hit (even a miss) when `victim->fighting == NULL`. Python and C agree.
  - **TRIG_DEATH C-oracle ground truth.** `mob_death_trigger.json` confirms `mp_death_trigger`
    fires after `group_gain`/XP and before `raw_kill`, with mob position temporarily STANDING.
    Python and C agree after 4 bug fixes (see summary).
  - **Bug fixes**: TRIG_DEATH ordering, `death_cry` default message, `xp_compute` logon=0 elapsed,
    snapshot dead-char filter. `mob_has_trigger()` helper added to `mobprog.py`.
  - Version 2.13.58; 5,493 tests pass.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-09_DIFF_HARNESS_KILL_DEATH_CORACLES.md](SESSION_SUMMARY_2026-06-09_DIFF_HARNESS_KILL_DEATH_CORACLES.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.58 |
| Tests | 5,493 passed, 5 skipped (last full run) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 25 enforced |
| Diff-harness scenarios | 20 scenarios (added KILL + DEATH this session) |
| Class 11 dynamic widening | EXIT + EXALL + GREET + GRALL + SPEECH + ACT + BRIBE + GIVE + SURR + FIGHT + HPCNT + KILL + DEATH all have C-oracle ground truth |

## Next Intended Task

Class 11 remaining work (in priority order):

1. **TRIG_RANDOM and TRIG_DELAY C-oracle scenarios** — RANDOM fires on `mobile_update`'s 1-in-8
   tick; need a seed that aligns the roll. DELAY fires when `mob->mprog_delay` reaches 0 during
   `mobile_update`; should be tractable with `__tick` and a mob preset to `mprog_delay=1`.
2. **Next divergence class** — consult `docs/parity/DIVERGENCE_CLASS_ROSTER.md` for the next
   unverified surface outside Class 11. Candidates: async message delivery ordering, affect-tick
   edge contracts, position-transition invariants.
3. **Latent parity gap: wizard shop status** — Python's `_has_shop` returns False for mob 3000
   (wizard) because the midgaard JSON area file has no `shops` section. C's midgaard.are defines
   wizard as a shopkeeper. Should be reviewed against shop scenario coverage.
