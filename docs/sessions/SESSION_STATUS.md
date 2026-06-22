# Session Status — 2026-06-22 — Death auto-action differential harness

## Current State

- **Active focus**: Differential-harness widening (the enumeration-independent
  ROM⇄Python parity oracle).
- **Last completed**:
  - Closed **FIGHT-079**: PC corpse money now follows ROM `make_corpse`
    (`src/fight.c:1483-1495`). Non-clan PCs keep all coins and get an owned
    corpse; clan PCs get an unowned corpse and drop half their coins on the ROM
    `> 1` gate.
  - Added `__plr_autoloot=0|1` and `__plr_autogold=0|1` meta commands to both
    diff harness drivers.
  - Added **`death_auto_gold`** and **`death_auto_loot`** C-oracle scenarios.
    They surfaced **FIGHT-080 / FINDING-040**, now fixed: death auto-gold and
    auto-loot route through ROM-style `do_get` output instead of the old
    fabricated `"You quickly gather..."` summary.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-22_DEATH_AUTO_ACTION_DIFF_HARNESS.md](SESSION_SUMMARY_2026-06-22_DEATH_AUTO_ACTION_DIFF_HARNESS.md)
- **Matching handoff**:
  [HANDOFF_2026-06-22_DEATH_AUTO_ACTION_DIFF_HARNESS.md](HANDOFF_2026-06-22_DEATH_AUTO_ACTION_DIFF_HARNESS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.208 |
| Tests | Focused parity suite: 154 passed; `ruff check .` clean |
| Differential scenarios | 51 / 51 converge (`KNOWN_DIVERGENCES` empty) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Differential harness widening (`death_auto_gold`, `death_auto_loot`) |

## Next Intended Task

Continue widening the death lifecycle differential surface. Good next probes:

- `PLR_AUTOSAC` after NPC death, especially the ROM branch that refuses autosac
  when `AUTOLOOT` left treasure in the corpse.
- `PLR_AUTOSPLIT` after auto-gold / sacrifice rewards, if a deterministic grouped
  PC setup is added to the harness.
- Driver-PC death remains integration-test-only for now; the current harness
  does not inspect the driver's own corpse after killing the PC.

Method reminder: bracket spawns with `__seed`; set mob wealth explicitly
post-spawn (`__mob_gold`/`__mob_silver`) because boot-rolled wealth is not
bit-matched C⇄Python; capture per-scenario (`python3 -m tools.diff_harness.capture
--scenario <name>`), never overwrite a real divergence golden.
