# Session Summary — 2026-07-16 — C-oracle scenario batch (DB-005/FIGHT-098/FIGHT-100) + FIGHT-103

## Scope

Autonomous loop iteration 7/10. Authored the three deferred C-oracle
differential scenarios locking this loop's parity fixes against the live
instrumented C engine (`src/diffshim`), and closed **FIGHT-103** — a real
fleer-output divergence the capture surfaced.

## Outcomes

### C-oracle scenarios — ✅ all three convergent (differential 102/102, 69 scenarios)

1. **`db005_reset_order_mob_census`** — valley.are mob 7803/7804 census.
   C golden: `['7866', '7860', '7848']` — 3 sentries, none in 7853, exactly
   the per-room ascending-vnum order DB-005 implemented. Required the
   `__mob_census` handler on the Python replay side (C side existed).
2. **`fight098_area_attack_domain`** — OFF_AREA_ATTACK sweep with a
   same-room fighter NEWER than the room head (Ally, staged fighting the mob
   then Tester re-enters to become head). **Mutation-tested**: reverting the
   sweep to `room.people` makes the replay fail; the golden has real recall.
   Required two new staging directives, mirrored C+Python: `__mob_fight` /
   `__char_fight` (one-way `set_fighting`). Shim rebuilt (ROM `src/*.c`
   untouched).
3. **`fight100_pc_wimpy_autoflee`** — PC `hit <= wimpy` auto-flee end-to-end
   (`wimpy 50` typed command + `__hp` staging + `__aggr_update`): scratch →
   BLEEDING → room look → "You flee from combat!" → exp loss, byte-identical.

### `FIGHT-103` — ✅ FIXED (surfaced by the fight100 capture)

- **(a)** `do_flee` composed flee/exp lines BEFORE the destination look; ROM
  renders the look first (`move_char` at `src/fight.c:3002` precedes
  `:3010-3019`). Reordered.
- **(b)** the FIGHT-100 auto-flee epilogue discarded `do_flee`'s return; ROM
  delivers via `send_to_char` to the victim's descriptor. Now routed through
  `_push_message`. (`do_recall`'s return stays discarded — that branch only
  fires for `desc==NULL` victims where ROM's send is a no-op.)
- **Lock**: the scenario golden (red before, green after).
- **Commits**: `8f782125` (FIGHT-103 + fight100 scenario), `c04f1f29`
  (DB-005/FIGHT-098 scenarios + directives). v2.14.329.

## Files Modified

- `mud/commands/combat.py` — do_flee look-before-flee-lines order
- `mud/combat/engine.py` — epilogue delivers flee output
- `tools/diff_harness/pyreplay.py` — `__mob_census`, `__mob_fight`,
  `__char_fight` handlers
- `src/diff_shim/diffmain.c` — `__mob_fight`, `__char_fight` (shim-owned,
  additive; rebuilt)
- 3 scenarios + 3 goldens; `docs/parity/FIGHT_C_AUDIT.md` (FIGHT-103 row);
  `CHANGELOG.md`; `pyproject.toml` → 2.14.329

## Test Status

- Unit **2801 passed, 1 skipped**; integration **3438 passed, 3 skipped**.
- Differential harness: **102/102 across 69 scenarios** convergent.

## Next Steps

Backlog: HANDLER-009 (test-only), carry-overs (FIGHT-094 check_killer
placement, DESC-001, OLC spell-name lookup, IS_BUILDER, stray db files).
FIGHT-094 is the most substantive remaining combat item — a probe-then-close
candidate.
