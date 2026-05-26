# Session Status — 2026-05-25 — INV-016 → INV-019 position-promotion (2.9.10 → 2.9.16)

## Current State

- **Active pass**: cross-file invariants + opportunistic gap closures.
  Seven clusters landed today: INV-016 (2.9.10), HPCNT-001 (2.9.11),
  die_follower (2.9.12), INV-017 (2.9.13), INV-018 (2.9.14),
  group XP NPC level-1 floor (2.9.15), INV-019 (2.9.16).
- **2.9.16** — INV-019 POSITION-PROMOTION-ON-HEAL filed as ✅ ENFORCED.
  Probe found the contract already correct by construction across three
  modules (`update_pos`, heal handlers, regen tick); pinned with a
  3-test regression suite in the spirit of INV-017.

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.16 |
| Tests | 4724 passed + 3 new (INV-019 pins) |
| Cross-file invariants | 19 of ~20 budget; INV-001 … INV-019 ✅ ENFORCED |
| Branch | `master` (2.9.10–2.9.15 on origin; 2.9.16 staged) |
| Watch list | wear-off ✅, group XP ✅, position-promotion ✅ |

## Next Intended Task

The position-promotion probe is complete. With 19 of ~20 INV budget
spent and all named candidate areas covered (affect ticks, position
transitions both directions, tick iteration safety, message wear-off
hybrid, follower/leader chains), the next session needs to decide:

1. **Hunt a 20th INV** — last remaining candidate from earlier
   queues: mob script triggers (TRIG_GREET / TRIG_GIVE / TRIG_BRIBE
   cross-file edges), or shop transaction atomicity
   (shop_keeper → obj_to_char → cost deduction). Both probes are
   5-minute scope.
2. **Restructure the budget** — at 19/~20, AGENTS.md notes a
   restructuring discussion is due if more contracts surface. Worth
   re-skimming the per-file audit tracker for any rows touching
   cross-module surfaces that should be lifted to INVs.
3. **Switch passes** — if cross-file invariants are functionally
   exhausted, the next mode is either P3 cleanup
   (`ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` P3 at 75%) or integration
   test coverage (`INTEGRATION_TEST_COVERAGE_TRACKER.md`).

Probe method (5-minute scope): read ROM C contract → read Python
equivalent → write one failing test. Then close as a single
gap-closer commit or file as the next free INV-NNN.

No push to origin without explicit per-cluster user approval.
Pending push: 2.9.16.
