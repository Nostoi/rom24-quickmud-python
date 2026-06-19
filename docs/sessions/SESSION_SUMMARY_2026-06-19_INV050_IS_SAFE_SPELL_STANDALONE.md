# Session Summary — 2026-06-19 — INV-050 gate: `is_safe_spell` standalone port

## Scope

Continued the cross-file / divergence-class sweep (per-file audit tracker
exhausted). Picked up the highest-leverage discrete follow-up from the prior
handoff: the **INV-050 gate** — auditing `is_safe_spell` against ROM's
standalone function before the broader bool-retirement could proceed. The audit
immediately revealed the gate was a real divergence, not just a paperwork step,
so it was closed in one TDD commit.

## Outcomes

### INV-050 (gate) — ✅ CLEARED — `is_safe_spell` now standalone-faithful

- **Python**: `mud/combat/safety.py:is_safe_spell` (rewritten as a faithful
  standalone port); `mud/skills/handlers.py:_is_safe_spell` (now a thin delegate).
- **ROM C**: `src/fight.c:1126-1218` (the STANDALONE `is_safe_spell`, distinct
  from `is_safe` at `:1018-1124`); gate consumer `src/magic.c:484`
  (TAR_OBJ_CHAR_OFF).
- **Gap**: `safety.py:is_safe_spell` delegated to the silent `is_safe` bool,
  which is bidirectionally divergent from ROM's *separate* `is_safe_spell`. It
  lacked: the immortal/area bypasses (`:1137`, `:1182`), the
  `victim->fighting == ch` retaliation bypass evaluated **before** the NPC
  ROOM_SAFE branch (`:1134` vs `:1144`), the legal-kill `is_same_group` clauses
  (`:1169`, `:1175`, `:1198`), and the entire PC-vs-PC clan PK ladder
  (`:1205-1216`).
- **Key finding**: a faithful copy already existed at
  `handlers.py:_is_safe_spell` (area spells) — but the `do_cast` object-target
  path used the divergent `safety.py` one. Fix promoted the faithful logic into
  `safety.py` as the single canonical implementation and pointed
  `handlers._is_safe_spell` at it (de-dup). Robust flag-reads kept self-contained
  in `safety.py` (`_spell_act_flags`/`_has_shop`/… mirror the handlers helpers)
  so the import direction stays handlers → safety.
- **Tests**: `tests/integration/test_inv050_is_safe_spell_standalone.py` — 4
  passing (3 were RED before the fix, pinning the divergences; 1 positive
  control). Verified the gate ordering against `src/magic.c:484` (is_safe_spell
  precedes `check_killer` at `:498`).
- **Collateral**: corrected one stale test —
  `test_do_cast_pk_gates.py::test_cast_curse_sets_killer_flag` had asserted the
  pre-fix divergence (a clan PC striking a non-clan PC >8 levels below was
  wrongly allowed to reach `check_killer`). Re-set to a legal-PK case (victim in
  a clan, equal level) per AGENTS.md "a test contradicting ROM C is the bug".

## Files Modified

- `mud/combat/safety.py` — `is_safe_spell` rewritten as faithful standalone ROM
  port + 6 self-contained flag-read helpers (`_spell_*`).
- `mud/skills/handlers.py` — `_is_safe_spell` collapsed to a delegate (−~80 lines).
- `tests/integration/test_inv050_is_safe_spell_standalone.py` — new, 4 tests.
- `tests/integration/test_do_cast_pk_gates.py` — corrected stale KILLER test.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-050 row: gate CLEARED.
- `CHANGELOG.md` — `Fixed` entry.
- `pyproject.toml` — 2.14.131 → 2.14.132.

## Test Status

- `tests/integration/test_inv050_is_safe_spell_standalone.py` — 4/4 passing.
- Area suites (do_cast PK gates, area-effect spells, spell damage, skills_mass,
  spec_funs, combat_assist) — 119/119 passing.
- Full suite: green (exit 0).
- `ruff check` — clean.
- `gitnexus_detect_changes` — scope confirmed (`is_safe_spell`, `_is_safe_spell`,
  the corrected test, tracker sections); risk LOW, 0 affected processes.

## Next Steps

INV-050's gate is now cleared, so the remaining tracked task is **unblocked**:
collapse `is_safe`'s callers onto the faithful `_kill_safety_message` mirror (or
make the silent bool a thin wrapper), leaving only the intentionally-silent
`apply_damage` re-check (`combat/engine.py`, FIGHT-002) on the raw bool. Other
open follow-ups: `mud/entrypoint.py` dead code. The higher-yield
enumeration-independent lever per `docs/parity/DIVERGENCE_CLASS_ROSTER.md`
remains the Hypothesis state-machine → diff_harness widening (Class 11 mobprog
paths are complete; the open frontier is non-mobprog scenario coverage).
