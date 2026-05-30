# Session Status — 2026-05-30 — CAST-007 PK Gates

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted — no
  ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **CAST-007 — do_cast PK safety gates ✅ DONE (2.11.53)** —
    ROM `src/magic.c:395-413` (`TAR_CHAR_OFFENSIVE`) and `:481-495`
    (`TAR_OBJ_CHAR_OFF`) PK gates enforced from `do_cast`: `is_safe` /
    `is_safe_spell` ("Not on that target." for PC casters), `check_killer`
    (KILLER flag for clan PCs attacking innocent PCs, charm stripping side
    effect), and the AFF_CHARM master gate ("You can't do that on your own
    follower."). Object targets bypass all three gates per ROM. Defensive
    spells have no PK gates per ROM. 17 integration tests.
  - **Before that**: CAST-004/005/006 (2.11.52), group-command lint (2.11.51),
    INV-025 (2.11.50), INV-001 shop haggle cousin (2.11.49).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-30_DO_CAST_PK_GATES.md](SESSION_SUMMARY_2026-05-30_DO_CAST_PK_GATES.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.53 |
| Tests | 17 new integration tests (all green); full suite passes |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Active focus | Cross-file invariants — continue probe/close cycle |

## Next Intended Task

Continue cross-file invariants as the primary pass. The `do_cast` surface is
now 7/7 gaps closed (CAST-001 through CAST-007). Remaining future parity work
is per-spell handler Object branches (bless/curse/poison/etc. accepting Object
targets — the routing is correct; the handlers need Object branches).

Carried-open items: known xdist flakes (`test_combat_death.py`,
`test_backstab_uses_position_and_weapon`); `Character.pet` stale type annotation
(GitNexus reports HIGH risk on the field, so handle deliberately).

## Commit / push state

- Working tree: clean (all changes included in the 2.11.53 commit).