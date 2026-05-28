# Session Status — 2026-05-28 — DB2-007 mob-dice fix shipped; combat differential harness v1 WIP

## Current State

- **Active mode**: differential-harness-driven parity verification. The combat slice
  of the harness (`tools/diff_harness/`, scenario `combat_melee_rounds`) is being built
  and is **already surfacing real Python parity bugs** the synthetic-mob test suite never
  caught.
- **Headline this session — DB2-007 (shipped to `master`, 2.11.2):** every JSON-loaded mob
  had wrong HP/mana/damage game-wide. `mob_loader.load_mobiles` read a phantom scalar `ac`
  token at the new-format stat line's index [2] (ROM has AC on the *next* line), shifting
  every dice field by one and dropping the real HP dice (Hassan 100 HP vs ROM 1000; drunk
  100 vs `2d6+22`). Fixed; all 52 area JSONs regenerated; full suite 4925/0.
- **Combat v1 is WIP, gated on FINDING-007** (xfail): mob spawn RNG draw-order diverges —
  ROM `create_mobile` draws gold before HP, Python `from_prototype` draws gold last, so
  the drunk spawns at HP 31 (C) vs 33 (Python) from the same seed.

## Branch state (READ THIS — work spans two branches)

| Branch | SHA | Contents |
|--------|-----|----------|
| `origin/master` / local `master` | `1857b5f8` (v2.11.2) | DB2-007 mob-dice fix + regenerated area JSONs **shipped**. Publish-ready. |
| `diff-harness` (active, local only) | `fc7880e8` | Everything on master **plus** the differential harness (v1 smoke + combat WIP), FINDINGS, design/plan. Combat scenario xfails on FINDING-007. **Resume here.** |

`diff-harness` is strictly ahead of `master` and is the active working branch for the
multi-session harness effort. It has not merged to master (combat v1 incomplete).

## Pointer to latest summary

[SESSION_SUMMARY_2026-05-28_DB2_007_MOB_DICE_AND_COMBAT_HARNESS_V1_WIP.md](SESSION_SUMMARY_2026-05-28_DB2_007_MOB_DICE_AND_COMBAT_HARNESS_V1_WIP.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version (master) | 2.11.2 |
| Full suite | 4925 passed / 4 skipped / 0 failed (post-DB2-007) |
| Differential harness | `movement_get_drop` PASS; `combat_melee_rounds` XFAIL (FINDING-007) |
| Open findings | FINDING-007 (mob spawn RNG draw-order) — gates combat v1 |

## Next Intended Task

**Fix FINDING-007 on `master`** (see `tools/diff_harness/FINDINGS.md` and the SESSION_SUMMARY):
reorder `mud/spawning/templates.py:from_prototype`'s RNG draws to match ROM
`create_mobile` (`src/db.c:2047-2091`) — **gold/wealth first, then HP dice, then mana
dice, then the `dam_type == 0` random damtype roll last**. Follow the gap-closer flow:
failing test first (a seeded `spawn_mob` whose rolled HP matches the ROM draw order),
fix, triage seeded-test fallout, land on master, merge into `diff-harness`, re-run the
differential — the `combat_melee_rounds` `KNOWN_DIVERGENCES` xfail auto-clears when the
diff goes clean. Then finish combat v1 (plan Tasks 4-6): triage any further combat-round /
message-wording divergences as master gap-closers, then clear the gate and bump version.

Plan: `docs/superpowers/plans/2026-05-28-combat-rng-differential-scenario-v1.md`.

> Note: GitNexus index was stale at session end (combat WIP + DB2-007 committed). Reindex
> (`npx gitnexus analyze --skip-agents-md`) before relying on `gitnexus_impact` next session.
