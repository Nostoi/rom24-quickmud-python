# Session Summary — 2026-05-30 — do_cast Object-Targeting Parity

## Scope

Continued from `SESSION_SUMMARY_2026-05-30_GROUP_COMMANDS_LINT_CLEANUP.md`.

The per-file audit tracker remains exhausted, so the standing mode is
cross-file invariant probing. Picked up the carried-open `do_cast`
object-targeting legs item from `SESSION_STATUS.md`.

## Outcome

### CAST-004/005/006 — `do_cast` object-targeting parity ✅ FIXED (2.11.52)

Three ROM `TAR_*` target resolutions that were deferred since the CAST-002/003
vocabulary split are now wired:

- **CAST-004** (`TAR_OBJ_INV`): Object-only spells (`identify`, `enchant armor`,
  `enchant weapon`, `fireproof`, `create water`, `detect poison`, `recharge`)
  previously fell through to `target = char`. Now they require a named target,
  resolve via `get_obj_carry(char, target_name)`, and ROM-exact error messages:
  "What should the spell be cast upon?" (no arg), "You are not carrying that."
  (not found).

- **CAST-005** (`TAR_OBJ_CHAR_OFF` object fallback): Offensive dual-target spells
  (`curse`, `poison`) previously returned "They aren't here." immediately when
  no character matched the target name. Now falls back to `get_obj_here` per
  ROM `src/magic.c:502-506`; errors "You don't see that here." only when
  neither character nor object matches.

- **CAST-006** (`TAR_OBJ_CHAR_DEF` object fallback): Defensive dual-target spells
  (`bless`, `invisibility`, `remove curse`) previously returned "They aren't
  here." immediately when no character matched. Now falls back to
  `get_obj_carry` per ROM `src/magic.c:525-529`; errors "You don't see that
  here." only when neither character nor object matches.

The spell dispatch now passes `target_obj` (when resolved) to the spell
handler via `spell_func(char, spell_arg)`, so handlers that accept `Object`
targets (`identify`, `enchant_armor`, etc.) receive them correctly.

## Files Modified

- `mud/commands/combat.py` — `do_cast` object-targeting branches (TAR_OBJ_INV,
  TAR_OBJ_CHAR_OFF fallback, TAR_OBJ_CHAR_DEF fallback); spell_arg dispatch
- `tests/integration/test_do_cast_object_target.py` — 10 new tests
  (TestCastObjectTarget 3, TestCastOffensiveObjectFallback 3,
  TestCastDefensiveObjectFallback 4)
- `docs/parity/MAGIC_C_AUDIT.md` — CAST-004/005/006 rows + Scope Notes update
- `CHANGELOG.md` — 2.11.52 entry
- `pyproject.toml` — bump 2.11.51 → 2.11.52
- `docs/sessions/SESSION_STATUS.md` — advance the session pointer

## Verification

- `pytest -n0 tests/test_skills_spells_cast_listing.py
  tests/integration/test_do_cast_object_target.py
  tests/integration/test_finding_013_cast_silent_on_success.py
  tests/integration/test_magic_002_bless_message.py -v`
  — 31 passed
- `pytest -n0 tests/test_combat.py -q` — 32 passed
- GitNexus detect_changes: low risk, 4 files changed, 0 affected processes

## Outstanding

- Spell handlers that only accept `Character` targets (e.g. `bless`, `curse`,
  `poison`, `remove_curse`, `invisibility`) will raise when passed an Object.
  The fix routes correctly (`do_cast` resolves the object); handler-side Object
  branches (ROM `spell_bless(obj)` vs `spell_bless(victim)`) are future
  per-spell parity work.
- `is_safe` / `check_killer` PK gates for offensive spells (ROM
  `src/magic.c:397-413`) remain unenforced from `do_cast`.
- Continue cross-file invariant probe/close cycle.
- Known xdist flakes remain carried-open.
- `Character.pet` stale type annotation remains open (HIGH risk per GitNexus).