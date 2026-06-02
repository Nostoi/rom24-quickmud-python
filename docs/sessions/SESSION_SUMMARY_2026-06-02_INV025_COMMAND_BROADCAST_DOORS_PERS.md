# Session Summary — 2026-06-02 — INV-025 command-layer `broadcast_room` PERS sweep (4th batch) + doors.py rework + `act_format._pers` fidelity

## Scope

Picked up the SESSION_STATUS "4th INV-025 PERS batch" task — the baked-f-string /
`act_format(recipient=None)` + `broadcast_room` TO_ROOM group the prior three
batches (object / equipment / give) walked past. ROM `act("$n …", TO_ROOM)`
renders `$n` through `PERS(ch, looker)` per recipient (`src/comm.c:act_new`), so
an invisible actor masks to "Someone" for an unaided witness (INV-027). These
command-layer sites baked the actor name into one string for all recipients,
leaking it. Converted every site to the shared `act_to_room` helper
(per-recipient PERS + TRIG_ACT). Mid-sweep the conversions surfaced two latent
`act_format._pers` divergences from ROM `PERS` and a residual shop-command group;
both were folded in rather than deferred (avoiding the over-claim the prior
session had to retract in `a4936805`).

## Outcomes

### Command-layer broadcast PERS sweep — ✅ CLOSED (commit `e020127d`, 2.12.55)

- **Python / ROM C** (each string re-verified against `src/`):
  - `position.py` rest/sit/sleep/stand (`_broadcast` helper)
  - `session.py` `do_quit` — `act_comm.c:1482`
  - `inspection.py` `do_scan` look-around (`scan.c:60`) + directional peer
    (`scan.c:90`, `$T`)
  - `healer.py` utter — `healer.c:183` (`$T`)
  - `imm_load.py` `do_mload` (`act_wiz.c:2512`, `$N`), `do_oload` (`:2566`, `$p`),
    `do_purge` room (`:2605`) + `$N` TO_NOTVICT disintegrate/purge
    (`:2633/2645`) — removed the bespoke `_notvict_broadcast` helper
  - `imm_search.py` `do_clone` object (`:2405`, `$p`) + mobile (`:2449`, `$N`)
  - `shop.py` `do_buy` pet (`act_obj.c:2636`, `$N`) / item (`:2742`/`:2734`,
    `$p[N]`) and `do_sell` (`:2923`, `$p`)
- **`do_restore` TO_VICT** (`act_wiz.c:2809/2842/2863`): `"$n has restored you."`
  now via `act_format(recipient=victim)` — an invisible restorer masks per the
  victim's sight; self-restore keeps the name (ROM `PERS(ch,ch)` short-circuits
  `can_see` TRUE → name, and ROM `$n` has no "You" self-case).
- **Shop TRIG_ACT**: the three shop sites were bare `.broadcast` with **no**
  TRIG_ACT dispatch — the `act_to_room` conversion adds it (INV-025's primary
  contract). PERS masking is unreachable for shops (keeper refuses an invisible
  customer, `act_obj.c:2395`), so the genuinely-new behavior is the trigger.
- **`act_format._pers` PERS fidelity**: the sweep exposed two divergences from
  ROM `PERS` (`src/merc.h:2145`) — `_pers` returned `target.name` for NPCs (ROM
  uses `short_descr`) and had a non-ROM `"You"` self-case (ROM `$n`/`$N` are
  always `PERS`, never "You"). Aligned with `mud/world/vision.py:pers`
  (NPC→short_descr, PC→name, no "You"). Production mobs were unaffected
  (`MobInstance.name` already == short_descr) but the fix makes act() rendering
  correct when they differ and stops a created/cloned mob receiving
  "… created You!".
- **Tests**: `tests/integration/test_inv025_command_broadcast_pers_sweep.py` (14:
  sleep/quit/scan/peer/mload/oload/purge/clone + restore room mask/name/self);
  shop buy TRIG_ACT dispatch added to `test_shop_room_broadcasts.py`.

### doors.py chokepoint PERS rework — ✅ CLOSED (commit `5299c664`, 2.12.55)

- **Python**: `mud/commands/doors.py` `_broadcast_act_to_room` helper + 15 callers
- **ROM C**: open/close/lock/unlock/pick — `act_move.c:384/412/436/492/515/534/
  622/655/690/757/790/825/907/945/981`
- **Gap**: the helper took a pre-baked `f"{actor_name} …"` string, delivering the
  actor's identity un-masked to every witness (it did already dispatch TRIG_ACT).
- **Fix**: reworked the helper to take a ROM `act()` format string (`$n opens $p.`
  / `$n opens the $d.`) and route through `act_to_room`; converted all callers.
  `$p` = portal/container object, `$d` = door keyword, `[N]`-style quantity
  unchanged. The reverse-side "The $d opens/closes." line has no `$n` → left as-is.
- **Tests**: `tests/integration/test_inv025_door_commands_pers_sweep.py` (7:
  open/close/lock container `$p` + open/pick door `$d`, invisible→"Someone",
  visible→name).

## Files Modified

- `mud/utils/act.py` — `_pers` ROM-PERS fidelity (NPC→short_descr, no "You").
- `mud/commands/position.py`, `session.py`, `inspection.py`, `healer.py`,
  `imm_load.py`, `imm_search.py`, `shop.py` — command-layer conversions; dropped
  `_notvict_broadcast`; pruned orphaned `broadcast_room`/`mp_act_trigger_room`
  imports.
- `mud/commands/doors.py` — `_broadcast_act_to_room` helper redesign + 15 callers.
- `tests/integration/test_inv025_command_broadcast_pers_sweep.py` — new (14).
- `tests/integration/test_inv025_door_commands_pers_sweep.py` — new (7).
- `tests/integration/test_shop_room_broadcasts.py` — +1 buy-TRIG_ACT test;
  removed unused import.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-025 trail: command-layer
  group flipped OPEN→CLOSED; recorded `_pers` fidelity + shop TRIG_ACT + doors.
- `CHANGELOG.md` — 2 `Fixed` entries.
- `pyproject.toml` — 2.12.54 → 2.12.55.
- `README.md` — version badge + count, tests 5281→5303.

## Test Status

- New/changed tests: 22 across the three files, all green.
- Area suites green throughout (doors ×29 incl. existing trigger tests; shop ×3;
  command-broadcast ×14; restore/imm_load ×20).
- **Full suite: 5303 passed, 4 skipped** (`pytest -p no:xdist -o addopts="" -q`,
  ~10m17s) — no regressions from the shared `_pers` change. `ruff check` clean on
  all touched files. `gitnexus_detect_changes` low-risk / 0 affected processes.

## Next Steps

The INV-025 command-layer `broadcast_room` / `act_format(recipient=None)` PERS
class is now **exhausted** across `mud/commands/` (residual grep for
`broadcast_room(.*f"` / `.broadcast(f"` returns only the no-`$n` door reverse
line). Next cross-file-invariants candidates (per AGENTS.md): mob script trigger
ordering (TRIG_ENTRY/GREET/GIVE/BRIBE), position transitions, group/follower
chains. The `act_format._pers` "You" removal is a shared-helper change — if any
future TO_VICT/TO_CHAR site relied on `$n`→"You" it would now render the name
(ROM-correct); none surfaced in the full suite.

> **Push note:** everything through 2.12.48 is on `master`; **2.12.49–51**
> (FIGHT-041/042 + NUKEPET-001), **2.12.52–54** (object/equipment/give), and
> **2.12.55** (this session — `e020127d`, `5299c664`) are committed locally but
> **NOT yet pushed**. README/CHANGELOG/version all reflect 2.12.55.
> **Index:** GitNexus reindexed after the doors commit.
