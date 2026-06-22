# Session Summary — 2026-06-22 — Death auto-action differential harness

## Landed

- Closed **FIGHT-079** in a separate commit (`da678a2f`):
  - Re-read ROM `src/fight.c:1483-1495` and corrected the stale filed note.
  - Python PC corpse money now matches ROM:
    - non-clan PC: owned corpse, no coin transfer, PC keeps all coins.
    - clan PC: unowned corpse, half gold/silver object on `> 1`, PC keeps the
      remainder.
  - Added/updated integration coverage in `tests/integration/test_money_objects.py`
    and `tests/integration/test_death_and_corpses.py`.

- Added death auto-action differential harness coverage:
  - `tools/diff_harness/scenarios/death_auto_gold.json`
  - `tools/diff_harness/scenarios/death_auto_loot.json`
  - C goldens:
    - `tests/data/golden/diff/death_auto_gold.golden.json`
    - `tests/data/golden/diff/death_auto_loot.golden.json`
  - New harness meta on both sides:
    - `__plr_autogold=0|1`
    - `__plr_autoloot=0|1`

- The new scenarios surfaced **FINDING-040 / FIGHT-080**, fixed in the same pass:
  - ROM `src/fight.c:945-967` calls `do_get(ch, "all corpse")` for autoloot and
    `do_get(ch, "all.gcash corpse")` for autogold when autoloot is off.
  - Python previously manually moved loot/coins and pushed
    `"You quickly gather the loot from the corpse."`.
  - `mud/combat/engine.py` now routes both death auto branches through
    `mud.commands.inventory.do_get` and delivers the returned get lines through
    `_push_message`.

## Docs / Trackers

- Bumped version to **2.14.208**.
- Updated `CHANGELOG.md`.
- Updated `docs/parity/FIGHT_C_AUDIT.md` with FIGHT-079 and FIGHT-080 fixed rows.
- Added `tools/diff_harness/FINDINGS.md` FINDING-040.
- Updated `tools/diff_harness/README.md` meta-command table.
- Updated `tests/test_differential_smoke.py` scenario-count comment to 51.

## Verification

- `PYTHONPATH=. pytest -q -n0 tests/integration/test_death_and_corpses.py tests/integration/test_money_objects.py tests/integration/test_fight078_npc_corpse_money_gate.py` — 50 passed before the FIGHT-079 commit.
- `PYTHONPATH=. pytest -q -n0 tests/test_differential_smoke.py tests/test_diff_harness_unit.py tests/test_combat_death.py tests/integration/test_death_and_corpses.py tests/integration/test_money_objects.py tests/integration/test_fight078_npc_corpse_money_gate.py` — 154 passed.
- `ruff check .` — clean.
- `git diff --check` — clean.

## Outstanding

- Next death-lifecycle probes should target `PLR_AUTOSAC` and `PLR_AUTOSPLIT`.
- Driver-PC corpse death is still covered by integration tests only; the diff
  harness cannot currently kill and inspect the driver PC's own corpse.
