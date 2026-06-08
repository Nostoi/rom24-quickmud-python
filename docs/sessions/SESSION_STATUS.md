# Session Status — 2026-06-08 — Hypothesis broke-keeper sell rules (2.13.33)

## Current State

- **Active mode**: cross-file invariants / diff-harness expansion (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **`zero_keeper_wealth` + `sell_sword_to_broke_keeper` Hypothesis rules (2.13.33).**
    Extends `DeterministicNoRngDiffMachine` to fuzz the keeper-broke sell-error path.
    `_keeper_is_broke` state tracks whether `__mob_gold=0` / `__mob_silver=0` have
    been emitted; `sell_sword_to_weaponsmith` is guarded so the successful and failed
    sell paths are mutually exclusive. Position-transition and affect_strip probes
    confirmed clean (no gaps).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-08_HARNESS_KEEPER_BROKE_HYPOTHESIS_RULES.md](SESSION_SUMMARY_2026-06-08_HARNESS_KEEPER_BROKE_HYPOTHESIS_RULES.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.33 |
| Tests | 5448 passing, 5 skipped (5453 collected) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 25 enforced |
| Diff-harness scenarios | 10 static + 17 generated-oracle tests |
| Diff-harness shop scenarios | `shop_buy_weapon`, `shop_sell_weapon`, `shop_buy_insufficient_funds`, `shop_sell_keeper_broke` |
| Shop integration tests | 15 passing |

## Next Intended Task

**Cross-file invariant candidates** — any of the following:

1. **INV-025 follow-up** — broader `_push_message`/`broadcast_room` narration surface:
   non-combat `act()` callsites in Python that may not dispatch `mp_act_trigger_room`.
   Run `grep -rn "broadcast_room\|act_to_room" mud/` and compare each site against its
   ROM C `act()` call to see if a `MOBtrigger` wrap is present. File a follow-up commit
   per unclosed site (per the INV tracker note "track as ad-hoc follow-up commits").
2. **Group/follower chain** (`src/act_move.c` follow-leader loop, `src/handler.c` group
   management): probe whether Python correctly propagates `ch->leader`/`ch->next_in_group`
   semantics on death, quit, and group leave. File as INV-041 if root cause spans modules.
3. **Mob-script trigger coverage** (`src/mob_prog.c` TRIG_* dispatch): probe remaining
   trigger types not yet wired in `mud/mobprog.py` (TRIG_RANDOM, TRIG_GREET, TRIG_ALL,
   TRIG_ENTRY vs current coverage).
