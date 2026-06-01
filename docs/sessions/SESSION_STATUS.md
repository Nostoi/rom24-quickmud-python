# Session Status — 2026-06-01 — MAGIC-012/013 manual-room-loop PERS masking (2.12.44)

## Current State

- **Active mode**: cross-file invariants — the **INV-025 manual-room-loop PERS
  sweep** is the active pass (the 2.12.30 sweep converted `_act_room` call sites
  but missed handlers baking `_character_name()` into `room.broadcast(...)` /
  hand-rolled room loops).
- **Earlier today (2.12.40 → 2.12.42, pushed green):** CAST-009 + TRAIN-005
  closed; full suite green (5242 passed); pushed to origin (also carried the
  prior session's unpushed 2.12.40 commits). See
  [SESSION_SUMMARY_2026-06-01_CAST009_TRAIN005_QUEUE_DRAIN.md](SESSION_SUMMARY_2026-06-01_CAST009_TRAIN005_QUEUE_DRAIN.md).
- **This pass (2.12.42 → 2.12.44):**
  - **MAGIC-012** (`14cf90c4`, 2.12.43) — `frenzy` success room line
    `$n`/`$s` per-recipient PERS masking (ROM `magic.c:2961`).
  - **MAGIC-013** (`ded5e147`, 2.12.44) — `cure_disease` success room line
    PERS masking **+ wrong-channel** fix (ROM `magic.c:1658`).
  - Probed group/follower + affect-tick — both **faithful** (no gap).
  - 4 new integration tests; INV-025 trail extended with the remaining
    ~12-site work-list.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-01_MAGIC012_013_MANUAL_ROOM_LOOP_PERS.md](SESSION_SUMMARY_2026-06-01_MAGIC012_013_MANUAL_ROOM_LOOP_PERS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.44 |
| Tests | full suite green at 2.12.42 (5242 passed); 2.12.44 run pending push (4 new tests → ~5246) |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 25 enforced |
| Open correctness gaps | INV-025 manual-room-loop PERS sweep: ~12 sites OPEN (work-list in INV-025 trail); dirt-kicking "their" line needs ROM verification |

## Next Intended Task

1. **Continue the INV-025 manual-room-loop PERS sweep** — ~12 remaining sites
   (work-list in the INV-025 "Touched by" trail in
   `CROSS_FILE_INVARIANTS_TRACKER.md`): rose (handlers.py:2624), earthquake
   (3550), sleep (7520), giant_strength (4966), haste/slow
   (5038/5075/7567/7604), `$n turns translucent` (6298), stone skin (7801),
   trip→`$s` (7981), weaken (8163). One failing-first MAGIC-NNN commit each;
   **verify each handler's exact `src/magic.c` `act()` format string** before
   converting (the `$s`/`$e`/`$m`/`$p` token and TO_ROOM vs TO_NOTVICT vary).
2. Verify the dirt-kicking already-affected caster line
   (`handlers.py:~3200`) — no ROM equivalent found; confirm Python-invented.

> **Push note:** MAGIC-012/013 + this handoff are local on `master` pending the
> full-suite confirmation at 2.12.44 (running `-n0`; the machine intermittently
> spikes to load ~180 from unrelated workloads, which hangs `-n auto` at worker
> startup — use `-n0`). README test-count/version refresh to 2.12.44 belongs in
> the push commit once the count is confirmed.

> **Stale index:** GitNexus index reindex pending — run on a quiet machine.
