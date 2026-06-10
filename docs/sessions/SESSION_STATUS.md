# Session Status — 2026-06-09 — Diff-harness C-oracle for TRIG_SURR, TRIG_FIGHT, TRIG_HPCNT (2.13.57)

## Current State

- **Active mode**: divergence Class 11 / dynamic differential widening
  (per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **TRIG_SURR C-oracle ground truth.** `mob_surr_trigger.json` confirms `mp_surr_trigger`
    fires when a PC surrenders to a mob with `TRIG_SURR` set. The mob does NOT retaliate
    after the trigger fires (`src/fight.c:3222-3241`). Python and C agree.
  - **TRIG_FIGHT C-oracle ground truth.** `mob_fight_trigger.json` confirms `mp_fight_trigger`
    fires each `violence_update` round after the NPC's `multi_hit` (INV-026 dispatch site,
    `src/fight.c:92-98`). Python and C agree.
  - **TRIG_HPCNT C-oracle ground truth.** `mob_hpcnt_trigger.json` confirms `mp_hitpnt_trigger`
    fires when mob HP falls below the percent threshold (`src/mob_prog.c:1354-1362`).
    Uses new `__mob_hp=` meta-command to stage mob below 50% without combat-RNG dependency.
    Python and C agree.
  - **`__mob_hp=<n>` meta-command** added to both C diffshim and Python pyreplay.
  - **`_room_occupant_line` look.py parity fix**: FIGHTING branch now correctly outputs
    `"YOU!"` / `"Name."` / `"thin air??"` / `"someone who left??"` mirroring
    `src/act_info.c:404-416`. All four branches covered by direct unit tests.
  - Version 2.13.57; 5,491 tests pass.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-09_DIFF_HARNESS_SURR_FIGHT_HPCNT_CORACLES.md](SESSION_SUMMARY_2026-06-09_DIFF_HARNESS_SURR_FIGHT_HPCNT_CORACLES.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.57 |
| Tests | 5,491 passed, 5 skipped (last full run) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 25 enforced |
| Diff-harness scenarios | 18 scenarios (added SURR + FIGHT + HPCNT this session) |
| Class 11 dynamic widening | EXIT + EXALL + GREET + GRALL + SPEECH + ACT + BRIBE + GIVE + SURR + FIGHT + HPCNT all have C-oracle ground truth |

## Next Intended Task

Class 11 remaining work (in priority order):

1. **TRIG_KILL and TRIG_DEATH C-oracle scenarios** — the `__mob_hp=` infrastructure added this
   session makes KILL scenarios tractable: set mob HP to 1, then one `__tick` should produce a
   killing blow (RNG-dependent — may need a `__instant_kill` or `__mob_hp=0` meta-command for
   deterministic death). Author scenarios and capture C-oracle goldens.
2. **RNG-locked paths** (`TRIG_RANDOM`, `TRIG_DELAY`) — requires seed alignment grounded probe
   before a meaningful C-oracle scenario can be authored. Defer until there is a reproducible
   seed sequence for those paths.
3. **Next divergence class** — consult `docs/parity/DIVERGENCE_CLASS_ROSTER.md` for the next
   unverified surface outside Class 11. Candidates include async message delivery ordering,
   affect-tick edge contracts, and position-transition invariants.
4. **Latent parity gap: wizard shop status** — Python's `_has_shop` returns False for mob 3000
   (wizard) because the midgaard JSON area file has no `shops` section. C's midgaard.are defines
   wizard as a shop keeper. Should be reviewed against shop scenario coverage before claiming
   shop parity is clean.
