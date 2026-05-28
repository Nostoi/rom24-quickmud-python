# Session Summary — 2026-05-27 — ARITH-202/205 close + ARITH-104/201 N/A reclass (2.9.81–2.9.83)

## Scope

Continued the META Class 2 ARITHMETIC_BOUNDARY close-out, picking up from the
GL-024 handoff (2.9.80). Closed the two cleanest remaining straight-fix gaps
(ARITH-202 room-light burnout floor, ARITH-205 runtime-extract carry_number
floor) as separate TDD commits, and reclassified two verified dead-code floors
(ARITH-104, ARITH-201) to ⛔ N/A. A background Sonnet subagent surveyed the
likely-N/A cluster (ARITH-004/017/018/019/104/201); its verdicts were
verified before acting, and three were deliberately left open (see Outstanding).

GitNexus was unavailable this session — its index DB is read-only
(`Cannot execute write operations`), so `gitnexus_impact` / `detect_changes`
could not run and the reindex itself can't write. Per CLAUDE.md's documented
read-only-DB exception, impact analysis fell back to grep + the integration
suite (the prescribed fallback for `game_loop.py`, which is also on the 32KB
scope-extraction failing-file list).

## Outcomes

### `ARITH-202` — ✅ FIXED (2.9.81)

- **Python**: `mud/game_loop.py:454` (`_decay_worn_light`, worn-light burnout branch)
- **ROM C**: `src/update.c:726` — `--ch->in_room->light;` raw, no floor
- **Gap**: Python clamped `room.light = max(0, current_light - 1)` on burnout; ROM decrements raw, exposing a desynced light count as negative (same philosophy as ARITH-107 nplayer / INV-023).
- **Fix**: Floor removed → `room.light = current_light - 1` with ROM-cite comment.
- **Tests**: `tests/integration/test_room_light_tracking.py::test_burnout_light_decrement_has_no_floor_exposing_desync` (room.light 0 + worn torch burns out → −1). Verified failing pre-fix (got 0). Note: `object_factory` does not sync `obj.value` from the proto (AGENTS.md gotcha) — the test sets `torch.value` explicitly, and equips under the IntEnum key `WearLocation.LIGHT` (the only key `_find_equipped_light` recognizes besides the literal `"light"`).

### `ARITH-205` — ✅ FIXED (2.9.82)

- **Python**: `mud/game_loop.py:819` (`_remove_from_character`, the `_extract_obj` carrier branch)
- **ROM C**: `src/handler.c:1678` — `ch->carry_number -= get_obj_number(obj);` raw (reached from `extract_obj`, `src/handler.c:2051`)
- **Gap**: Python clamped `carry_number = max(0, current_number - slot_cost)`; ROM subtracts raw.
- **Fix**: Floor removed → raw subtraction with ROM-cite comment. `carry_weight` is still re-summed via `_recalculate_carry_weight()`, so **INV-011 (CARRY-WEIGHT-COHERENCE) still holds on the in-sync path** — the negative surfaces only on desync. INV-011 enforcement suite re-run green.
- **Tests**: `tests/integration/test_arith_205_carry_number_no_floor.py` (carry_number 0 + one carried object extracted → −1). Verified failing pre-fix.

### `ARITH-104` — ⛔ N/A reclass (2.9.83, comment-only)

- **Python**: `mud/world/movement.py:428` `max(0, move_cost // 2)`
- **Verdict**: structurally redundant. Every `movement_loss` value is ≥1 (`movement.py:411-423`), so `move_cost ≥ 1` at line 425 and `move_cost // 2 ≥ 0` always — the floor can never fire. ROM `src/act_move.c:181` does `move /= 2` raw with the identical result. ROM-cite comment added.

### `ARITH-201` — ⛔ N/A reclass (2.9.83, comment-only)

- **Python**: `mud/game_loop.py:426` carry_weight/number fallback in `_destroy_light`
- **Verdict**: dead for real objects. Every `Object` exposes a `pIndexData` property (`mud/models/object.py:97-99`) that never raises, so `hasattr(obj, "pIndexData")` is always True and the early-return at `game_loop.py:418-420` routes through `_extract_obj` → `_remove_from_character` (the ARITH-108/109/205 raw path). Only non-`Object` test doubles reach line 426. ROM `src/handler.c:1678-1679` subtracts raw via obj_from_char. **Subagent had the mechanism right but described `Object` as "having pIndexData set as its prototype reference" — verified it's actually a property alias; conclusion stands.** ROM-cite comment added.

## Files Modified

- `mud/game_loop.py` — ARITH-202 floor removed (`_decay_worn_light`); ARITH-205 floor removed (`_remove_from_character`); ARITH-201 dead-code ROM-cite comment (`_destroy_light`).
- `mud/world/movement.py` — ARITH-104 dead-code ROM-cite comment.
- `tests/integration/test_room_light_tracking.py` — new ARITH-202 regression + `_decay_worn_light` import.
- `tests/integration/test_arith_205_carry_number_no_floor.py` — new ARITH-205 regression.
- `docs/parity/audits/ARITHMETIC_BOUNDARY.md` — flipped rows: ARITH-202 (Batch C #21) → ✅ FIXED, ARITH-205 (Batch C #24) → ✅ FIXED, ARITH-104 (Batch B #10) → ⛔ N/A, ARITH-201 (Batch C #20) → ⛔ N/A; status header tally → **21 FIXED / 19 N/A / 7 ❌ MISSING**.
- `CHANGELOG.md` — 2.9.81 / 2.9.82 / 2.9.83 sections.
- `pyproject.toml` — 2.9.80 → 2.9.83.

## Test Status

- New regressions: `test_burnout_light_decrement_has_no_floor_exposing_desync` 1/1, `test_arith_205_carry_number_no_floor.py` 1/1. Both verified failing pre-fix.
- INV-011 enforcement (`test_inv011_carry_weight_coherence.py`) + carry/extract/light suites: green.
- Full integration suite: **2346 passed, 3 skipped** in 83.18s.
- `ruff check` on touched files: clean **except** a pre-existing I001 import-sort issue at `mud/world/movement.py:1-17` (duplicate `collections.abc` imports) — not introduced this session; parked with the other documented lint debt.

## Outstanding / Next Steps

1. **Push approval needed** — local `master` is **5 commits ahead** of `origin/master` (GL-024 2.9.80 + handoff, then ARITH-202 2.9.81, ARITH-205 2.9.82, ARITH-104/201 reclass 2.9.83). Handoff commit makes 6. Verify with `git log origin/master..HEAD`. Shipping covers 2.9.80 → 2.9.83.
2. **ARITH-017 / ARITH-018 / ARITH-019 — left ❌ OPEN, need multi-path verification.** The Sonnet subagent called these N/A based on the `do_cast` gate (`mud/commands/combat.py:762` `int(getattr(char,"level",1) or 1)` clamps to ≥1). That proves only the player-cast path. These are spell handlers (`demonfire`/dispel_evil/dispel_good); the N/A bar (per ARITH-006/007/008 precedent) requires proving **all** dispatch paths — scroll/wand/potion (`obj_cast_spell` with item level, which can be 0) and mobprog (`mpcast`). Not yet checked. **Do not reclass without verifying those paths.** Cleanest next: read `obj_cast_spell` / scroll-recite level sourcing in ROM `src/magic.c` + Python equivalent, confirm whether a level-0 item can reach these handlers.
3. **ARITH-004 — stays ❌ OPEN (real divergence).** `mud/combat/engine.py:1562` `max(1, weapon_level)`: Python double-floors (`_weapon_level() or 1` at :1556 + `max(1,...)` at :1562) so it can never call `saves_spell(0, ...)`, but ROM `src/fight.c:606` uses `wield->level` raw — a level-0 weapon produces `level=0` in ROM. Candidate future fix (drop both floors; verify saves_spell handles 0).
4. **Remaining ARITH ❌ MISSING (7 total)**: ARITH-004, 017, 018, 019, 114 (get_curr_stat per-race/class ceiling — focused stat-table session), 206/207 (`reset_handler.py` arg=0 semantics — need `db.c` reset re-read), 208 (`templates.py:172` dice+bonus — UB-divisor policy check vs `docs/divergences/UB_DIVISORS.md`).
5. **GitNexus read-only DB** — `gitnexus_impact`/`detect_changes` unavailable; reindex can't write. Surface to user; if it persists, the DB file perms / lock need fixing outside the session. 32KB scope-extraction failures on `game_loop.py` etc. remain regardless.
6. **Pre-existing lint** parked: B007/F841 cluster; F541 in `shop.py:798` area; **new this session**: I001 import-sort at `mud/world/movement.py:1-17`.
7. **Pre-existing flake** at `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
8. **Worktree hygiene** — locked worktrees still present in `.claude/worktrees/`.
