# Session Summary — 2026-06-04 — XP-DELIVERY-001 + FINDING-027 money/coin parity

## Scope

Started from a live player bug report: "You receive 155 experience points."
printed *after* the player walked north out of the room where the kill happened.
Root-caused the message-ordering divergence, then — while finishing the
in-progress diff-harness money widening that SESSION_STATUS had queued as the
next task (`drop gold/silver`, `get coins`, `give coins`) — the new
`money_drop_get_give` scenario surfaced two further ROM divergences in coin-object
handling. All three fixed this session across two commits.

## Outcomes

### `XP-DELIVERY-001` — ✅ FIXED (INV-001 wrong-channel cousin)

- **Python**: `mud/groups/xp.py:group_gain`/`_drop_alignment_conflicts`,
  `mud/advancement.py:advance_level`/`gain_exp`
- **ROM C**: `src/fight.c:1788` (`group_gain` → `send_to_char(buf, gch)`),
  `src/update.c:113` (`advance_level`), `src/update.c:131` (`gain_exp`)
- **Gap**: a kill resolves during a combat *tick* (`violence_update`), when
  nothing drains the `char.messages` mailbox. The four death-chain lines using
  the mailbox-only `Character.send_to_char` (XP award, level-up, "you gain N hit
  points", alignment-conflict zap) surfaced only at the player's *next* command.
  The sibling auto-loot line already used `push_message`, which is why it arrived
  on time and exposed the ordering.
- **Fix**: routed all four sites through the canonical async-aware
  `send_to_char_buffered` (loop-aware: async send for connected PCs, mailbox
  fallback for disconnected/tests). Filed under INV-001's wrong-channel-cousins
  trail (the inverse of double-delivery), not a new INV.
- **Tests**: `tests/integration/test_group_gain_tick_delivery.py` (new,
  connected-socket-at-tick-time, fail→pass); `test_character_advancement.py::
  test_level_up_message_sent_to_character` re-pointed to the canonical
  mailbox-fallback path.

### `FINDING-027` (a) — money object vnum swap — ✅ RESOLVED

- **Python**: `mud/models/constants.py:OBJ_VNUM_GOLD_SOME`/`OBJ_VNUM_SILVER_SOME`
- **ROM C**: `src/merc.h:1022-1023` (`GOLD_SOME 3`, `SILVER_SOME 4`)
- **Gap**: the two constants were transposed (silver_some=3, gold_some=4), so
  `drop 50 silver` built coin vnum 3 where the C golden had vnum 4. All consumers
  use the symbolic names, so flipping the values is transparent.

### `FINDING-027` (b) — `create_money` fabricated-proto wording/cost — ✅ RESOLVED

- **Python**: `mud/handler.py:create_money`
- **ROM C**: `src/handler.c:2438-2480`; prototypes `area/limbo.are` #1-#5
- **Gap**: `create_money` hand-rolled prototype strings/economics instead of
  mirroring ROM's limbo.are protos (ROM uses the proto `short_descr` as a printf
  format). Divergences: "one silver coin"/"one gold coin" → ROM "a silver
  coin"/"a gold coin"; "N silver and N gold coins" → ROM "N silver **coins** and
  N gold coins"; gold-only `cost = 100*gold` → ROM `obj->cost = gold`
  (`handler.c:2454`).
- **Fix**: `create_money` now fabricates a per-call `ObjIndex` matching limbo.are
  #1-#5 exactly (name keywords incl. `gcash`, short_descr wording, description,
  value, weight) with ROM's per-branch value/cost/weight. A **per-call** proto is
  required (not the shared registry proto) because Python reads object weight from
  `prototype.weight` (`inventory.py:_get_obj_weight`), so each coin needs its own
  weight; the ONE branches keep the proto untouched, only SOME/COINS override.
- **Tests**: `tests/integration/test_money_objects.py` (30 cases; the 4 that
  encoded the old port behavior realigned to ROM with source citations);
  C-golden `money_drop_get_give` replay.

### Diff-harness widening (supporting infrastructure)

- Added `silver` to the snapshot through the whole pipeline (`diffmain.c`,
  `pysnap.py`, `schema.py` with a backward-compat default) and `__gold=`/
  `__silver=` replay meta-commands.
- `pyreplay.py:__mload` now snapshots a spawned mob **only** when its key is in
  `watch.chars` — matching the C shim, which resolves snapshot keys strictly from
  the declared watch set. (Previously Python auto-watched every mload'd mob;
  diverged for undeclared give/transfer targets like the scenario's "wizard".)
- New scenario `tools/diff_harness/scenarios/money_drop_get_give.json` + golden;
  all 7 goldens regenerated (silver field + new scenario).

## Files Modified

- `mud/groups/xp.py`, `mud/advancement.py` — async-aware delivery for tick-time
  death-chain messages (XP-DELIVERY-001).
- `mud/models/constants.py` — money vnum constants un-swapped.
- `mud/handler.py` — `create_money` per-call proto rewrite (FINDING-027b).
- `src/diff_shim/diffmain.c` — emit `silver`; `__gold=`/`__silver=` meta-commands.
- `tools/diff_harness/{schema,pysnap,pyreplay,compare}.py` — silver field;
  `__mload` watch-set parity.
- `tools/diff_harness/scenarios/money_drop_get_give.json` — new scenario.
- `tools/diff_harness/FINDINGS.md` — FINDING-027 (RESOLVED).
- `tests/integration/test_group_gain_tick_delivery.py` — new.
- `tests/integration/test_character_advancement.py`,
  `tests/integration/test_money_objects.py`, `tests/test_diff_harness_unit.py` —
  realigned to ROM / new silver field.
- `tests/data/golden/diff/*.golden.json` — regenerated (silver + new scenario).
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-001 trail (XP-DELIVERY-001).
- `CHANGELOG.md`, `pyproject.toml` — 2.13.9 → 2.13.11.

## Test Status

- `tests/integration/test_group_gain_tick_delivery.py` — passing.
- `tests/integration/test_money_objects.py` — 30/30 passing.
- Diff-harness: `tests/test_differential_smoke.py` + `test_diff_harness_unit.py`
  + `test_diff_harness_generated.py` — 25 passing (7 scenarios incl. new money).
- Full suite: **5425 passed, 4 skipped** (`pytest`, ~289s).
- `ruff check .` clean.

## Next Steps

1. Continue Phase C deterministic diff-harness widening on adjacent no-RNG paths
   (the money class is now covered: drop/get/give coins).
2. Optional follow-up filed in FINDING-027: ROM `create_money` clamps invalid
   input (`gold = UMAX(1, gold)`) and never returns NULL; the Python port still
   returns `None` and callers guard on it. Not exercised by any scenario; left
   as-is (changing it touches the `make_corpse`/`do_drop` caller contract).
3. Optional: add connected-socket tick-time tests for the level-up / "you gain
   hit points" / zap delivery sites (same helper as XP, mechanism already proven).
