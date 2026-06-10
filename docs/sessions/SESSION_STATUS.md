# Session Status — 2026-06-10 — affect shadow LIFO + DEX/INT/WIS APPLY_ mapping (2.13.63)

## Current State

- **Active mode**: cross-file invariants pass + diff-harness coverage expansion
- **Last completed**:
  - **Three affect parity bugs fixed via C-oracle** — the `affect_expiry_lifecycle`
    diff-harness scenario was goldenated against the C binary, revealing and closing:
    1. Affect shadow list was FIFO (`append`) instead of LIFO (`insert(0)`) in both
       `sync_spell_effect_to_affected` and `Character.affect_to_char`.
    2. DEX/INT/WIS stat → APPLY_ location mapping used wrong `stat_int + 1` formula
       (Stat.DEX=3 → location=4=APPLY_WIS instead of APPLY_DEX=2). Affected haste+slow.
    3. Sanctuary SpellEffect missing `wear_off_message` (ROM const.c:1438 msg_off).
    Secondary fix: `handler.py:reset_char` stat-matching blocks used the same wrong formula.
  - Two new enforcement tests committed; `affect_expiry_lifecycle` scenario now passes (was skipping).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-10_AFFECT_SHADOW_LIFO_APPLY_MAPPING.md](SESSION_SUMMARY_2026-06-10_AFFECT_SHADOW_LIFO_APPLY_MAPPING.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.63 |
| Tests | 5504 passed, 5 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 26 enforced |
| Diff-harness scenarios | 25 scenarios, 40 passing (1 skipped — shop_sell_keeper_broke) |
| FINDINGS.md highest ID | FINDING-032 |

## Next Intended Task

Cross-file invariants remains the active pass. The diff-harness now has 25 scenarios / 40
C-oracle tests passing. Concrete candidates for the next session:

1. **Author charm/follower wear-off lifecycle scenario** — exercises `AFF_CHARM` expiry,
   follower detach, `pet` pointer cleanup (`INV-037`). Tests the `stop_follower` path
   through the C oracle.

2. **Author `drink`/`eat`/`food` consumption scenario** — condition decay, THIRST/FULL/HUNGER
   bitvectors. Another diff-harness surface with no current coverage; requires `__set_condition=`
   or `__thirst=` meta-command additions to pyreplay + diffmain.

3. **`shop_sell_keeper_broke` golden** — capture the C golden for the one remaining skipped
   scenario. The keeper-broke selling edge case is already authored; just needs the C binary
   run (`python3 -m tools.diff_harness.capture --scenario shop_sell_keeper_broke`).

4. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule.
