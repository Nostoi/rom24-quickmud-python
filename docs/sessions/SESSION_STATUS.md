# Session Status — 2026-06-12 — INV-045 walk-order class + LOOK holylight bypasses (2.14.14)

## Current State

- **Active audit**: Cross-file invariants pass (all per-file P0/P1/P2 rows at 100%)
- **Last completed**: Five gaps in one session.
  - **GL-040/GL-041/GL-042** — `obj_update`/`char_update`/`mobile_update` walked their registries
    oldest-first; ROM walks head-inserted `char_list`/`object_list` newest-first
    (`src/db.c:2256-2257`, `src/db.c:2482-2483`). With the shared Mitchell-Moore RNG stream, walk
    order decides which entity consumes which roll. All three now iterate
    `list(reversed(<registry>))` with mid-tick extraction skips. Filed as **INV-045
    (CHAR-LIST-WALK-ORDER)** in `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`, status ⚠️ PARTIAL.
  - **LOOK-005/LOOK-006** — PLR_HOLYLIGHT bypasses missing: `check_blind` lacked the
    `!IS_NPC && PLR_HOLYLIGHT → TRUE` short-circuit (src/act_info.c:544-545; `do_exits` also
    bypassed `check_blind` with a raw AFF_BLIND test), and `do_look`'s pitch-black gate dropped
    the `!IS_SET(act, PLR_HOLYLIGHT)` conjunct (src/act_info.c:1068-1069). Both were hidden
    behind stale-✅ audit rows (one pointing at the removed `mud/rom_api.py`).
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-12_INV045_WALK_ORDER_AND_LOOK_HOLYLIGHT.md](SESSION_SUMMARY_2026-06-12_INV045_WALK_ORDER_AND_LOOK_HOLYLIGHT.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.14 |
| Tests | 5626 passed, 4 skipped (2026-06-12) |
| ROM C files audited | All P0/P1/P2 at 100% |
| Active focus | Cross-file invariants (next free ID: INV-046; INV-045 ⚠️ PARTIAL) |

## Next Intended Task

**Finish INV-045 (CHAR-LIST-WALK-ORDER)** — two known offenders remain; close each as a single
gap-closer commit, then flip INV-045 to ✅ ENFORCED:

1. **`get_char_world` first-match** — `mud/world/char_find.py:103` returns the OLDEST matching
   character; ROM `src/handler.c:get_char_world` walks head-inserted `char_list` and returns the
   NEWEST. Observable via `summon`/`gate`/immortal `goto` with duplicate names. Probe: two
   same-named mobs, assert the newer is returned. File under the handler/char_find audit doc.
2. **Aggr walk** — `mud/ai/aggressive.py:57` iterates `character_registry` forward; ROM
   `aggr_update` walks `char_list` newest-first and the walk is RNG-bearing (attack rolls follow).
   Same reversed-walk + extraction-skip pattern as GL-040/041/042.

After INV-045 closes, fresh probe candidates: mob memory (ATTACK_BACK/hunt in `src/fight.c`),
`update_handler` pulse cadence vs Python tick scheduler, `weather_update` message fan-out order.

For each: read ROM C contract → read Python equivalent → write one failing test if divergence
found → close as single-gap commit or file as INV-NNN.
