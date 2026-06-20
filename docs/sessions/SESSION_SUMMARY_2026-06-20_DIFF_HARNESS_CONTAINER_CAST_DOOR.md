# Session Summary — 2026-06-20 — Differential harness: containers, cast-position gate, door lock cycle

## Scope

Picked up from the INV-052 + CAST-013 + INTERP-028 handoff (v2.14.200), whose
"START HERE" directive was to **expand the differential harness**
(`tools/diff_harness/`) — the only enumeration-*independent* parity oracle now
that the per-file audit tracker is drained and the cross-INV / per-file passes
are enumeration-dependent (`DIVERGENCE_CLASS_ROSTER.md` guardrail #3). The
instrumented C shim (`src/diffshim`) was already built; the harness was green
(68 passed). Authored three net-new scenarios on surfaces grep-verified as
exercised by **zero** prior scenarios, captured C goldens from the ROM 2.4b6
binary, and confirmed Python convergence.

## Outcomes

### `container_put_get` — ✅ NEW SCENARIO (clean negative)

- **Scenario**: `tools/diff_harness/scenarios/container_put_get.json` (15 steps)
- **Golden**: `tests/data/golden/diff/container_put_get.golden.json`
- **Surface**: `put <obj> <container>`, get-from-container (`get sword bag`),
  `look in <container>`, re-nesting, plus LIFO carry-list ordering through the
  transitions (bag 3032 + sword 3021).
- **Result**: converges end-to-end. Locks the INV-039 head-insert /
  FINDING-019/021/022 container surface as a committed JSON scenario (previously
  only covered by generated/Hypothesis tests).

### `cast_position_gate` — ✅ NEW SCENARIO (differentially locks CAST-013)

- **Scenario**: `tools/diff_harness/scenarios/cast_position_gate.json` (6 steps)
- **Golden**: `tests/data/golden/diff/cast_position_gate.golden.json`
- **ROM C**: `src/magic.c:341` (`ch->position < skill_table[sn].minimum_position`
  → "You can't concentrate enough."), `src/const.c:961` (armor `POS_STANDING`).
- **Python**: `mud/commands/combat.py:915-917` (CAST-013 per-spell gate).
- **Mechanism**: minimal pair on a single spell. `cast armor` (`POS_STANDING`=8)
  is **rejected** at `__char_position=7` (FIGHTING) and **accepted** at
  `__char_position=8` (STANDING, `__seed=777` → mana 100→80, affects=['armor']).
  The reject-at-7 leg is the exact regression a flat-`POS_FIGHTING` (=7)
  implementation could **not** produce, so a passing golden can only come from
  the per-spell behavior. The gate is an early reject before any RNG draw / mana
  deduction on **both** engines (verified by source reading), so the reject leg
  is deterministic without seeding.
- **Result**: converges end-to-end — CAST-013 is now locked against the C oracle.

### `door_lock_cycle` — ✅ NEW SCENARIO (clean negative)

- **Scenario**: `tools/diff_harness/scenarios/door_lock_cycle.json` (11 steps)
- **Golden**: `tests/data/golden/diff/door_lock_cycle.golden.json`
- **Surface**: full keyed-door lifecycle on Cityguard HQ 3110 → Captain's Office
  3142 (door reset state closed+locked, key 3120): `open west` while locked →
  "It's locked." → `__oload=3120; get key` → `unlock west` (*Click*) →
  `open west` (Ok.) → `west` (traverse; room shows 4 cityguards + captain in the
  FINDING-031 reset order) → `east` → `close west` (Ok.) → `lock west` (*Click*).
  All deterministic — no `pick` RNG.
- **Result**: converges end-to-end. Confirms Python applies D-resets
  (closed+locked door state) identically to ROM `reset_room`, and the
  open/close/unlock/lock verbs + keyed traversal match.

No engine divergence surfaced — three clean negatives. `FINDINGS.md` unchanged
(it records divergences, not clean scenarios).

## Files Modified

- `tools/diff_harness/scenarios/container_put_get.json` — new scenario
- `tools/diff_harness/scenarios/cast_position_gate.json` — new scenario
- `tools/diff_harness/scenarios/door_lock_cycle.json` — new scenario
- `tests/data/golden/diff/container_put_get.golden.json` — new C golden
- `tests/data/golden/diff/cast_position_gate.golden.json` — new C golden
- `tests/data/golden/diff/door_lock_cycle.golden.json` — new C golden
- `tests/test_differential_smoke.py` — refreshed the stale "four scenarios"
  `KNOWN_DIVERGENCES` comment (now 44 scenarios, all converge)
- `CHANGELOG.md` — `Added` entry
- `pyproject.toml` — 2.14.200 → 2.14.201

No production engine code changed (test data + one comment only).

## Test Status

- `pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py` —
  **71 passed** (was 68; +3 new scenario tests). 44 scenarios / 44 goldens.
- Capture was per-scenario (`--scenario <name>`), so no provenance churn on the
  other 41 goldens.
- GitNexus reindexed at session start (`npx gitnexus analyze --skip-agents-md`,
  exit 0) — MCP graph current.

## Next Steps

Continue widening the differential harness — still grep-verified absent:
**character advancement** (`practice`/`train`/`gain`), **death lifecycle**
(`corpse` → auto-loot/auto-gold → `sacrifice`; the mob_death_trigger scenario
fires the trigger, not the corpse/loot mechanics), and **group/follow**
(`follow`/`group`). These mix RNG (practice/train rolls, combat-to-death) so
they require careful `__seed` bracketing (the `shop_buy_weapon.json` /
`affect_armor.json` technique) — author the deterministic slice first
(`gain`/`sacrifice`/`group` membership) before the RNG legs. A divergence is a
FINDING (→ `FINDINGS.md` → `/rom-gap-closer` or new INV), never a golden to
overwrite. Secondary: the `test_all_commands.py` `tap` alias false-positive
(harness artifact, low).
