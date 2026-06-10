# Session Status — 2026-06-09 — Diff-harness C-oracle for TRIG_ACT, TRIG_BRIBE, TRIG_GIVE (2.13.55)

## Current State

- **Active mode**: divergence Class 11 / dynamic differential widening
  (per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **TRIG_ACT C-oracle ground truth.** `mob_act_trigger.json` confirms `mp_act_trigger`
    fires when the formatted `act()` buffer matches `trig_phrase` via substring search
    (`src/comm.c:2385`, `src/mob_prog.c:1183-1197`). Python and C agree.
  - **TRIG_BRIBE C-oracle ground truth.** `mob_bribe_trigger.json` confirms `mp_bribe_trigger`
    fires when silver given meets threshold (`amount >= atoi(trig_phrase)`, `src/act_obj.c:735`).
    Python and C agree.
  - **TRIG_GIVE C-oracle ground truth.** `mob_give_trigger.json` confirms `mp_give_trigger`
    fires on object give by vnum match (`src/mob_prog.c:1207-1242`). Python and C agree.
    Note: wizard (3000) was replaced by sailor (3007) as recipient — wizard is a shop keeper
    in the C area file and rejects item gives before mp_give_trigger can fire.
  - All three new scenarios pass Python/C parity immediately (no engine code changes needed).
  - Version 2.13.55; 5,484 tests pass.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-09_DIFF_HARNESS_ACT_BRIBE_GIVE_CORACLES.md](SESSION_SUMMARY_2026-06-09_DIFF_HARNESS_ACT_BRIBE_GIVE_CORACLES.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.55 |
| Tests | 5,484 passed, 5 skipped (last full run) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 25 enforced |
| Diff-harness scenarios | 15 static scenarios; 21+ golden tests; all findings resolved |
| Class 11 dynamic widening | EXIT + EXALL + GREET + GRALL + SPEECH + ACT + BRIBE + GIVE deterministic paths all have C-oracle ground truth |

## Next Intended Task

Class 11 remaining work (in priority order):

1. **RNG-locked paths** (`TRIG_RANDOM`, `TRIG_DELAY`) — requires seed alignment grounded
   probe before a meaningful C-oracle scenario can be authored. Defer until there is a
   reproducible seed sequence for those paths.
2. **Combat-path C-oracle scenarios** (`TRIG_FIGHT`, `TRIG_HPCNT`, `TRIG_KILL`, `TRIG_DEATH`,
   `TRIG_SURR`) — these have OLC MEdit runtime probes but no diff-harness C-oracle scenarios.
   Combat triggers require controlled damage mechanics (fixed weapon + armor + level) to
   produce deterministic C output. Authoring deterministic variants (no-RNG-gate) is the
   next concrete step if Class 11 C-oracle completeness is the goal.
3. **Next divergence class** — consult `docs/parity/DIVERGENCE_CLASS_ROSTER.md` for the next
   unverified surface outside Class 11. Candidates include async message delivery ordering,
   affect-tick edge contracts, and position-transition invariants.
4. **Latent parity gap: wizard shop status** — Python's `_has_shop` returns False for mob 3000
   (wizard) because the midgaard JSON area file has no `shops` section. C's midgaard.are defines
   wizard as a shop keeper. The shop scenarios (`shop_buy_weapon`, `shop_sell_weapon`) pass,
   so this likely affects only `do_give` item-give rejection. Should be reviewed against shop
   scenario coverage before claiming shop parity is clean.
