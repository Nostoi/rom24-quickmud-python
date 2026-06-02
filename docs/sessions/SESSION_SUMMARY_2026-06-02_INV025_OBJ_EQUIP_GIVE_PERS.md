# Session Summary — 2026-06-02 — INV-025 object/equipment/give PERS sweep (act_format class closed; broadcast_room group still open)

## Scope

Picked up the SESSION_STATUS "finish the INV-025 baked-name re-probe" task
(`mud/combat/`, `mud/world/`, `mud/commands/communication.py`). Probing showed
those three were **already swept** — `mud/combat/engine.py` routes every room
line through `_broadcast_pos_change`/`_broadcast_damage_messages`/`act_to_room`
(PERS + TRIG_ACT), `mud/world/` has no raw `broadcast_room`/`.broadcast` sites,
and `communication.py` `do_say`/`do_tell`/`do_shout` use manual per-recipient
`pers()` loops + TRIG_ACT.

The **real** remaining divergence was a larger, uniform class the prior passes
hadn't reached: object commands rendering their ROM `act("$n …", TO_ROOM)` lines
via `act_format(..., recipient=None)` (which returns the actor's raw name — no
viewer) piped to `protocol.broadcast_room` (one baked string for all recipients).
TRIG_ACT was already dispatched at most sites via a paired `mp_act_trigger_room`,
so the gap was per-recipient **PERS masking** — an invisible actor leaked its name
to unaided witnesses (INV-027). Closed in three batches (advisor-reviewed scope;
`give` split out for its inverse TRIG_ACT contract). Each batch reconciled a
previously-✅ audit row per the AGENTS.md "re-verify ✅" rule.

## Outcomes

### Batch 1 — object commands — ✅ CLOSED (commit `733a741d`, 2.12.52)

- **Python**: `obj_manipulation.py`, `inventory.py`, `consumption.py`,
  `liquids.py`, `magic_items.py`
- **ROM C**: `src/act_obj.c` put `:440/445/479/484`, get `:151/158`, drop
  `:586/608/632`, sacrifice `:1782/1856`, quaff `:1897`, eat `:1317/1342`, drink
  `:1238/1263`, fill `:1025`, pour `:1142/1155`, pour-out `:1075`; remove
  `handler.c:remove_obj`
- **Gap**: `act_format(recipient=None)+broadcast_room` baked the actor name (no
  per-recipient PERS); leaked an invisible actor to witnesses.
- **Fix**: collapsed each `broadcast_room` + `mp_act_trigger_room` pair into one
  `act_to_room(room, "$n …", actor, …, exclude=actor)` (per-recipient PERS +
  TRIG_ACT preserved). `magic_items._broadcast` helper rewritten to delegate to
  `act_to_room` (handles the zap TO_NOTVICT `exclude=[ch,victim]` → `exclude=victim`).
- **Reconciled**: RECITE-002 / BRANDISH-004 / ZAP-004 audit rows.
- **Tests**: `tests/integration/test_inv025_obj_command_pers_sweep.py` (7) — get/
  drop/put/quaff/eat/sacrifice invisible→"Someone", sighted→name. Green.

### Batch 2 — equipment commands — ✅ CLOSED (commit `379baa0b`, 2.12.53)

- **Python**: `mud/commands/equipment.py`
- **ROM C**: level-fail `src/act_obj.c:1410`, remove `:1389`, light `:1419`,
  hold `:1674`, wear-by-slot `:1435-1612`, wield `:1639`
- **Gap**: baked `f"{ch.name} …"` f-strings (and `act_format(recipient=None)` for
  the wear-slot templates) → `broadcast_room`; **the hold line also used a literal
  `"in their hand."`** where ROM renders `"$n holds $p in $s hand."` (gendered
  possessive).
- **Fix**: every site → `act_to_room` (per-recipient PERS + `$s` possessive +
  TRIG_ACT).
- **Reconciled**: WEAR-004 audit row.
- **Tests**: `tests/integration/test_inv025_equipment_pers_sweep.py` (5) — wear/
  wield/hold/light/level-fail invisible→"Someone"; hold→"… in her hand". Green.

### Batch 3 — give — ✅ CLOSED (commit `4b6a012e`, 2.12.54)

- **Python**: `mud/commands/give.py` (`do_give` object branch, `_give_money` coins)
- **ROM C**: object branch `src/act_obj.c:830-846` (`MOBtrigger=FALSE` wrap),
  coins branch `:726` (NOT suppressed)
- **Gap**: both branches baked the giver name via
  `act_format(recipient=None)+_broadcast_to_room_observers`; the **coins branch
  never dispatched TRIG_ACT** though ROM `:726` is unsuppressed.
- **Fix**: both → `act_to_room(…, exclude=victim)` (auto-excluded actor +
  `exclude=victim` = ROM TO_NOTVICT). Object branch stays wrapped in
  `disable_mobtrigger()` (TRIG_ACT suppressed; `mp_give_trigger` unchanged); coins
  branch plain so TRIG_ACT now fires. Removed the now-unused
  `_broadcast_to_room_observers` helper.
- **Reconciled**: `do_give` audit row; rewrote
  `test_inv025_do_give_act_trigger_suppression.py` from the obsolete
  `mp_act_trigger_room`-call assertion to the ROM behavioral contract (observer
  receives the TO_NOTVICT line, no TRIG_ACT fires).
- **Tests**: `tests/integration/test_inv025_give_pers_sweep.py` (4) — object/coins
  invisible→"Someone"; object suppresses bystander TRIG_ACT; coins fires it. Green.

## Files Modified

- `mud/commands/obj_manipulation.py`, `inventory.py`, `consumption.py`,
  `liquids.py`, `magic_items.py` — Batch 1 conversions; dropped now-unused
  `act_format`/`broadcast_room`/`mp_act_trigger_room` imports where applicable.
- `mud/commands/equipment.py` — Batch 2 conversions (+ hold `$s` possessive fix).
- `mud/commands/give.py` — Batch 3 conversions; removed `_broadcast_to_room_observers`.
- `tests/integration/test_inv025_obj_command_pers_sweep.py` — new (7).
- `tests/integration/test_inv025_equipment_pers_sweep.py` — new (5).
- `tests/integration/test_inv025_give_pers_sweep.py` — new (4).
- `tests/integration/test_inv025_do_give_act_trigger_suppression.py` — reconciled (1).
- `docs/parity/ACT_OBJ_C_AUDIT.md` — INV-025 reconciliation notes on RECITE-002,
  BRANDISH-004, ZAP-004, WEAR-004, `do_give`.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-025 trail: re-probe CLOSED.
- `CHANGELOG.md` — 3 `Fixed` entries.
- `pyproject.toml` — 2.12.51 → 2.12.54.
- `README.md` — version badge + count, tests 5259→5281, invariants 24/24→25/25.
- `docs/sessions/SESSION_STATUS.md` — refreshed to point here.

## Test Status

- New/reconciled tests: 17/17 passing across the four files.
- Area suites green throughout (obj/inventory/consumption/liquids/magic ×126;
  equipment ×56; give/shop ×53).
- **Full suite: 5281 passed, 4 skipped** (serial `pytest -p no:xdist -o addopts=""
  -q`, ~10m). One mid-run failure was the obsolete give-suppression test, since
  reconciled and re-verified green. `ruff check` clean on all touched files (2
  pre-existing inventory.py lint nits on HEAD are unrelated and unchanged).
- `gitnexus_detect_changes` low-risk / 0 affected processes on each commit; index
  reindexed clean after the batch.

## Next Steps

The `act_format(recipient=None)` object/equipment/give class is **closed**, and
`mud/combat/`/`mud/world/`/`communication.py` were verified already-swept.
**Not yet complete:** advisor review (post-batch) surfaced a remaining
**baked-f-string `broadcast_room` TO_ROOM group** this session walked past —
`imm_load.py:120/216/277` (do_mload/oload/purge; note `do_mload` ROM uses `$N`
for the created mob, not a baked short_descr), `session.py:65` (quit),
`inspection.py:77/114` (scan/peer), `position.py:92` (rest/sit/sleep,
`act_format(recipient=None)`), `healer.py:242` (utter), `imm_search.py:472/541`
(clone), and the `doors.py:_broadcast_act_to_room` chokepoint (~12 open/close/
lock/unlock sites pass a baked `f"{actor_name} …"` string). The `doors.py`
reverse-side `rev_msg` has no `$n` (fine); `imm_load` do_restore is TO_VICT
(verify). **This is the next session's task — a 4th INV-025 PERS batch** (same
mechanical pattern, ~22 sites, ROM-string verify each). After it, move to the
remaining cross-file invariants candidates: position transitions, mob script
trigger ordering, group/follower chains.

> **Push note:** 2.12.49–51 (FIGHT-041/042 + NUKEPET-001) and 2.12.52–54
> (this session's three batches) are committed locally but **NOT yet pushed** to
> `master`. README/CHANGELOG/version reflect 2.12.54.
