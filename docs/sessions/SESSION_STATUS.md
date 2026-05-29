# Session Status — 2026-05-29 — FINDING-011 closed (FIGHT-028 combat miss line keeps the attack noun)

## Current State

- **Active mode**: differential-harness-driven combat parity verification. The
  `combat_melee_rounds` scenario now **converges end-to-end** on both engines — the
  differential harness has **zero known divergences** (`KNOWN_DIVERGENCES` is empty).
- **Last completed** (this session):
  - **`FIGHT-028`** ✅ (master 2.11.16, `9b2fd868`) — `dam_message` no longer forces
    the no-noun `TYPE_HIT` template on a miss. ROM `src/fight.c:2157` selects the
    template purely on `dt == TYPE_HIT` vs not; `dam == 0` only swaps the verb to
    "misses". Deleted the `percent <= 0` early-return so a resolved-noun miss renders
    `"The drunk's beating misses you."` like its own hit path (also fixes low-damage
    hits rounding to percent 0). **Closes FINDING-011.** Re-baselined 5 stale
    noun-less miss assertions with ROM citations.
  - **`FINDING-011`** ✅ RESOLVED (diff-harness `4094aded`) — merged FIGHT-028,
    confirmed `combat_melee_rounds` converges with FINDING-011 *removed* from
    `KNOWN_DIVERGENCES` (clean diff, not toleration); marked RESOLVED in `FINDINGS.md`.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-29_FINDING_011_FIGHT_028_MISS_ATTACK_NOUN.md](SESSION_SUMMARY_2026-05-29_FINDING_011_FIGHT_028_MISS_ATTACK_NOUN.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.16 |
| Tests | 4950 passed, 4 skipped (full suite, parallel, ~143s) |
| ROM C files audited | 43 / 43 (per-file pass complete; differential + cross-file invariants active) |
| Active focus | `fight.c` combat-tick — differential converges, zero known divergences |

## Next Intended Task

The per-scenario divergence chase (FINDING-007 → -011) is exhausted for the existing
differential scenarios — `combat_melee_rounds` and `movement_get_drop` both converge
end-to-end. Next session should either:

1. **Add a new differential scenario** exercising an un-probed path (spell combat,
   multi-mob room, group fight, shop/pet interaction) to surface the next divergence; or
2. Pick up an Outstanding follow-up from `docs/parity/FIGHT_C_AUDIT.md` — `ACT-CAP-001`
   (non-combat act() capitalization at `broadcast_room`/`act_format`) is the most
   self-contained, then `SHOP-PET-001` (pet `dam_type` bypasses `from_prototype`).

Also pending (test-infra, not a parity gap): seed RNG in the `test_combat_death.py`
unit death tests to kill the xdist ordering flake documented in this session's summary.
