# Session Summary — 2026-05-17 — GL-010 / GL-017 affect wear-off suppression closed

## What landed

Closed the last two `update.c` audit gaps tied to affect wear-off handling:

- **GL-010** — `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/affects/engine.py`
  - `tick_spell_effects()` now uses the ordered ROM-style `character.affected` list when present.
  - Expiring `AffectData` entries are removed one-by-one.
  - The merged legacy `character.spell_effects` entry is now preserved when a later same-type affect remains active, matching ROM `char_update()` semantics.
  - Wear-off messaging now follows ROM ordering instead of deleting the whole merged spell effect too early.

- **GL-017** — `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/game_loop.py`
  - `_tick_object_affects()` now suppresses duplicate wear-off broadcasts for consecutive zero-duration same-type affects.
  - This matches ROM `obj_update()` linked-list behavior: only the final affect in a same-type zero-duration run emits `msg_obj`.

## ROM source traced

- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/src/update.c:762`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/src/update.c:939`

## Root-cause notes

- The old audit note for `GL-010` / `GL-017` was partially wrong: this did **not** require an architectural migration away from the current data model.
- Python already had ordered affect chains available:
  - `Character.affected`
  - `ObjectData.affected`
- The real missing behavior was simply that the tickers were not consulting the ordered affect chains when deciding whether to emit a wear-off message and whether the owning merged spell effect should remain active.
- One stale unit expectation also surfaced and was corrected: ROM decrements duration `1 -> 0` on one tick, then removes/emits on the **next** tick.

## Tests added / updated

### New targeted tests
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_affects.py`
  - `test_tick_spell_effects_keeps_spell_effect_when_same_spell_affect_remains_active`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_obj_update_rom_parity.py`
  - `test_wear_off_suppressed_for_consecutive_zero_duration_same_type_affects`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_update_c_parity.py`
  - `test_char_update_keeps_spell_effect_when_same_type_affect_remains`
  - `test_obj_update_suppresses_duplicate_same_type_wear_off_messages`

### Stale expectations corrected to ROM
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_affects.py`
  - `test_affect_to_char_applies_stat_modifiers`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_game_loop.py`
  - `test_char_update_applies_regen_conditions_and_wear_off_messages`

## Verification

### Focused red/green
- `./venv/bin/python -m pytest -q /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_affects.py -k keeps_spell_effect_when_same_spell_affect_remains_active`
- `./venv/bin/python -m pytest -q /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_obj_update_rom_parity.py -k consecutive_zero_duration_same_type_affects`

### Focused parity slice
- `./venv/bin/python -m pytest -q /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_affects.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_obj_update_rom_parity.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_game_loop.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_update_c_parity.py -k 'wear_off or affect or obj_update or plague or poison or armor or regen_tick'`
  - **Result:** `53 passed, 24 deselected`

### Broader shared-surface regression band
- `./venv/bin/python -m pytest -q /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_affects.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_game_loop.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_obj_update_rom_parity.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_handler_affects_rom_parity.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_saves_rom_parity.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_update_c_parity.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_spell_affects_persistence.py`
  - **Result:** `151 passed, 3 skipped`

### Lint
- `./venv/bin/python -m ruff check /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/affects/engine.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/game_loop.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_update_c_parity.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_affects.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_obj_update_rom_parity.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_game_loop.py`
  - **Result:** clean

### Full suite recertification
- `./venv/bin/python -m pytest -q --maxfail=1`
  - **Result:** `4546 passed, 11 skipped in 577.18s (0:09:37)`

## Docs updated

- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/UPDATE_C_AUDIT.md`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/INTEGRATION_TEST_COVERAGE_TRACKER.md`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_STATUS.md`

## Current repo state

- `update.c` audit is now fully closed, including the former deferred wear-off rows.
- Full suite is green.
- One unrelated local dirty file remains outside this slice:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/log/orphaned_helps.txt`

## Recommended next target

The next useful ROM-source-first slice is not another `update.c` follow-up. Best next move is to strengthen the remaining documented `fight.c` cross-file contracts that still lack enforcement tests:

- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`
  - `INV-005` same-room combat coherence
  - `INV-006` fighting-pointer coherence after death

That keeps momentum on real parity risk rather than stale tracker cleanup.
