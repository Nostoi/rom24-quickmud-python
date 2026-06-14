# Session Summary — 2026-06-14 — act_obj.c entry-gate sweep (GIVE-003)

## Scope

Picked up from the act_comm.c broadcast-verb sweep handoff
(`SESSION_SUMMARY_2026-06-14_ACT_COMM_TELL009_GOSSIP003.md`). The per-file audit
tracker has no ⚠️ Partial / ❌ Not Audited rows, so the active pass is the
cross-file / divergence-class sweep. The handoff named a concrete lead: the
recurring "category-error" shape in act_comm.c (a precondition checked in the
wrong order or borrowed from the wrong command family — SHOUT-005, TELL-009 —
where the **first failing gate selects the player-facing message**). The
prescribed probe target was any command file that mixes a generic gate helper
with per-command gates: **act_obj.c entry gates** (get/give/drop/put).

Method per verb: read the ROM C gate sequence top-to-bottom → diff against the
Python early-returns for *presence, order, and message* → one failing test if
they diverge. Recall check: the same method re-derives SHOUT-005/TELL-009 (read
ROM gate order, flag any presence/order/message mismatch), so its silence is
trustworthy.

`do_get`/`_get_obj` (the shared chokepoint) and `do_drop` were verified
parity-clean. `do_give`'s **object** path matched ROM gate-for-gate. The
**money** path diverged — one gap, closed.

## Outcomes

### `GIVE-003` — ✅ FIXED (v2.14.98)

- **Python**: `mud/commands/give.py:_give_money`
- **ROM C**: `src/act_obj.c:682-698`
- **Gap**: money-path gate-ordering inversion. ROM's numeric-give branch
  validates *amount + currency* first (`amount <= 0 || arg2 not in
  {coins,coin,gold,silver}` → "Sorry, you can't do that.", :683-689) and only
  **then** re-reads arg2 as the recipient and tests for a missing victim
  (:693-698 → "Give what to whom?"). Python's `_give_money` collapsed both into a
  single `if amount <= 0 or len(parts) < 3:` that prioritized the
  **missing-victim** message, so a malformed currency or non-positive amount
  with **no recipient** (`give 3 copper`, `give 0 gold`) wrongly returned
  "Give what to whom?" instead of ROM's "Sorry, you can't do that." Same
  gate-ordering class as SHOUT-005/TELL-009.
- **Fix**: reordered `_give_money` to check amount/currency before the recipient,
  matching ROM. Local to one function (LOW impact — only caller is `do_give`).
- **Tests**: `tests/integration/test_give_command.py::test_give003_invalid_currency_without_target_uses_sorry_not_missing_target`
  + `::test_give003_zero_amount_without_target_uses_sorry_not_missing_target`
  (2, green). Both pre-existing currency tests
  (`give 3 copper receiver` → Sorry; `give 3 gold` → Give-what-to-whom) stayed
  green — only the untested bad-currency/bad-amount-AND-missing-victim
  combination diverged.

### `do_get` / `_get_obj` — ✅ VERIFIED CLEAN (no change)

- **Python**: `mud/commands/inventory.py:_get_obj` (+ `do_get`)
- **ROM C**: `src/act_obj.c:92-191` (get_obj helper), `:195-342` (do_get)
- The shared `_get_obj` chokepoint tracks ROM gate-for-gate and in order:
  ITEM_TAKE → carry_number → carry_weight (with the in-obj/carried-by skip) →
  can_loot → furniture-occupancy → pit level/timer → money/autosplit. No
  borrowed or missing gate. The pit "Don't be so greedy!" + closed-container +
  corpse-loot gates in `do_get`'s container branch also match.

### `do_drop` — ✅ VERIFIED CLEAN (no change)

- **Python**: `mud/commands/inventory.py:do_drop`
- **ROM C**: `src/act_obj.c:496-655`
- The money branch reads the currency token **before** validating it
  (`drop 5 banana` → "Sorry, you can't do that."), so it does **not** share the
  GIVE-003 inversion (do_drop has no recipient argument, so there is no
  missing-victim branch to mis-order). Object / all / all.obj branches
  (can_drop_obj, MELT_DROP, wear_loc skip) match ROM.

## Files Modified

- `mud/commands/give.py` — reordered `_give_money` amount/currency gate before
  the missing-recipient gate (GIVE-003).
- `tests/integration/test_give_command.py` — added two `test_give003_*` tests.
- `docs/parity/ACT_OBJ_C_AUDIT.md` — added GIVE-003 row (✅ FIXED); noted in the
  do_give "Remaining Gaps" line.
- `CHANGELOG.md` — added 2.14.98 (GIVE-003) section.
- `pyproject.toml` — 2.14.97 → 2.14.98.

## Test Status

- `tests/integration/test_give_command.py` + `test_drop_command.py` — 32/32
- give-001/inv025/mobprog-give related suites — 9/9
- Full suite: **5787 passed, 4 skipped** (was 5785; +2 GIVE-003 tests)
- `ruff check` (changed files) — clean
- GitNexus reindexed clean post-commit.

## Next Steps

The act_obj.c entry-gate probe is done for get/give/drop. The remaining
`do_put` object/all branches were read against ROM during the sweep and showed
no gate-ordering or borrowed-gate divergence (put has no recipient/currency
mis-order surface; its gates — closed-container, fold-into-itself, can_drop_obj,
WEIGHT_MULT, fit-by-weight, pit-timer — map 1:1 to ROM `:357-489`), but were not
locked with a fresh test this pass. If continuing the "category-error" lead,
the next untouched candidates are the **position/condition gate families** in
`consumption.py` (do_eat/do_drink/do_quaff — ROM gates on item type + hunger/
thirst + position) and `act_move.c` entry gates, though move_char is a single
gate site (low borrowing surface for this class). Alternatively, per the roster,
the explicitly-named open lever is **Hypothesis state-machine → diff_harness
widening** (Class 11/Phase C), which is enumeration-independent and where most
recent FINDING-0xx actually originated — higher expected yield than another
hand-picked verb probe.
