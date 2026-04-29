# Session Summary — 2026-04-29 — TABLES-001 `AffectFlag` bit-position migration

## What landed

Closed **TABLES-001** (CRITICAL) — Python `AffectFlag` bit positions diverged from ROM
`src/merc.h:953-982` for 20 of 29 bits, silently mis-aligning `convert_flags_from_letters`
output (which was already ROM-correct) with the enum members of the same name.

`tables.c` flips from ⚠️ Partial 75% → ✅ AUDITED 100% (TABLES-001 / 002 / 003 all closed).

## Changes

| File | Change |
|---|---|
| `mud/models/constants.py:548-583` | `AffectFlag` renumbered to match ROM merc.h letters A..dd → bits 0..29. `DETECT_GOOD` moves 1<<10→1<<6, `SANCTUARY` 1<<6→1<<7, `HASTE` 1<<23→1<<21, `WEAKEN` 1<<20→1<<24, `BERSERK` 1<<21→1<<26, `SLOW` 1<<24→1<<29, `PLAGUE` 1<<25→1<<23, `DARK_VISION` 1<<26→1<<25, etc. Letter `# (X)` comments added. Bit 11 reserved (`AFF_UNUSED_FLAG = L`). |
| `mud/persistence.py` | Added `_AFFECT_BIT_TRANSLATION` (legacy bit → ROM bit), `translate_legacy_affect_bits(value)`, `PFILE_SCHEMA_VERSION = 1`. Added `pfile_version: int = 0` to `PlayerSave`. Save path always writes `pfile_version=1`. Load path: `_upgrade_legacy_save` detects `pfile_version < 1` and translates `affected_by` on character + pet, every `Affect.bitvector` in inventory/equipment/contains/pet-affects, then bumps version. |
| `tests/integration/test_tables_parity.py` | Removed `xfail(strict=True)` on `test_affect_flag_letters_match_rom_merc_h`. Added `AFF` to `_PREFIX_TO_ENUM` and removed the `AFF_*` skip in `test_merc_h_letter_macros_match_python_intflag_values` so it now covers all merc.h `AFF_*` macros too. |
| `tests/integration/test_tables_001_affect_migration.py` | New file. 4 tests: legacy `affected_by` translation, legacy nested item-affect `bitvector` translation, save-writes-`pfile_version=1`, post-migration round-trip idempotence. |
| `tests/test_affects.py:test_affect_flag_values` | Updated hard-coded bit asserts to ROM-canonical positions (BLIND..INFRARED bits 0..9). |
| `tests/test_movement_followers.py:test_charmed_follower_stays_with_master` | Mob proto `affected_by` letter changed `R` → `S`: ROM `R = AFF_SLEEP`, `S = AFF_CHARM`. The old test was passing only because the buggy Python enum mis-labeled bit 17 as `CHARM`. |
| `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` | `tables.c` row flipped ⚠️ Partial 75% → ✅ AUDITED 100%. |
| `docs/parity/TABLES_C_AUDIT.md` | TABLES-001 row → ✅ FIXED with closure note. Phase 4 / Phase 5 sections updated. |
| `CHANGELOG.md` | New `Fixed: TABLES-001` entry under `[Unreleased]`. |
| `pyproject.toml` | Version 2.6.33 → 2.6.34 (patch — internal data-format change, no API surface). |

## Tests

- New: 4 migration tests in `tests/integration/test_tables_001_affect_migration.py` — all pass.
- Flipped: `test_affect_flag_letters_match_rom_merc_h` from `xfail(strict)` → green.
- Extended: `test_merc_h_letter_macros_match_python_intflag_values` now also covers ~30 `AFF_*` macros.
- Targeted suites green: `tests/integration/test_tables_parity.py`, `tests/integration/test_tables_001_affect_migration.py`, `tests/test_affects.py`, `tests/test_movement_followers.py`, `tests/integration/` (1352 passed, 10 skipped).
- Full pytest delta vs master baseline: 2 newly-green xfail strict cases plus 4 new tests; the 2 test fixes above (`test_affect_flag_values`, `test_charmed_follower_stays_with_master`) were tests asserting the buggy old behavior. ~50 pre-existing failures (test_olc_save / test_building / test_commands / test_logging_admin) are unrelated and confirmed against the master baseline.

## Notes / discoveries

- `tests/test_movement_followers.py::test_charmed_follower_stays_with_master` had a latent bug-dependency: it set `affected_by="R"` on a mob proto expecting CHARM. ROM letter R is `AFF_SLEEP`; the test was only passing because the old Python `AffectFlag` enum had `CHARM = 1 << 17` lined up with the (correct) ROM letter R bit. Fixed by switching to letter `S` (ROM `AFF_CHARM`). This is the kind of silent test-bug TABLES-001 was hiding.
- The migration is one-way: legacy pfiles upgrade on first load and re-save with `pfile_version=1`. After the next save no further translation runs (idempotent — verified by `test_pfile_round_trip_post_migration_is_idempotent`). Old branches loading new files would mis-interpret them, so this is a coordination point if downgrades become necessary; for now ROM-canonical wins.
- Mob protos / area files (`affected_by` letter strings like `"ABG"`) need no migration — the loader decodes via `convert_flags_from_letters`, which has always produced ROM-canonical bits. The renumber means those bits now finally align with the Python enum members of the same name.
- Race table (`mud/models/races.py`) and ~50 in-memory call sites use symbolic `AffectFlag.X` references and need no code change — the bits flow with the enum.

## Next session

`tables.c` is done. Candidates: `board.c` (P2 partial), OLC cluster (P2), or NANNY-008/009/010. See `SESSION_STATUS.md`.
