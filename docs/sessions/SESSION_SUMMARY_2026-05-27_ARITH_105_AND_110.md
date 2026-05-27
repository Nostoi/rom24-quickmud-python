# Session Summary — 2026-05-27 — ARITH-105 fix + ARITH-110 reclass (2.9.72 + 2.9.73)

## Scope

Picked up after 2.9.71 (`2f05d054`, session handoff for ARITH-005 + ARITH-209)
per `docs/sessions/SESSION_STATUS.md`. The prior session's "Next Intended Task"
named **ARITH-105** (`get_curr_stat` floor 0→3) as the largest remaining ARITH
gap. This session closed it, surfaced a related ceiling divergence as the new
**ARITH-114**, then opportunistically reclassified the next-easiest sibling
**ARITH-110** (pet-shop haggle floor) as N/A after a math proof of
unreachability — and held back its sibling **ARITH-111** (item-shop haggle
floor) with a documented reachability condition that needs deeper
`deduct_cost`-side analysis.

Two commits this session, one fix + one reclass, each with its own version bump.

## Outcomes

### `ARITH-105` — ✅ FIXED (2.9.72, `7b6bc45`)

- **Python**: `mud/models/character.py:469-485` — `get_curr_stat`. Was
  `return max(0, min(25, total))`; now
  `return max(3, min(25, total))`. Docstring rewritten to cite ROM and
  flag the separately-tracked ceiling divergence.
- **ROM C**: `src/handler.c:872` — `return URANGE (3, ch->perm_stat[stat]
  + ch->mod_stat[stat], max);`. Minimum stat is **3**, never 0.
- **Divergence**: Pre-fix, stacked debuffs (e.g. `weaken`, `chill_touch`,
  plague tick, cursed equipment) could drive a character's effective
  STR/INT/WIS/DEX/CON to 0–2 and feed wrong-row reads of `str_app`
  (hit/dam), `dex_app` (defensive AC, save-vs-spell, carry), `con_app`
  (HP gain on level), `int_app` (learn rate), `wis_app` (practice gain
  on level), and the `_STR_WIELD` ladder. ROM walls those table rows
  off as defensive padding only; they are never indexed in PC stat-space
  under correct rules.
- **Test (new)**: `tests/integration/test_get_curr_stat_floor_three.py` —
  17 parametrized cases across STR/INT/WIS/DEX/CON × {heavily-debuffed
  (perm 13, mod -15 = -2 raw), exactly-zero (perm 13, mod -13 = 0 raw),
  already-3 boundary, positive-buff sanity, ceiling sanity}. Pre-fix:
  10 failed / 7 passed. Post-fix: 17/17 passing.
- **Test (updated)**: `tests/integration/test_advancement_con_app.py::
  test_advance_level_hp_minimum_floor_is_two` — was reaching the
  `UMAX(2, add_hp)` defensive floor in `advance_level` via the buggy
  CON-0 path. Per AGENTS.md ("A test asserting a behavior that
  contradicts ROM C is a bug in the test, not in the implementation"),
  rewrote it to verify the floor via `monkeypatch(con_hitp_bonus, -4)`
  + pinned `number_range`. Same intent (the `UMAX(2, ...)` floor at
  `mud/advancement.py:114` is still verified), but the input no longer
  violates the ROM CON-3 floor.
- **Suite**: full integration run **2334 passed, 3 skipped** in 75.52s
  (was 2317 baseline + the 17 new ARITH-105 cases).

### `ARITH-114` — ❌ MISSING (filed, not closed)

Surfaced during ARITH-105 close as a sibling divergence at the **same
line** but a different direction:

- **Python**: `mud/models/character.py:478` clamps the ceiling to a flat
  `min(25, total)`.
- **ROM C**: `src/handler.c:856-870`. For NPCs / immortals the ceiling
  is 25; for PCs it is `pc_race_table[ch->race].max_stats[stat] + 4`
  (+2 if class prime, +1 if human), then `UMIN(max, 25)`. So PC stats
  in Python can exceed ROM's per-race/class soft cap.
- Companion site at `mud/world/movement.py:151` (Batch B row 9) was
  marked ✅ MATCH at triage and stays ✅ MATCH because it reads NPC
  stats only — that judgement is unaffected by this new finding.
- Filed in the audit doc at the appropriate position with status
  ❌ MISSING. Not in scope for this commit.

### `ARITH-110` — ⛔ N/A (reclassified, 2.9.73, `bf51a43`)

- **Python**: `mud/commands/shop.py:586` — `cost = max(0, cost -
  discount)` where `discount = (cost // 2) * roll // 100` and
  `roll = number_percent() ∈ [0, 99]`.
- **ROM C**: `src/act_obj.c:2601-2608 do_buy (pet)` —
  `cost -= cost / 2 * roll / 100;` raw, no floor.
- **Reachability proof** (closed-form):
  - `discount ≤ c_div(c_div(cost, 2) * 99, 100) < c_div(cost, 2)`
  - so `cost - discount > cost - c_div(cost, 2) ≥ 0` for all
    `cost ≥ 0`.
- **Decision**: dead defensive code — same shape as ARITH-006 / 007 /
  008 / 013 / 014. Floor kept; ROM-cite comment added at
  `mud/commands/shop.py:582-590` documenting the unreachability and
  pointing to the audit row.
- **Tests**: no regression added — comment-only change. Confirmed
  the shop suite still green: **66 passed** across
  `tests/test_shops.py`, `tests/test_shop_conversion.py`,
  `tests/integration/test_olc_save_004_mob_shops.py`,
  `tests/integration/test_shop_room_broadcasts.py`.

### `ARITH-111` — ❌ MISSING (left open with reachability docs)

Initially scoped as ARITH-110's sibling for a "one ROM function, two
sites" combined commit (the way ARITH-101 / 102 / 103 closed in
2.9.66). Reading the Python source more carefully showed it is **not**
the same shape:

- ROM at `src/act_obj.c:2727` is `cost -= obj->cost / 2 * roll / 100;`
  — the discount is derived from `obj->cost` (the unmarked-up proto
  cost) but applied to the **marked-up** working `cost =
  obj->cost * profit_buy / 100`.
- When a shop's `profit_buy < 50`, the discount can exceed `unit_price`,
  driving the working cost negative. ROM has no clamp; Python clamps
  to 0 (free item).
- A clean close requires deciding how `deduct_cost` should behave with
  a negative cost (does it ADD money to the player? does the
  silver/gold split underflow?). Held back for a future targeted
  session with a probe-then-scope on the negative-cost interaction.
- Documented inline in the audit-doc row 26 with the conditions and
  the held-back rationale.

## Files Modified

- `mud/models/character.py` — ARITH-105 fix (line 478 floor 0→3,
  docstring rewrite with ROM cite + ARITH-114 cross-reference).
- `mud/commands/shop.py` — ARITH-110 ROM-cite comment + unreachability
  proof at the pet-shop haggle site (line 582-590).
- `tests/integration/test_get_curr_stat_floor_three.py` — new file,
  17 parametrized regression tests for the ARITH-105 floor.
- `tests/integration/test_advancement_con_app.py` — updated
  `test_advance_level_hp_minimum_floor_is_two` to verify the
  `UMAX(2, add_hp)` floor via `monkeypatch(con_hitp_bonus, -4)` instead
  of the now-impossible CON-0 path.
- `docs/parity/audits/ARITHMETIC_BOUNDARY.md` — flipped ARITH-105 to
  ✅ FIXED (gap-table row + Batch B row 13); filed ARITH-114 as a new
  ❌ MISSING gap-table row; flipped ARITH-110 to ⛔ N/A (Batch B row 25);
  expanded ARITH-111 (Batch B row 26) with reachability conditions and
  hold-back rationale; updated status header tally and summary table.
- `CHANGELOG.md` — `[2.9.72]` Fixed entry (ARITH-105) + ARITH-114 file
  note; `[2.9.73]` Changed entry (ARITH-110 reclass + ARITH-111 note).
- `pyproject.toml` — `2.9.71` → `2.9.72` → `2.9.73`.

## Test Status

- New: `tests/integration/test_get_curr_stat_floor_three.py` — 17/17
  passing across STR/INT/WIS/DEX/CON × debuffed/zero/at-floor/buff/cap.
- Touched: `tests/integration/test_advancement_con_app.py::
  test_advance_level_hp_minimum_floor_is_two` — passing post-rewrite.
- Full integration suite (run after the ARITH-105 fix):
  **2334 passed, 3 skipped** in 75.52s.
- Shop suite (run after the ARITH-110 reclass): **66 passed** in 27.19s.
- Pre-existing pyright diagnostics in `mud/commands/shop.py` (rows 81 /
  86 / 212 / 216 / 261 / 220 / 328) confirmed unchanged by this
  session's edits at line 582-590 (different lines, separate
  `_ShopContext` type-hints territory).

## GitNexus / lint hygiene

- Stop-and-reindex rule fired twice (after `7b6bc45` and after
  `bf51a43`); both reindexes completed in background.
- FTS-index read-only DB warning continues to fire on every Bash hook
  (documented persistent upstream issue; node/edge graph remains
  current).
- `mud/models/character.py` is in the gitnexus-blacklisted file list
  (per CLAUDE.md 32 KB scope-extractor cap), so `gitnexus_impact` on
  `get_curr_stat` would have under-counted callers. Fell back to
  `grep -rn` and surveyed the call sites
  (`mud/game_loop.py`, `mud/advancement.py`, the str_app/dex_app/
  con_app/int_app/wis_app accessor wrappers in `mud/math/stat_apps.py`,
  and downstream prompt/hit/dam/AC consumers). Blast radius reported
  to user before editing.
- `mud/commands/shop.py` is also gitnexus-blacklisted; comment-only
  edit so no caller-graph implication.

## Push state

- `origin/master` still at `2f05d054` (2.9.71 handoff). Local `master`
  is now `bf51a43` (2.9.73), **3 commits ahead** of `origin/master`
  (ARITH-005 fix from prior session + ARITH-209 reclass from prior
  session + ARITH-105 fix this session + ARITH-110 reclass this
  session — actually 4 commits if counting all unpushed; verify with
  `git log origin/master..HEAD`). Approval required before next push.

## Outstanding

- **ARITH-111** held back with documented reachability conditions —
  needs `deduct_cost`-side analysis when working `cost` goes negative.
  Probe candidate: trace `deduct_cost(char, negative_cost)` through
  the gold/silver split at `mud/commands/shop.py` and ROM
  `src/act_obj.c:2746-2748` to see whether ROM's negative-cost
  behavior is itself coherent (it may be a known ROM bug).
- **ARITH-114** filed as a new ❌ MISSING — the per-race/class
  PC ceiling on `get_curr_stat`. High blast radius (every
  stat-dependent calc above the cap), but only matters for PCs with
  equipment buffs pushing into 22–25 territory. Real-world impact
  needs measurement vs. shipped class table values.
- **24 ❌ MISSING** remaining in the ARITH triage after this session
  (was 25 at session start: +1 ARITH-114 filed, −1 ARITH-105 closed,
  −1 ARITH-110 reclassed N/A, +1 ARITH-114 already counted = 24 net).
  Next-easiest probes likely in the level-0 spell/skill dice cluster
  (ARITH-020/021/022/023) or the carry-weight/number sites
  (ARITH-106/108/109/112/113 — all the same `obj_from_char`
  divergence at five sites).
- **Pre-existing lint** still parked: `mud/handler.py:566-567` (F841),
  `mud/handler.py:960` (F401), `tests/integration/test_do_practice_command.py:255`
  (F841), `mud/commands/combat.py:685` (F541). New pyright diagnostics
  in `mud/commands/shop.py` (line 81/86/212/216/261/220/328) are
  pre-existing — verified by reading the file before editing.
- **Pre-existing flake** at `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
- **Worktree hygiene** — locked worktrees still present in
  `.claude/worktrees/`.

## Next Intended Task

1. **Push approval needed** — 4 commits ahead for 2.9.70 / 2.9.71 /
   2.9.72 / 2.9.73 (verify with `git log origin/master..HEAD`).
2. **Carry-weight/number cluster** —
   ARITH-106/108/109/112/113 are five sites of the same
   `obj_from_char` divergence (`max(0, carry_weight - delta)` and
   `max(0, carry_number - 1)` floors that ROM does not have). Likely
   closeable as one commit pattern like ARITH-101/102/103 did for
   `create_money`. Need to verify ROM's `obj_from_char` at
   `src/handler.c:1678-1679` doesn't have a hidden upstream guard.
3. **Level-0 spell/skill dice cluster** — ARITH-020/021/022/023.
   Reachable via mob-program or scripted dispatch per the audit doc;
   probe ROM source first to see whether each is a real divergence
   or dead defensive code.
4. **ARITH-111** when ready — the held-back item-shop haggle floor.
   Needs the `deduct_cost`-with-negative-cost analysis described in
   the audit doc row 26.
5. **ARITH-114** — the new PC-ceiling divergence on `get_curr_stat`.
   Lower priority than the level-0 / carry-tracking clusters because
   it only matters above stat-22, which is a small fraction of PC
   gameplay.
