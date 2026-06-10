# Session Summary — 2026-06-10 — FINDINGS.md numbering cleanup

## Scope

Continuation from v2.13.61 (INV-015 sub-contracts locked). The active pass is
cross-file invariants. This session opened by verifying both "next task"
candidates from the previous SESSION_STATUS.md were already resolved (affect-join
plague-spread was ✅ FIXED 2026-06-08 in HANDLER_C_AUDIT; position-transition
affect-application had no gap — `update_pos` in C is pure HP→position math with
no affect stripping, and Python matches exactly). The diff harness confirmed the
codebase is clean (38 passed, 1 skipped). The productive work this session was
reconciling three documentation-debt items in `tools/diff_harness/FINDINGS.md`
that had accumulated across multiple sessions.

## Investigation

Two cross-file probe candidates from SESSION_STATUS.md were evaluated:

1. **Affect-join contract** — confirmed already fixed: `game_loop.py` calls
   `affect_join(vch, new_af)` after the `has_affect(PLAGUE)` guard; HANDLER_C_AUDIT
   shows `affect_join` ✅ FIXED 2026-06-08.

2. **Position-transition affect-application** — confirmed not a gap: ROM
   `src/fight.c:update_pos` is pure HP→position math (no affect stripping); the
   `AFF_SLEEP` strip lives in `set_fighting` (fight.c:1424-1425). Python
   `set_fighting` at `mud/combat/engine.py:809-828` correctly calls
   `ch.strip_affect("sleep")`. Both functions match faithfully.

Running `pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py`
confirmed 38 scenarios pass, 1 skipped (`shop_sell_keeper_broke` — known expected
skip).

## Outcomes

### FINDINGS.md documentation cleanup — ✅ RESOLVED

Three accumulated documentation-debt items fixed:

1. **Duplicate FINDING-026** — the room-occupant look-order finding (resolved
   2026-06-09, filed after FINDING-030 was the max) was mistakenly given the ID
   FINDING-026, colliding with the existing shop sell/value finding from 2026-06-03.
   Renamed to **FINDING-031**.

2. **Duplicate FINDING-024** — the class-13 bypass sweep (15 runtime `.append`
   bypass sites) was filed with the same ID as the save/load carry-seq finding.
   Renamed to **FINDING-032**.

3. **Stale ⚠️ OPEN block** — the original pre-resolution text for what became
   FINDING-022 (`look in` contents indent) was left appended to FINDING-032's entry
   and never removed when FINDING-022 got its own resolved section (2026-06-03).
   Replaced with a one-line forward reference.

`docs/parity/DIVERGENCE_CLASS_ROSTER.md` updated to reference FINDING-031 (was
FINDING-026) for the room-occupant ordering entry.

## Files Modified

- `tools/diff_harness/FINDINGS.md` — renamed FINDING-026→FINDING-031,
  FINDING-024 (class-13)→FINDING-032; removed stale ⚠️ OPEN block (15 lines)
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — updated FINDING-026 references to
  FINDING-031 (2 occurrences)

## Test Status

- Diff harness: 38 passed, 1 skipped (`shop_sell_keeper_broke` known skip)
- Full suite: 5500 passed, 5 skipped (no regressions — doc-only commit)

## Next Steps

The cross-file invariants pass remains active. All 26 INV rows are ✅ ENFORCED
and both session-status candidates were confirmed already resolved. The most
concrete next candidates:

1. **New diff-harness scenario** — author a scenario exercising an untested
   surface: charm/follower wear-off lifecycle, sanctuary+haste affect bitvectors
   with tick expiry, or drink/eat/food consumption. These are surfaces the harness
   does not currently cover and would provide C-oracle enforcement where no golden
   exists. Schema is at `tools/diff_harness/scenarios/`; the scenario skips
   gracefully until a golden is captured against the instrumented C binary.

2. **MATH-002/003/004** — documented ⚠️ OPEN hygiene items (LOW severity) in
   `docs/parity/audits/MATH_AND_RNG.md`. Provably-non-negative `//` operands in
   `mud/combat/engine.py` and `mud/skills/handlers.py` that would need `c_div` only
   if the operands could go negative. Held for a future PARITY008 lint rule; no
   observable behavioral gap.
