# Session Summary — 2026-04-28 — `interp.c` `one_argument` port + `tail_chain` verification

## Scope

Third loop iteration of the same-day `interp.c` push (releases 2.6.10
and 2.6.11 already landed). Goal was to close the two remaining
parser/extension-hook gaps:

- `INTERP-015` — replace `shlex.split` with a ROM-faithful
  `one_argument` port so backslash and quote semantics match the C
  source.
- `INTERP-016` — verify `tail_chain()` is a no-op in stock ROM and
  document/close-defer.

Both closed in one commit per `rom-gap-closer` discipline (one
production change `_one_argument` plus one documentation flip).

## Outcomes

### `INTERP-015` — ✅ FIXED

- **Python**: `mud/commands/dispatcher.py` (`_one_argument`,
  `_split_command_and_args`).
- **ROM C**: `src/interp.c:766-798`.
- **Gap**: `_split_command_and_args` used `shlex.split` for the
  alphanumeric branch. shlex treats `\` as an escape and consumes
  unbalanced quotes differently from ROM's `one_argument` (which is
  byte-for-byte: lowercase the head, support `'` and `"` as
  single-char quote sentinels with no nesting, treat backslash
  literally, strip surrounding whitespace).
- **Fix**: ported `_one_argument(argument: str) -> tuple[str, str]`
  that mirrors ROM exactly. `_split_command_and_args` now routes the
  alphanumeric/quoted branch through it. Single-char punctuation
  tokens (`.`, `,`, `/`, `;`, `:`, `'`-not-as-sentinel handled
  separately) still short-circuit. `shlex` import removed.
- **Tests**: 8 parametrized cases in
  `test_interp_015_one_argument_matches_rom` covering plain split,
  single- and double-quoted heads, literal backslash, lowercasing,
  empty quoted token, leading/trailing whitespace.
- **Test side-effect**: `tests/test_alias_parity.py::test_alias_case_sensitivity`
  began failing because it asserted "uppercase doesn't match
  lowercase alias", which was Python's shlex-era behavior, not ROM.
  ROM `do_alias` stores keys via `one_argument` (lowercased —
  `src/alias.c:127, 217`); `substitute_alias` then compares the
  lowercased input head against the stored key
  (`src/alias.c:78-81`) — so uppercase input *does* expand a
  lowercased alias. Renamed the test to
  `test_alias_case_insensitive_lookup_matches_rom` and flipped its
  assertion. Per AGENTS.md the test was the bug, not the
  implementation.
- **Commit**: `22fa717`.

### `INTERP-016` — ✅ CLOSED-DEFERRED

- **ROM C**: `src/interp.c:557` (call site), `src/db.c:3929`
  (definition).
- **Gap (audit-only)**: ROM `interpret()` calls `tail_chain()` at end
  of dispatch.
- **Investigation**: `src/db.c:3929-3932` is `void tail_chain(void) { return; }` —
  empty function. Comment at `src/db.c:3920-3927` describes it as a
  hook used by some derivatives for stack-tail-call extension; stock
  ROM behavior is "do nothing".
- **Resolution**: row flipped to ✅ CLOSED-DEFERRED. Python already
  matches stock ROM by omission. Will only be re-opened if a
  downstream extension wires the hook.
- **Commit**: bundled into `22fa717` (no code change).

## Files Modified

- `mud/commands/dispatcher.py` — added `_one_argument()`; rewrote
  `_split_command_and_args` to use it; dropped `shlex` import.
- `tests/integration/test_interp_dispatcher.py` — added 8
  parametrized cases for `_one_argument`.
- `tests/test_alias_parity.py` — renamed and flipped
  `test_alias_case_sensitivity` → `test_alias_case_insensitive_lookup_matches_rom`
  with ROM citations.
- `docs/parity/INTERP_C_AUDIT.md` — flipped INTERP-015 → ✅ FIXED;
  INTERP-016 → ✅ CLOSED-DEFERRED.
- `CHANGELOG.md` — added `[2.6.12]` section.
- `pyproject.toml` — `2.6.11` → `2.6.12`.

## Recent Commits (this iteration)

- `22fa717` — `fix(parity): interp.c:INTERP-015 — port ROM one_argument; close INTERP-016`

## Test Status

- `pytest tests/integration tests/test_alias_parity tests/test_help_system tests/test_communication`
  → **1229 passed, 10 skipped, 0 failed** (≈3 min wall-clock).
- New tests this iteration: 8 cases in `test_interp_015_*`.

## Audit Progress

- `interp.c`: **22 / 24 gaps fixed** + 1 closed-deferred (INTERP-016)
  + 1 deferred-pending (INTERP-013, blocked on `ACT_OBJ_C`
  `do_wear` port). Tracker row remains ⚠️ Partial because
  INTERP-013 is not actually fixed; only behavior-equivalent.
- ROM C files audited overall: **16 / 43**.

## Next Steps

The only remaining `interp.c` work is `INTERP-013` and it requires
ACT_OBJ_C side first:

1. **`ACT_OBJ_C` audit add-on** — file new gaps for the wield/hold
   features Python's `do_wear` is missing:
   - `WEAR-001` — STR wield-weight check, weapon-skill flavor
     message, two-hand vs shield conflict
     (`src/act_obj.c:1616-1668` vs `mud/commands/equipment.py:329-382`).
   - `WEAR-002` — HOLD auto-unequip the existing held item
     (`src/act_obj.c:1670-1678` vs
     `mud/commands/equipment.py:451-454` which rejects).
2. Close `WEAR-001`/`WEAR-002` with TDD per
   `rom-gap-closer`, then collapse `do_wield`/`do_hold` into aliases
   on `do_wear` to satisfy `INTERP-013`.
3. **Pre-existing RNG-isolation flake** — add session-scoped
   `rng_mm.seed_mm` autouse fixture to `tests/conftest.py`.
