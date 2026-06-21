# Session Status — 2026-06-21 — Reset mob-level fix (DB-004, game-wide)

## Current State

- **Active focus**: Returning to differential-harness widening (the
  enumeration-independent parity oracle) after a user-reported live bug
  pulled the session into a game-wide reset fix.
- **Last completed** (this session): closed **`DB-004`** — the area-reset
  M-case wrongly decremented **every reset-spawned mob's level by 2**. ROM
  `src/db.c:1750` `level = URANGE(0, pMob->level - 2, LEVEL_HERO-1)` is an
  **object**-fuzz local for the following O/G/E resets, never written back
  to the mob; `create_mobile` (`src/db.c:2071`) keeps the prototype level.
  Python had assigned the fuzzed value to `mob.level`, so a level-1 school
  wimpy monster (vnum 3703, room 3715) reset to level 0 → its corpse paid
  `max(1, 0*3)` = 1 silver on sacrifice/AUTOSAC instead of ROM's 3 (and
  THAC0/damage/saves/XP were skewed game-wide). Fix keeps the mob at its
  prototype level and routes `mob_level-2` through `last_mob_level` /
  `_compute_object_level` so O/G/E object levels stay ROM-correct.
  Corrected the false test that encoded the bug
  (`test_m_reset_level_calculation` → `test_m_reset_preserves_mob_prototype_level`).
  Also added an AUTOSAC reward-scaling guard
  (`test_auto_sacrifice_reward_scaling.py`, commit `8de18809`).
- **Investigated, ROM-correct (no change)**: Mud School fast respawn
  (`src/db.c:1627` `age = 15 - 2`, ~3-min school repop); reconnect resumes
  mid-combat (ROM `nanny` link-dead reattach).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-21_RESET_MOB_LEVEL_DB004.md](SESSION_SUMMARY_2026-06-21_RESET_MOB_LEVEL_DB004.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.205 |
| Tests | 6017 passing (4 skipped) |
| Differential scenarios | 48 / 48 converge (`KNOWN_DIVERGENCES` empty) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Differential harness widening (DB-004 closed this session) |

## Next Intended Task

**Resume widening the differential harness** (the pre-DB-004 focus):

- **`practice` differential** — needs a partial-skill shim meta
  (`__learn_pct=<skill>=<pct>`, both C shim + pyreplay); `make_test_char`
  skips `group_add` so the default char knows no skills, and the existing
  `__learn` meta sets 100% (adept) which short-circuits practice. Then
  `practice <skill>` exercises the INT-learn-rate increment + 3-column
  known-skill display.
- **FIGHT-079** — PC corpse half-coin gate (`src/fight.c:1483-1495`): ROM
  drops half the coins (non-clan only); Python drops full + zeroes. Own
  gap-closer commit; needs a PC-victim corpse-money test.
- **auto-loot / auto-gold death scenarios** — needs a PLR_AUTOLOOT/AUTOGOLD
  meta; `death_corpse_loot_sacrifice` covers manual corpse→get→sacrifice only.

Method (reinforced): bracket spawns with `__seed`; set mob wealth explicitly
post-spawn (`__mob_gold`/`__mob_silver`) — boot-rolled wealth is NOT bit-matched
C⇄Python; capture per-scenario (`--scenario`), never `--all`; a divergence is a
FINDING (→ `/rom-gap-closer` or new INV-NNN; **never** overwrite the golden).

**Redeploy note**: DB-004 corrects mob level at every reset, so a backend
restart picks it up — no JSON regeneration needed. The live
`python -m mud websocketserver` does **not** hot-reload — restart after any
engine change. When chasing a live-only bug, reproduce via the reset system
(`reset_area`/`apply_resets`), not `spawn_mob()` directly — the two paths
diverged here and only the reset path carried DB-004.
