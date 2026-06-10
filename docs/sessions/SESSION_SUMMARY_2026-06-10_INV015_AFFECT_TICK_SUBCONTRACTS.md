# Session Summary — 2026-06-10 — INV-015 Affect-Tick Sub-Contract Enforcement

## Scope

Continuing from v2.13.60 (INV-041 closed). The active pass is cross-file
invariants. This session selected the first candidate from SESSION_STATUS.md:
**affect-tick edge contracts** (`src/update.c:762-786 char_update` affect-expiry
loop). The approach was probe-then-scope: read the ROM C source, compare to
`mud/affects/engine.py:tick_spell_effects`, verify correctness, then lock any
unguarded sub-contracts as enforcement tests.

## Investigation

Two specific contracts were probed from `src/update.c:768` and `:774-775`:

1. **RNG unconditional consumption (GL-026)** — ROM's `if (number_range(0,4) == 0
   && paf->level > 0)` evaluates the LHS unconditionally (C `&&` is
   left-to-right). Python's `tick_spell_effects` correctly calls
   `rng_mm.number_range(0, 4)` before the `level > 0` check, with a comment
   explicitly noting the ordering constraint. The existing code was correct.

2. **Msg_off dedup** — `if (paf_next == NULL || paf_next->type != paf->type
   || paf_next->duration > 0)` emits wear-off only for the last consecutive
   same-type expiring affect. Python's `should_emit` predicate at lines 78-82
   mirrors this exactly. Correct.

3. **Dual-path removal (shadow vs raw AffectData)** — `sync_spell_effect_to_affected`
   appends shadow `AffectData` entries **directly** (bypassing `affect_to_char`),
   so `affect_modify(True)` is never called on them — the comment at engine.py:92-99
   is accurate post-INV-040. The split between bare removal (spell_effects-managed)
   and `affect_remove` (raw) is correct and consistent.

**Probe result: clean.** No parity gaps found.

## Outcomes

### INV-015 sub-contracts — ✅ LOCKED (2.13.61)

- **ROM C**: `src/update.c:768` — RNG consumed unconditionally per `duration>0`
  affect; `src/update.c:774-775` — dedup: only last consecutive same-type expiry
  fires `msg_off`.
- **Python**: `mud/affects/engine.py:tick_spell_effects` — both contracts verified
  correct.
- **New enforcement tests** (added to existing file):
  - `test_rng_slot_consumed_per_duration_positive_affect` — seeds RNG, applies two
    `duration>0` affects (level=10 + level=0), ticks once, asserts exactly two RNG
    slots consumed. GL-026 regression guard: if operands were swapped, the level=0
    affect would skip the roll and desync the global RNG stream.
  - `test_msg_off_dedup_suppresses_all_but_last_same_type_affect` — two same-type
    `duration=0` raw AffectData entries, one tick, asserts exactly one wear-off
    message emitted (from the last one).

## Files Modified

- `tests/integration/test_inv015_affect_tick_lifecycle.py` — two new enforcement
  tests + `rng_mm` import
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-015 description extended
  with RNG-slot and dedup sub-contract notes (2.13.61)
- `CHANGELOG.md` — added `[2.13.61] Added` entry
- `pyproject.toml` — 2.13.60 → 2.13.61

## Test Status

- `pytest tests/integration/test_inv015_affect_tick_lifecycle.py tests/integration/test_inv018_wear_off_message_for_raw_affect.py -v -n0` — 6/6 passed
- Full suite: **5500 passed, 5 skipped** (82.37s)

## Next Steps

Cross-file invariants remains the active pass. Two remaining candidates:

1. **Position-transition invariants** — ROM position changes
   (STANDING→FIGHTING, DEAD→SLEEPING via `update_pos`) must trigger correct
   broadcasts and affect applications. INV-016 covers the broadcast side; no INV
   row yet covers the affect-application side (e.g. sanctuary stripping at certain
   positions). A probe-then-scope pass on `src/update.c:update_pos` vs
   `mud/combat/engine.py:update_pos` would determine if a gap exists.
2. **Affect-join contract** — noted as ⚠️ Partial in `docs/parity/HANDLER_C_AUDIT.md`
   row `affect_join`: ROM uses `affect_join` for plague-spread (averages levels +
   sums durations+modifiers when victim already has plague), but Python calls
   `affect_to_char` directly, stacking a second plague entry instead of merging.
   This was flagged in INV-040's "Note" field and is a concrete open gap.
