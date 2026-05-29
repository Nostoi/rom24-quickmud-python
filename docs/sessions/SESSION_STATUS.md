# Session Status — 2026-05-29 — FINDING-009 combat-tick round fully resolved (FIGHT-021..026)

## Current State

- **Active mode**: differential-harness-driven combat parity verification. The
  `combat_melee_rounds` scenario's step-5 (`__tick` / `violence_update`)
  divergence was root-caused into four facets; **all four are now closed on
  `master`** and the differential's step 5 converges on both engines.
- **Last completed** (this session):
  - **`FIGHT-021`** ✅ (2.11.9, `79c4d7f7`) — `multi_hit` draws 2nd/3rd-attack `number_percent()` unconditionally (facet 1a).
  - **`FIGHT-022`** ✅ (2.11.10, `4d9fb5c3`) — faithful NPC `mob_hit` adds ROM's `number_range(0,2)`/`(0,8)` draws + off-skill dispatch (facet 1b).
  - **`FIGHT-026`** ✅ (2.11.11, `850662b5`) — NPC `do_dirt`/`do_trip`/`do_disarm` no longer crash on `mob_hit` dispatch (latent FIGHT-022 fallout exposed by FIGHT-024).
  - **`FIGHT-024`** ✅ (2.11.12, `863f8734`) — `violence_tick` walks `character_registry` reversed to match ROM head-first `char_list` (facet 3).
  - **`FIGHT-023`** ✅ (2.11.13, `027eee0f`) — mob `dam_type` is the ROM attack_table index, not a DamageType class; drunk renders "beating" + correct DAM_BASH class (facet 2).
  - **`FIGHT-025`** ✅ (2.11.14, `b8878785`) — combat act() output capitalized like ROM `act_new` (facet 4). **Closes FINDING-009.**
  - **FINDING-009** ✅ RESOLVED — differential step 5 converges; first divergence advanced to **step 6**, filed as **FINDING-010** (round-2 damage severity) on the diff-harness branch (`9bc1a489`).
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-29_FINDING_009_COMBAT_TICK_CLOSED.md](SESSION_SUMMARY_2026-05-29_FINDING_009_COMBAT_TICK_CLOSED.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.14 |
| Tests | 4942 passed, 4 skipped (full suite, parallel) |
| ROM C files audited | 43 / 43 (per-file pass complete; differential + cross-file invariants active) |
| Active focus | `fight.c` combat-tick (FINDING-009 closed; FINDING-010 open) |

## Next Intended Task

Pick up **FINDING-010** (combat-tick round-2 damage amount diverges — C
"scratches" ≤5% vs py "hits" ≤15%). Root cause unknown; **rule out a regression
from this session's FIGHT-023/021/022 first** (step 6 was never compared before
the FINDING-009 fixes). Discriminating probe: dump the per-round RNG draw
*sequence* + damage components (dice value, damroll, STR app, RIV, and the
drunk's wait-state between rounds) for both engines at step 6. Draw counts
diverge by round 2 → facet-1/wait-state residual; draws match but damage differs
→ damage-formula bug. File as a FIGHT-NNN gap once isolated.

Outstanding filed follow-ups (in `docs/parity/FIGHT_C_AUDIT.md`): `SHOP-PET-001`
(pet `dam_type` bypasses `from_prototype` resolution), `ACT-CAP-001` (non-combat
act() capitalization at `broadcast_room`/`act_format`), and NPC `do_X`
per-command RNG-draw fidelity for flagged mobs.
