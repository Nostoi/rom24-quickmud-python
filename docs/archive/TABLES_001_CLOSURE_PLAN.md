# TABLES-001 Closure Plan — `AffectFlag` bit-position migration

**Gap**: ROM `merc.h:953-982` defines `AFF_*` bit positions A..dd (1<<0..1<<29). Python `mud/models/constants.py:548-580 AffectFlag` has different bit positions for bits 6..29. `convert_flags_from_letters` decodes letters with the ROM-correct mapping, so any letter-form input is silently misaligned with the Python enum.

**Reproducer (durable)**: `tests/integration/test_tables_parity.py::test_affect_flag_letters_match_rom_merc_h` (currently `xfail strict`).

## Divergence inventory

20 of 29 `AFF_*` bits diverge. Mapping (Python current bit → ROM-canonical bit):

| Member | Python bit | ROM bit (merc.h) | Δ |
|---|---|---|---|
| BLIND | 0 | 0 | ✓ |
| INVISIBLE | 1 | 1 | ✓ |
| DETECT_EVIL | 2 | 2 | ✓ |
| DETECT_INVIS | 3 | 3 | ✓ |
| DETECT_MAGIC | 4 | 4 | ✓ |
| DETECT_HIDDEN | 5 | 5 | ✓ |
| **SANCTUARY** | 6 | 7 | +1 |
| **FAERIE_FIRE** | 7 | 8 | +1 |
| **INFRARED** | 8 | 9 | +1 |
| **CURSE** | 9 | 10 | +1 |
| **DETECT_GOOD** | 10 | 6 | -4 |
| **POISON** | 11 | 12 | +1 |
| **PROTECT_EVIL** | 12 | 13 | +1 |
| **PROTECT_GOOD** | 13 | 14 | +1 |
| **SNEAK** | 14 | 15 | +1 |
| **HIDE** | 15 | 16 | +1 |
| **SLEEP** | 16 | 17 | +1 |
| **CHARM** | 17 | 18 | +1 |
| **FLYING** | 18 | 19 | +1 |
| **PASS_DOOR** | 19 | 20 | +1 |
| **WEAKEN** | 20 | 24 | +4 |
| **BERSERK** | 21 | 26 | +5 |
| **CALM** | 22 | 22 | ✓ (coincidence) |
| **HASTE** | 23 | 21 | -2 |
| **SLOW** | 24 | 29 | +5 |
| **PLAGUE** | 25 | 23 | -2 |
| **DARK_VISION** | 26 | 25 | -1 |
| **SWIM** | 27 | 27 | ✓ (coincidence) |
| **REGENERATION** | 28 | 28 | ✓ (coincidence) |

Bit 11 (`AFF_UNUSED_FLAG = L`) is reserved/unused in ROM — Python currently uses it as `POISON`. After migration POISON moves to bit 12 and bit 11 becomes unused.

## Persistence blast radius

### Touched (need migration)

1. **Character pfiles** — `mud/persistence.py:271, 913, 996`. PCs persist `affected_by: int`. Existing pfiles encode bits in the old Python positions. After renumber, `1<<6` would mean DETECT_GOOD (ROM) instead of SANCTUARY (old Python). **Migration required.**
2. **Persisted active Affect bitvectors** — `mud/persistence.py:205, 237, 395, 454, 506, 705`. `Affect.bitvector: int` is stored on every saved spell affect. Same migration needed.
3. **Pet snapshots** — `mud/persistence.py:556, 642`. PC pets carry their own `affected_by`. Same migration.

### Untouched (no migration)

1. **Mob protos / area files** — `mud/loaders/mob_loader.py` stores `affected_by` as ROM-canonical letter strings ("ABG"). Letters are ROM-canonical and decoded only at use time via `convert_flags_from_letters`, which already produces ROM-correct bits. After renumber, those bits *finally* match the Python enum members of the same name. **Naturally fixes itself.**
2. **Race table** — `mud/models/races.py` uses symbolic `AffectFlag.X` references. Renumber → race ints update automatically. **No data migration.**
3. **In-memory uses** — All ~50 callsites use `AffectFlag.SANCTUARY`/`AffectFlag.HASTE` etc. symbolically (verified in earlier session). Bit values flow with the enum. **No code change.**

### Verified-clean tests

Pre-existing grep showed no test asserts a specific integer value for `AffectFlag` (everything is symbolic). The new programmatic test in `test_tables_parity.py` is the canonical regression guard.

## Migration approach (recommended: A)

### Option A — Schema version + on-load translation (recommended)

1. Add `pfile_version: int` field on persisted character schema. Existing pfiles get `pfile_version=0` on first load.
2. Add `_translate_legacy_affect_bits(value: int) -> int` using a precomputed mapping table from old Python bits → new ROM bits.
3. In the load path: if `pfile_version < 1`, translate `affected_by` and every persisted `Affect.bitvector`, then bump version → 1.
4. Going forward, save with `pfile_version=1`. Translation only runs once per pfile on first post-migration load.

**Pros**: reversible (old branches still load; new code translates lazily); no offline data migration step; no downtime; survives developers running mixed branches.

**Cons**: persistent code path lives forever (small).

### Option B — One-shot offline migration script

1. Write `mud/scripts/migrate_affect_bits.py` that walks every pfile JSON, translates `affected_by` and Affect.bitvector ints, writes back.
2. Bump `pyproject.toml` minor version (data-format change).

**Pros**: no on-load logic; clean code surface afterwards.

**Cons**: requires a synchronization moment; old branches that loaded the new files would mis-interpret them.

### Option C — Accept divergence (rejected)

Loading an existing pfile with the new enum would shift each PC's affects. E.g. a PC with sanctuary today (saved as `1<<6`) would suddenly have detect_good after upgrade. Not acceptable for a parity port.

## Implementation steps

1. **Branch off master.** Verify clean tree.
2. **Inventory pass** (no code yet):
   - Confirm no other persisted ints carry `AffectFlag` bits.
   - Run `grep -rn "1 << \|0x[0-9a-f]\+" mud/ tests/` against `AffectFlag` callsites — verify none hardcode bits.
3. **Add translation table** (`mud/persistence/affect_migration.py` or extend `mud/persistence.py`):
   ```python
   _AFFECT_BIT_REMAP = {
       1 << 6: 1 << 7,   # old SANCTUARY → new (= ROM SANCTUARY at bit 7)
       1 << 7: 1 << 8,   # old FAERIE_FIRE → new (bit 8)
       1 << 8: 1 << 9,   # old INFRARED → new (bit 9)
       1 << 9: 1 << 10,  # old CURSE → new (bit 10)
       1 << 10: 1 << 6,  # old DETECT_GOOD → new (bit 6)
       1 << 11: 1 << 12, # old POISON → new (bit 12)
       # ... continue per the divergence table above
   }

   def translate_legacy_affect_bits(value: int) -> int:
       """Translate pre-TABLES-001 AffectFlag int to ROM-canonical bits."""
       result = 0
       for bit_index in range(30):
           old_bit = 1 << bit_index
           if value & old_bit:
               result |= _AFFECT_BIT_REMAP.get(old_bit, old_bit)
       return result
   ```
4. **Add schema version field**: extend the persistence dataclass / SQLAlchemy model with `pfile_version: int = 0`. Default `0` for legacy rows.
5. **Wire migration into load path** in `mud/persistence.py`:
   - On character load: if `pfile_version < 1`, translate `affected_by` and every nested `Affect.bitvector`, set `pfile_version = 1`.
   - On character save: always write `pfile_version = 1`.
6. **Renumber `AffectFlag`** in `mud/models/constants.py:548-580` to match `merc.h:953-982` exactly. Update `# (X)` comments to show ROM letter.
7. **Test pass**:
   - Flip `tests/integration/test_tables_parity.py::test_affect_flag_letters_match_rom_merc_h` from `xfail(strict)` → expected pass. (Just remove the decorator.)
   - Add new migration-specific test: synthesize a legacy pfile dict with old `affected_by`, run loader, assert each PC bit translates correctly.
   - Run full integration suite. Watch for: combat tests asserting `has_affect(SANCTUARY)`, regen ticks, charm/calm/sleep, dark_vision visibility — all should pass because they're symbolic.
8. **Tracker / docs**:
   - Flip TABLES-001 row from 🔄 OPEN → ✅ FIXED in `TABLES_C_AUDIT.md`.
   - Flip `tables.c` row in `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` from ⚠️ Partial 75% → ✅ AUDITED 100% (TABLES-001/002/003 all closed).
   - Bump `tables.c` audited count: 27 → 28 / 43.
   - CHANGELOG entry under `Fixed`: cite TABLES-001 closure + migration.
9. **Version bump**: `pyproject.toml` patch (2.6.33 → 2.6.34) — internal data-format change, no API surface.
10. **Session handoff**: write `SESSION_SUMMARY_<date>_TABLES_001_AFFECT_FLAG_MIGRATION.md` and refresh `SESSION_STATUS.md`.

## Test plan

| Test | Purpose |
|---|---|
| `test_affect_flag_letters_match_rom_merc_h` (existing, xfail removed) | Asserts every letter-decoded bit equals the Python member of the same name. The canary. |
| `test_legacy_pfile_affect_bits_translated` (new) | Constructs a legacy persistence dict with old Python bits set on `affected_by`, runs the loader, asserts the in-memory char has the right `AffectFlag.X` set via `has_affect`. |
| `test_legacy_active_affect_bitvector_translated` (new) | Same, but for a persisted `Affect.bitvector`. |
| `test_pfile_save_writes_pfile_version_1` (new) | Asserts saves go out tagged at version 1. |
| `test_pfile_round_trip_post_migration_is_idempotent` (new) | Save → load → save → assert byte-identical (version 1 doesn't re-translate). |
| Existing `test_handler_affects_rom_parity.py`, combat suites, game_loop suites | Must stay green — symbolic uses follow the renumbered enum. |

## Risk assessment

| Risk | Severity | Mitigation |
|---|---|---|
| `mud/persistence.py` is in the 32 KB-per-file list (`gitnexus_impact` unreliable) | Medium | Manual `grep` for `affected_by` callsites; rely on integration tests not the graph. |
| Existing pfiles are silently mis-translated due to incomplete remap table | High | Test every bit explicitly: `for bit_index in range(30): legacy = 1<<bit_index; loaded = ...; assert ...`. |
| A code path stores `affected_by` somewhere not yet enumerated | Medium | Inventory pass step 2 above; spot-check `mud/db/`, `mud/account/`, `mud/scripts/`. |
| Race file uses ints rather than symbolic `AffectFlag.X` | Low | Verified — `mud/models/races.py` uses symbolic refs only. |
| Pre-existing `test_building.py` failures mask new regressions | Low | Run target suites individually post-renumber, not full suite. |

## Estimated effort

- Inventory pass: 30 min.
- Implementation: 90 min.
- Test writing + verification: 60 min.
- Tracker/doc updates + commit hygiene: 30 min.

**One focused session, ~3.5 hours.**

## Out of scope

- Renumbering any other IntFlag (TABLES-003 confirmed only `AffectFlag` diverges).
- Migrating object/mob proto on-disk data (already letter-form, naturally fixed).
- Refactoring `convert_flags_from_letters` (already ROM-correct).
- Compatibility with pre-`pfile_version` save formats older than ~6 months — there's only one schema in play; migration runs once.
