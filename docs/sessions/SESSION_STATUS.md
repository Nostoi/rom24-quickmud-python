# Session Status — 2026-06-22 — Practice differential harness widening

## Current State

- **Active focus**: Differential-harness widening (the enumeration-independent
  parity oracle).
- **Last completed** (this session): added the **`practice_skill_listing`**
  C-oracle scenario and the `__learn_pct=NAME=N` harness meta-command on both
  sides. The scenario `__mload`s the Midgaard mage guildmaster (`3020`,
  `ACT_PRACTICE`), seeds `armor` at 1%, runs `practice armor`, then runs bare
  `practice`; ROM and Python converge with `armor` at 35% and 4 practice
  sessions left. This covers the `do_practice` INT-learn-rate increment plus
  known-skill listing path without using `__learn`'s 100% adept shortcut.
- **Investigated, ROM-correct (no change)**: Mud School wimpy aggressive mob
  non-aggression against a standing level-2 PC. ROM `src/update.c:1106` skips
  `ACT_WIMPY` aggressive mobs when the watched PC is awake; Python mirrors it
  in `mud/ai/aggressive.py`.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-22_PRACTICE_DIFF_HARNESS.md](SESSION_SUMMARY_2026-06-22_PRACTICE_DIFF_HARNESS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.206 |
| Tests | Focused diff-harness suite: 77 passing |
| Differential scenarios | 49 / 49 converge (`KNOWN_DIVERGENCES` empty) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Differential harness widening (`practice_skill_listing` added this session) |

## Next Intended Task

**Continue widening the death/autoloot differential surface**:

- **FIGHT-079** — PC corpse half-coin gate (`src/fight.c:1483-1495`): ROM
  drops half the coins (non-clan only); Python drops full + zeroes. Own
  gap-closer commit; needs a PC-victim corpse-money test.
- **auto-loot / auto-gold death scenarios** — needs a PLR_AUTOLOOT/AUTOGOLD
  meta; `death_corpse_loot_sacrifice` covers manual corpse→get→sacrifice only.

Method (reinforced): bracket spawns with `__seed`; set mob wealth explicitly
post-spawn (`__mob_gold`/`__mob_silver`) — boot-rolled wealth is NOT bit-matched
C⇄Python; capture per-scenario (`--scenario`), never `--all`; a divergence is a
FINDING (→ `/rom-gap-closer` or new INV-NNN; **never** overwrite the golden).

The live `python -m mud websocketserver` does **not** hot-reload — restart after
any engine change. When chasing a live-only bug, reproduce reset-population bugs
via the reset system (`reset_area`/`apply_resets`), not `spawn_mob()` directly.
