# Session Status — 2026-05-18 — skill improvement parity and stale skip sweep recertified

## Current State

- **The `check_improve()` parity gap is closed.**
- ROM combat learning above class adept is now enforced in `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/skills/registry.py`, with deterministic integration coverage in `tests/integration/test_skills_integration.py`.
- The stale money/spell integration skips were converted to executable tests.
- The plague-contagion path exposed a **real parity bug** in `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/game_loop.py`, now fixed by applying a full spread affect with `affect_to_char(new_af)` per ROM `src/update.c:839-840`.
- The kick ROM parity test was tightened so it asserts the real damage-roll call without conflating follow-up `check_improve()` RNG.
- **Pointer to latest summary**:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_SUMMARY_2026-05-18_SKILL_IMPROVEMENT_AND_STALE_SKIP_SWEEP_RECERTIFIED.md`

## Verification

- Focused parity slices:
  - `./venv/bin/python -m pytest tests/integration/test_skills_integration.py tests/test_skills.py tests/integration/test_do_practice_command.py tests/integration/test_money_objects.py tests/integration/test_spell_affects_persistence.py tests/integration/test_update_c_parity.py` → `112 passed, 1 skipped`
  - `./venv/bin/python -m pytest -q tests/test_skill_combat_rom_parity.py -k 'kick_success_damage_formula_and_type or kick_failure_does_zero_damage_and_skips_number_range or kick_success_probability_is_strictly_greater'` → `3 passed`
  - `./venv/bin/ruff check mud/skills/registry.py mud/game_loop.py tests/integration/test_skills_integration.py tests/test_skills.py tests/integration/test_money_objects.py tests/integration/test_spell_affects_persistence.py tests/test_skill_combat_rom_parity.py` → clean
- Full-suite recertification on record:
  - `./venv/bin/python -m pytest -q --maxfail=1`
  - `4553 passed, 4 skipped`

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.14 |
| Cross-file invariants enforced | **8/8 ✅ ENFORCED** |
| Audit-bound ROM C files | 40/40 audited (100%) |
| N/A ROM C files | 3/3 (`recycle.c`, `mem.c`, `imc.c`) |
| Full suite | ✅ green (`4553 passed, 4 skipped`) |
| Warnings | ✅ zero |
| Current focus | reconcile remaining stale audit headers now that the canonical tracker is green |

## Next Intended Task

1. Treat the current integration-skip sweep as closed unless a newly added skip starts firing in CI.
2. Reconcile stale audit headers that still advertise fixed `nanny.c` / persistence gaps as open, then choose the next real ROM-source-first target.
3. If a new failing/skip-only slice appears, confirm it reproduces under normal world boot before changing test expectations.
