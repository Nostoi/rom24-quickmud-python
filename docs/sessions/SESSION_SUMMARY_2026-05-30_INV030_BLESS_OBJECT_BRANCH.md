# Session Summary — 2026-05-30 — INV-030 Bless Object Branch + Probes

## Scope

Continued from `SESSION_SUMMARY_2026-05-30_TEST_FLAKE_FIX_AND_INV_PROBE.md`.

Cross-file invariants active session:
1. **INV-030 BLESS-OBJECT-BRANCH** — implemented the missing TARGET_OBJ branch
   for `spell_bless` (ROM src/magic.c:788-834).
2. Probed NPC shop PCHAR flag integrity — no gap (Python matches ROM).
3. Checked `Character.pet` type annotation hygiene — deferred (no behavioral
   impact).

## Outcome

### INV-030 BLESS-OBJECT-BRANCH — ✅ FIXED (2.11.55)

The `bless()` handler in `mud/skills/handlers.py` only had the character
branch (ROM src/magic.c:836-865). The TARGET_OBJ branch (ROM :788-834) was
documented as "not ported here" and "currently unreachable." With CAST-006
(2.11.52) having already fixed `do_cast` to route `defensive_character_or_object`
object targets through `get_obj_carry`, the Object branch was reachable via
`cast bless <object>` but would crash (Object has no `.position` attribute).

Implementation mirrors ROM src/magic.c:788-834:
1. **Already-blessed check**: `IS_OBJ_STAT(obj, ITEM_BLESS)` → rejection
2. **Evil-dispel branch**: `saves_dispel(level, paf->level || obj->level, 0)`;
   success: `affect_remove_obj` removes curse affect, `REMOVE_BIT(ITEM_EVIL)`,
   "$p glows a pale blue."; failure: "The evil of $p is too powerful..."
3. **Clean object**: `affect_to_obj` with `TO_OBJECT / APPLY_SAVES / -1 / ITEM_BLESS`,
   "$p glows with a holy aura."
4. **Worn-object side effect**: `obj->wear_loc != WEAR_NONE` →
   `ch->saving_throw -= 1`

Signature changed from `(caster: Character, target: Character | None)` to
`(caster: Character, target: Character | Object | None)`.

All five `defensive_character_or_object` / `offensive_character_or_object`
spells now handle Object targets:
- `bless` ✅ (this session)
- `curse` ✅ (pre-existing)
- `poison` ✅ (pre-existing)
- `remove_curse` ✅ (pre-existing)
- `invisibility` ✅ (pre-existing)

### Probe: NPC Shop PCHAR flag integrity — no gap filed

Reviewed the pet shop purchase path (`do_buy` → `_handle_pet_shop_purchase`),
pet extraction on owner death (`_nuke_pets`), and the connection-disconnect
cleanup path. All match ROM faithfully. The `ActFlag.PET` flag is set on
purchase, charm is applied, and `_nuke_pets` dismisses pets on owner
extraction. No cross-file contract violation found.

### Probe: Character.pet type annotation — deferred

`pet: Character | None` should be `MobInstance | None` for accuracy, but this
is a type hygiene issue only (Python doesn't enforce types at runtime). Not a
parity bug; noted for future type pass.

### Carry-open: backstab test

`test_backstab_uses_position_and_weapon` passes cleanly under both serial and
xdist execution. The previously-reported flake appears to have been resolved
by a prior change.

## Files Modified

- `mud/skills/handlers.py` — bless() rewritten with Object branch
  (already-blessed, evil-dispel, clean-object affect, worn-object bonus)
- `tests/integration/test_inv030_bless_object_branch.py` — new (7 tests)
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-030 row added
- `docs/parity/MAGIC_C_AUDIT.md` — bless Object branch "deferred" note updated
  to "now implemented (INV-030)"
- `CHANGELOG.md` — 2.11.55 entry
- `pyproject.toml` — 2.11.54 → 2.11.55

## Verification

- `pytest tests/integration/test_inv030_bless_object_branch.py -n0 -v` — 7 passed
- `pytest -n auto -q` — 5087 passed, 4 skipped
- `ruff check mud/skills/handlers.py tests/integration/test_inv030_bless_object_branch.py` — all checks passed

## Outstanding

- Continue cross-file invariant probe/close cycle.
- `Character.pet` type annotation hygiene (`Character | None` → `MobInstance |
  None`) — future type pass, not a parity bug.
- Per-spell handler `curse` type annotation hygiene (missing `Object` in
  signature) — future type pass.
- Remaining candidate areas for INV probing: affect-tick interaction across
  modules (e.g., plague spread during char_update and its interaction with
  SINGLE-DELIVERY), group/follower chain contracts beyond INV-020.