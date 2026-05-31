# Session Summary — 2026-05-31 — TRAIN-004 + INV-025 door-command family

## Scope

Cross-file-invariants primary pass (per-file audit tracker exhausted). Picked
up from `SESSION_STATUS.md`'s "Next Intended Task" list: (1) the carried-over
`get_max_train` hardcoded-22 divergence (TRAIN-004), then (2) the next INV-025
act-dispatch slice — the door-command family `do_close`/`do_lock`/`do_unlock`/
`do_pick`, mirroring the already-closed `do_open` follow-up. Two gaps closed,
one commit each, failing-test-first.

## Outcomes

### `TRAIN-004` / `WIZ-050` — ✅ FIXED (2.12.2, commit a39f68ee)

- **ROM C**: `src/act_move.c:1716-1725,1781` (`do_train` stat caps) +
  `src/handler.c:876-893` (`get_max_train`).
- **Python**: `mud/handler.py:get_max_train`, `mud/commands/advancement.py:do_train`,
  `mud/commands/imm_set.py:do_mset` (consumer).
- **Gap**: `do_train` hardcoded `max_stat = 22` at both cap sites; ROM
  `get_max_train` is race/class-dependent (`pc_race_table[race].max_stats[stat]`
  + prime-class bonus **+3 human / +2 other**, clamped 25 — the audit note's
  "+4" was wrong, caught by reading source).
- **Root cause (cross-file)**: a *shared broken helper* — `mud.handler.get_max_train`
  already existed but compared the **int** `ch.race` index against PC-race
  *name* strings and read a non-existent `class_num` attr, so for every real PC
  it fell through a hardcoded `return 18`. This silently capped `do_mset`'s
  `set char <name> <stat> <value>` ranges at 18 regardless of race (WIZ-050),
  and was shadowed in `do_train` by its own literal 22.
- **Fix**: corrected `get_max_train` at the root (int-race→name bridge via
  `get_race_by_index`/`get_pc_race`, correct `ch_class`, ROM `+3/+2` prime
  bonus, fallback 25 not 18) and routed both `do_train` sites through the one
  helper. `do_mset` ranges fixed for free. Collapsed an initial duplicate
  `Character.get_max_train` (advisor reconciliation: ROM's `get_max_train`
  lives in `handler.c`, so `mud/handler.py` is the faithful home).
- **Tests**: `tests/integration/test_recall_train_commands.py` — 3 new
  (`test_train_caps_human_nonprime_stat_at_race_max`, `::_caps_dwarf_dex_at_race_max`,
  `::_prime_stat_gets_class_bonus` [+3 human], `::_prime_stat_nonhuman_bonus_is_plus_two`
  [+2 giant] = 4); `tests/integration/test_imm_set_stat_range.py` — 1 new
  (dwarf STR settable to 20, rejected at 21); corrected
  `tests/test_advancement.py::test_train_lists_only_unmaxed_stats` (had encoded
  the old "race_max + 4 = 22" assumption). All verified red-first.

### INV-025 door family — ✅ FIXED (2.12.3, commit e2140828)

- **ROM C**: `src/act_move.c:534`/`:690`/`:825`/`:981` (actor-room
  `act("$n closes/locks/unlocks/picks …", …, TO_ROOM)`, no `MOBtrigger=FALSE`
  wrap) + `src/comm.c:2384-2385` (TRIG_ACT dispatch to NPC recipients).
- **Python**: `mud/commands/doors.py` — `do_close`, `do_lock`, `do_unlock`,
  `do_pick`.
- **Gap**: these four routed their actor-room lines through plain
  `broadcast_room`, so a mob scripted on "$n closes/locks/unlocks/picks …"
  silently no-opped. Only `do_open` had been wired (the INV-025 follow-up gap).
- **Fix**: swapped the two object broadcasts (`arg1=obj`) and the actor-room
  door broadcast (`arg2=keyword`) per command — 12 sites total — to the
  existing `_broadcast_act_to_room` helper, exactly mirroring `do_open`. The
  reverse-side linked-room broadcasts (`doors.py:209`/`:302`) were
  **deliberately left** as plain `broadcast_room` to stay symmetric with the
  `do_open` precedent (advisor catch).
- **Tests**: `tests/integration/test_inv025_door_commands_act_trigger_dispatch.py`
  — 4 new (one per command), all verified red against the pre-fix path.

## Files Modified

- `mud/handler.py` — corrected `get_max_train` (int-race→name bridge, `ch_class`,
  +3/+2 prime bonus, fallback 25).
- `mud/commands/advancement.py` — `do_train` routes both cap sites through
  `get_max_train`; removed the literal 22 + wrong comments.
- `mud/commands/doors.py` — `do_close`/`do_lock`/`do_unlock`/`do_pick`
  actor-room + object broadcasts routed through `_broadcast_act_to_room`.
- `tests/integration/test_recall_train_commands.py` — +4 TRAIN-004 tests.
- `tests/integration/test_imm_set_stat_range.py` — new (WIZ-050).
- `tests/integration/test_inv025_door_commands_act_trigger_dispatch.py` — new (4).
- `tests/test_advancement.py` — corrected `test_train_lists_only_unmaxed_stats`.
- `docs/parity/ACT_MOVE_C_AUDIT.md` — TRAIN-004 → ✅ FIXED.
- `docs/parity/HANDLER_C_AUDIT.md` — corrected the false-✅ `get_max_train` row.
- `docs/parity/ACT_WIZ_C_AUDIT.md` — new WIZ-050 row (✅ FIXED).
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-025 follow-up sweep +
  "Touched by" trail extended to the door family; reverse-side open follow-up filed.
- `CHANGELOG.md` — TRAIN-004/WIZ-050 + INV-025 door-family entries.
- `pyproject.toml` — 2.12.1 → 2.12.3.

## Test Status

- `pytest tests/integration/test_recall_train_commands.py test_imm_set_stat_range.py
  test_advancement.py` — green; INV-025 + door suites — 263 passed.
- Full suite: **5116 passed, 4 skipped** (`pytest`, ~183s).
- `ruff check` on changed files — clean.
- `gitnexus_detect_changes` — LOW risk, scoped to expected symbols both commits.

## Outstanding / Next Steps

- **INV-025 reverse-side door broadcasts (uniform open follow-up)**:
  `do_open:209` ("The $d opens.") and `do_close:302` ("The $d closes.") in the
  *linked* room are still plain `broadcast_room`. ROM's `act(..., rch, TO_CHAR)`
  loop there (`src/act_move.c:447-448`/`:545-547`) would dispatch TRIG_ACT to a
  far-room NPC via `src/comm.c:2384`. Left untouched to stay symmetric with the
  `do_open` precedent; close `do_open` + `do_close` together if pursued
  (lock/unlock/pick have no reverse-side broadcast — ROM silently sets bits).
- Resume INV-025 sweep on the broader `_push_message`/`broadcast_room`
  narration surface (non-combat act() lines).
- Other probe candidates: affect ticks, position transitions, mob script
  triggers, group/follower chain.
