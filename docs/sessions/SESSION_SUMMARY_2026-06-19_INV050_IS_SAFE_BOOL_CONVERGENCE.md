# Session Summary — 2026-06-19 — INV-050 `is_safe` bool convergence (thin wrapper)

## Scope

Picked up the remaining (now-unblocked) INV-050 task from the prior session's
handoff: collapse the silent bool `mud/combat/safety.py:is_safe` onto the single
faithful mirror `mud/commands/combat.py:_kill_safety_message`, leaving only the
intentionally-silent `apply_damage` re-check on the bool. The previous session
cleared the gate (made `is_safe_spell` standalone-faithful), so this could
proceed without silently shifting `do_cast`'s object-target branch.

What started as a "make the bool a thin wrapper" gap-close turned out to be a
behavior-changing refactor: the faithful predicate broke 45 unit tests across 12
files. A canary check confirmed **all 45 are fixture shortcuts** (roomless and/or
non-clan PC pairs) that leaned on the old bool's leniency — **production impact is
nil** (combatants always have rooms; PC-vs-PC is gated upstream by
`do_kill`/`do_murder`/`do_cast`). User chose "do the dedup + fix fixtures" over
deferring; this session does that.

## Outcomes

### `INV-050` — ✅ ENFORCED (convergence complete)

- **Python**: `mud/combat/safety.py:is_safe` (now ~10 lines)
- **ROM C**: `src/fight.c:1018-1124` (`is_safe`), `:730` (the `damage()` re-check)
- **Change**: `is_safe` now delegates to the canonical mirror —
  `return _kill_safety_message(char, victim) is not None` (function-local import,
  mirroring `spec_funs._is_safe_mirror`). Deleted the ~85-line divergent body.
  This removes the bidirectional divergence: over-blocks (`is_ghost`, `ACT_GAIN`,
  ROOM_SAFE for all victims) and under-blocks (immortal bypass :1026,
  `victim->fighting == ch` retaliation bypass :1023, the PC-vs-PC clan PK ladder
  :1096-1120). The sole caller — the intentionally-silent `apply_damage` re-check
  (FIGHT-002) — discards the string and is now ROM-faithful in its predicate.
- **Tests**: new guard `tests/integration/test_inv050_is_safe_bool_faithful.py`
  (2 tests) — asserts `is_safe(ch,v) == (_kill_safety_message(ch,v) is not None)`
  across branches, incl. the retaliation-bypass-before-ROOM_SAFE ordering.
- **Impact**: `gitnexus_impact` — only d=1 caller is `apply_damage`;
  `detect_changes` LOW risk, 0 affected processes.

### Stale-assertion correction

- `tests/integration/test_fight_c_safe_room_damage_gate.py` asserted *no damage*
  for a victim **fighting the attacker** in a safe room. ROM `is_safe` :1023
  evaluates `victim->fighting == ch → FALSE` **before** the ROOM_SAFE gate :1034,
  so the fight continues. Reworked to use a fresh (non-retaliating) NPC victim,
  preserving the test's intent (the re-check blocks fresh aggression into a safe
  room) while being ROM-faithful.

### Test-fixture legalization (45 tests, 12 files)

Two ROM-faithful behaviors the old bool lacked drove the failures: the
`in_room == NULL → safe` guard (:1020) and the PC-vs-PC clan ladder (:1096-1120).
Fixtures were updated to use real non-safe rooms and legal-PK pairs (clan members
within 8 levels, or `PLR_KILLER` victims). NPC victims sidestep the clan ladder.

## Files Modified

- `mud/combat/safety.py` — `is_safe` → thin wrapper over `_kill_safety_message`.
- `tests/integration/test_inv050_is_safe_bool_faithful.py` — **new** guard.
- `tests/integration/test_fight_c_safe_room_damage_gate.py` — stale assertion corrected.
- `tests/integration/test_fight036_dirt_kick_pronoun_masking.py`,
  `tests/integration/test_fight037_dirt_kick_victim_legs.py` — `_pc` gains clan.
- `tests/test_combat.py`, `tests/test_combat_damage_types.py`,
  `tests/test_fighting_state.py`, `tests/test_skills_combat.py`,
  `tests/test_combat_death.py`, `tests/test_combat_rom_parity.py`,
  `tests/test_skills_learned.py`, `tests/test_skills_damage.py`,
  `tests/test_spell_breath_weapons_rom_parity.py`,
  `tests/test_spell_critical_gameplay_rom_parity.py`,
  `tests/test_spell_area_effects_rom_parity.py`,
  `tests/test_spell_damage_additional_rom_parity.py` — rooms + legal-PK fixtures.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-050 row → ✅ ENFORCED.
- `CHANGELOG.md` — Fixed entry.
- `pyproject.toml` — 2.14.132 → 2.14.133.

## Test Status

- Targeted files: all green when run with `-n0` (per-file verification).
- Full suite: **5841 passed, 4 skipped, 0 failed** (`pytest -q`, ~9 min serial-ish).
- `ruff check` / `ruff format --check`: clean.

## Next Steps

- INV-050 is now fully closed (✅ ENFORCED). The only `is_safe` caller is the
  faithful, intentionally-silent `apply_damage` re-check.
- Lower priority: `mud/entrypoint.py` dead code.
- Higher-yield enumeration-independent lever per
  `docs/parity/DIVERGENCE_CLASS_ROSTER.md`: the Hypothesis state-machine →
  diff_harness widening (Class 11 mobprog paths complete; open frontier =
  non-mobprog scenario coverage).
- Note: `tests/test_mobprog_triggers.py::test_event_hooks_fire_rom_triggers`
  passed alone and in the final full run, but flaked once mid-session under a
  different xdist worker grouping — a pre-existing cross-file isolation
  sensitivity, not caused by this change. Worth hardening if it recurs.
