# Session Status — 2026-05-15 — full suite re-certified, next target set to combat→XP verification

## Current State

- **Full suite is green.**
- Verified with:
  - `./venv/bin/python -m pytest -q --maxfail=1`
  - `4535 passed, 11 skipped in 340.16s (0:05:40)`
- **This session re-ran the full suite from a written execution plan**:
  - plan saved at `docs/superpowers/plans/2026-05-15-full-suite-rerun-and-next-rom-verification.md`
- **This session stabilized two flaky tests surfaced by the rerun**:
  - `tests/test_account_auth.py::test_new_player_triggers_wiznet_newbie_alert` now isolates `global_registry.descriptor_list` so wiznet delivery does not inherit prior test state
  - `tests/integration/test_character_advancement.py::test_kill_mob_grants_xp_integration` now uses fixed ROM RNG seed `1` instead of wall-clock seeding
- **Pointer to latest summary**:
  - `docs/sessions/SESSION_SUMMARY_2026-05-15_FULL_SUITE_RECERT_AND_XP_ALERT_FLAKE_STABILIZATION.md`

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.11 |
| Cross-file invariants enforced | **8/8 ✅ ENFORCED** |
| Audit-bound ROM C files | 40/40 audited (100%) |
| N/A ROM C files | 3/3 (`recycle.c`, `mem.c`, `imc.c`) |
| Full suite | ✅ green |
| Warnings | ✅ zero |
| Current focus | fresh ROM verification on combat→XP flow |

## Next Intended Task

1. Run a ROM-source-first verification pass on the combat → XP advancement flow.
2. Authoritative ROM sources:
   - `src/fight.c` — `group_gain`, `xp_compute`, `raw_kill`
   - `src/update.c` — `gain_exp`
3. Treat the recent XP test failure as a signal about this surface, but not as evidence of a production bug; the rerun proved it was test nondeterminism.

## Open Follow-ups

- **Combat → XP advancement verification** — proactive parity pass chosen from the clean full-suite rerun
