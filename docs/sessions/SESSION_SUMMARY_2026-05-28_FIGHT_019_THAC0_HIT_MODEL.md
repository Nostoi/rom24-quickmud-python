# Session Summary — 2026-05-28 — FIGHT-019 combat THAC0 hit model (FINDING-008 sub-issue 1)

## Scope

Continuation of the combat differential-harness thread
(`SESSION_SUMMARY_2026-05-28_SPAWN_001_RNG_DRAW_ORDER.md`). The prior session left
the `combat_melee_rounds` differential gated on **FINDING-008** — three untriaged
sub-issues at step 4 `kill drunk` (C `You miss the drunk.` vs py
`{2You scratch the drunk.{x` ×2). This session triaged all three, then closed the
one real engine parity bug (sub-issue 1) on `master` via the gap-closer flow.

## Outcomes

### `FIGHT-019` — ✅ FIXED (master, 2.11.4, commit `7f4d55f1`)

- **Python**: `mud/combat/engine.py::attack_round`, `compute_thac0`; `mud/config.py`
- **ROM C**: `src/fight.c:386-516` (`one_hit` attack roll), `src/fight.c:445-457` (NPC thac0 branch)
- **Gap**: ROM `one_hit` resolves every melee swing through a single model — the
  THAC0 / `number_bits(5)` roll (re-roll until `< 20`; miss on `diceroll == 0` or
  `diceroll != 19 && diceroll < thac0 - victim_ac`). The port shipped this behind
  the `COMBAT_USE_THAC0` flag **defaulted to False**, so production combat ran a
  non-ROM percent model (`50 + hitroll + AC/2` via `number_percent()`) — diverging
  on both the RNG draw and the hit/miss decision.
- **Fix**: made THAC0 the only path; deleted the percent branch and the
  `COMBAT_USE_THAC0` flag. **Surfaced + fixed a second masked divergence**: the
  THAC0 path always indexed the PC `class_table[ch_class]`, which crashes for NPC
  attackers (`MobInstance` has no `ch_class`) and ignored ROM's NPC rule.
  `compute_thac0` gained a `thac0_pair` override and `attack_round` now derives an
  NPC attacker's `(thac0_00=20, thac0_32)` from its ACT class flag (WARRIOR -10 /
  THIEF -4 / CLERIC 2 / MAGE 6, default -4 "as good as a thief").
- **Verification**: convergence proven empirically *before* the change — seed 777 →
  spawn drunk #3064 → `multi_hit`: percent model = `scratch`, THAC0 model = `miss`
  (= C reference). 15 percent-model-dependent combat tests re-baselined
  ROM-faithfully (pinned nat-19 / high hitroll where they verify damage or XP, not
  hit chance). Fixed a pre-existing `test_room` isolation leak (room 3001 `.people`
  now restored) that THAC0's lower kill rate exposed.
- **Tests**: `tests/integration/test_fight_019_thac0_attack_roll.py` (seed-777 miss
  reproduction + NPC ACT-flag→thac0 selection);
  `tests/test_combat_thac0.py::test_thac0_npc_pair_overrides_class_table`.

### FINDING-008 sub-issue triage (durable record)

The harness reported FINDING-008 as three open hypotheses. All now triaged:

1. **Hit/miss outcome** — ✅ **real parity bug**, fixed as FIGHT-019 above.
2. **Color codes** (`{2…{x` in py, absent in C) — **harness color-normalization**
   (compare-fairness, like FINDING-002/005). Not an engine bug. Still open
   **harness-side** on `diff-harness`.
3. **Double-delivery** (py emits the line twice) — **harness capture artifact**,
   NOT a SINGLE-DELIVERY invariant violation. Confirmed: an isolated `multi_hit`
   for a skill-less, haste-less L5 mage returns exactly **one** line; the replay
   double-counts because it captures the command return value *and* drained
   `char.messages`. Still open **harness-side** on `diff-harness`.

Consequently the `combat_melee_rounds` xfail **correctly stays red** — sub-issues
2/3 keep the differential diverging until reconciled on `diff-harness`. A
persisting xfail here is expected, not a regression.

## Files Modified

- `mud/combat/engine.py` — `attack_round` THAC0-only + NPC thac0 branch; `compute_thac0` `thac0_pair` override; removed `COMBAT_USE_THAC0` import + `urange`.
- `mud/config.py` — removed the `COMBAT_USE_THAC0` feature flag.
- `tests/integration/test_fight_019_thac0_attack_roll.py` — new (2 tests).
- `tests/test_combat_thac0.py` — added NPC `thac0_pair` unit test.
- `tests/test_combat.py`, `tests/test_combat_thac0_engine.py`, `tests/test_damage_reduction_integration.py`, `tests/integration/test_combat_str_app.py`, `tests/integration/test_combat_dex_app.py`, `tests/integration/test_skills_integration.py`, `tests/integration/test_character_advancement.py`, `tests/integration/test_group_combat.py`, `tests/integration/test_mob_ai.py` — re-baselined to the ROM THAC0 model (+ `test_room` isolation fix).
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-019 row ✅ FIXED + brittleness note.
- `CHANGELOG.md` — 2.11.4 entries; `pyproject.toml` — 2.11.3 → 2.11.4.

## Test Status

- `tests/integration/test_fight_019_thac0_attack_roll.py` — 2/2 passing.
- Full suite (parallel, `-n auto`): **4928 passed, 4 skipped, 0 failed** (95s).
- `gitnexus_detect_changes`: 14 files / 32 symbols, **LOW** risk, 0 affected processes.

## Outstanding

- **`master` is 2 commits ahead of `origin/master` (UNPUSHED)** at 2.11.4:
  SPAWN-001 (`47f8fd75`) + FIGHT-019 (`7f4d55f1`).
- **Push blocker (pre-existing):** `ruff check .` reports **10 I001 import-sort
  errors in `mud/spawning/templates.py`** (`apply_spell_effect` function-local
  imports) — present before this session, `--fix`-able. Settle before pushing
  master. (FIGHT-019's own touched files are ruff-clean.)
- **FINDING-008 sub-issues 2 (color normalization) + 3 (capture double-count)** —
  both harness-side, to reconcile on `diff-harness` so the `combat_melee_rounds`
  xfail clears and combat v1 can land. Triage conclusions recorded above.
- **Combat-test brittleness (candidate hardening pass):** unseeded combat tests in
  `tests/test_combat.py` assert exact hit/damage via the old `number_percent` knob
  or `hitroll = ±100` rather than pinning `number_bits`; they pass on RNG-stream
  position. The ones that broke were re-baselined; the rest left intact to keep this
  commit scoped. See the "Notes" section in `docs/parity/FIGHT_C_AUDIT.md`.
- **GitNexus** — reindexed clean this session (exit 0, 41,787 nodes).

## Next Steps

1. **Triage FINDING-008 sub-issues 2/3 on `diff-harness`** (color normalization in
   `compare._norm_lines`; capture double-count in the replay) so the
   `combat_melee_rounds` differential goes clean.
2. **Settle the pre-existing `templates.py` ruff errors**, then push `master`
   (SPAWN-001 + FIGHT-019).
3. **Merge `diff-harness` → master** once combat v1 is green (per the multi-session
   harness plan).
