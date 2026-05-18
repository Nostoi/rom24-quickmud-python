# Session Summary — 2026-05-18 — skill improvement parity and stale skip sweep recertified

## Landed

- Closed the ROM `check_improve()` parity gap in `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/skills/registry.py`.
  - Combat-driven skill learning now continues above class adept up to `100`, matching ROM `src/skills.c`.
- Replaced stale skipped integration placeholders with executable coverage in:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_skills_integration.py`
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_money_objects.py`
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_spell_affects_persistence.py`
- Fixed a real plague contagion parity bug in `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/game_loop.py`.
  - Spread victims now receive a full `AffectData` record through `affect_to_char(new_af)`, matching ROM `src/update.c:839-840`.
- Reconciled the integration coverage tracker so the skills and spell-affects slices reflect the real enforced state.
- Tightened `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_skill_combat_rom_parity.py` so kick damage assertions are isolated from follow-up `check_improve()` RNG.

## Verification

- Targeted skills/parity slice:
  - `./venv/bin/python -m pytest tests/integration/test_skills_integration.py tests/test_skills.py tests/integration/test_do_practice_command.py tests/integration/test_money_objects.py tests/integration/test_spell_affects_persistence.py tests/integration/test_update_c_parity.py`
  - `112 passed, 1 skipped`
- Kick parity regression slice:
  - `./venv/bin/python -m pytest -q tests/test_skill_combat_rom_parity.py -k 'kick_success_damage_formula_and_type or kick_failure_does_zero_damage_and_skips_number_range or kick_success_probability_is_strictly_greater'`
  - `3 passed`
- Lint:
  - `./venv/bin/ruff check mud/skills/registry.py mud/game_loop.py tests/integration/test_skills_integration.py tests/test_skills.py tests/integration/test_money_objects.py tests/integration/test_spell_affects_persistence.py tests/test_skill_combat_rom_parity.py`
  - clean
- Full suite:
  - `./venv/bin/python -m pytest -q --maxfail=1`
  - `4553 passed, 4 skipped in 437.55s`

## Files

- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/skills/registry.py`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/game_loop.py`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_skills_integration.py`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_skills.py`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_money_objects.py`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_spell_affects_persistence.py`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_skill_combat_rom_parity.py`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/INTEGRATION_TEST_COVERAGE_TRACKER.md`

## Next

- Return to the next ROM-source-first parity target outside the integration skip cleanup work.
- Prefer a tracker-backed row or a cross-file invariant that still lacks explicit enforcement.
