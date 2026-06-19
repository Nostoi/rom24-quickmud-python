# Session Summary — 2026-06-19 — /loop gap-closer: signed-math + reset-limit divergences

## Scope

`/loop` gap-closer session (target 5 gaps → **closed 4 genuine reachable ones,
stopped honestly rather than pad a 5th**). Per-file audit tracker remains
exhausted, so this was a cross-file / divergence-class (Layer B/C) sweep. The
documented next probes from the prior summary (`do_value`, buy-side cost
inheritance) were re-verified **clean** — already reconciled. The productive
vein was **signed integer math (Layer B, divergence class 7)** and a comparison
of ROM `reset_room` against Python `apply_resets`, which surfaced four real
divergences and one larger finding (DB-003) filed for a dedicated audit.

A stronger-model advisor pass at the start caught the first gap (BUY-010) on a
surface I had just declared clean, and steered the session: "each gap must be a
ROM-C divergence you can point to; three real beats five padded; if the well
runs dry, close what's real and write an honest handoff."

## Outcomes

### `BUY-010` — ✅ FIXED (2.14.164)

- **Python**: `mud/commands/shop.py:876-877`
- **ROM C**: `src/act_obj.c:2747-2748`
- **Gap**: keeper coin split on a negative-total buy used bare `//`/`%`. When a
  shop's `profit_buy < 50`, a winning haggle drives `cost*number` NEGATIVE (buyer
  refunded via `deduct_cost`). C truncates toward zero / `%` takes the dividend
  sign; Python `//`/`%` floor / take the divisor sign — same net wealth, divergent
  gold/silver split (total −9 → ROM gold 0/silver −9, Python gold −1/silver +91).
- **Fix**: split with `c_div`/`c_mod`.
- **Tests**: `tests/test_shops.py::test_buy_negative_total_cost_keeper_split_uses_c_truncation`; full shop suite 46/46.

### `ARITH-114` — ✅ FIXED (2.14.165)

- **Python**: `mud/models/character.py:660`, new `mud/handler.py:get_curr_stat_max`
- **ROM C**: `src/handler.c:872` (`get_curr_stat`)
- **Gap**: `Character.get_curr_stat` clamped every character's effective stat to a
  flat 25. ROM caps a PC at `pc_race_table[race].max_stats[stat] + 4` (+2 prime,
  +1 human), `UMIN(.,25)`; only NPCs/immortals use flat 25. Gear/spell `mod_stat`
  buffs on a low-cap race could exceed ROM's soft cap (elf STR 16 + 8 gear read
  24, ROM 20) — inflating combat, regen, carry capacity. Distinct from
  `get_max_train` (trainable cap, +2/+3 prime, no +4) which was already correct.
- **Fix**: added `get_curr_stat_max` helper (ROM `get_curr_stat` ceiling) and routed
  the accessor through it; non-`pc_race` rows (race 0 / NPC) fall back to 25.
- **Impact**: gitnexus rated this **CRITICAL** (11 direct callers); user approved
  proceeding. **Full suite 5879 passed, 0 regressions** — test chars use race 0
  → flat-25 fallback, real-stat tests stay under the cap.
- **Tests**: `tests/test_player_stats.py::TestStatBoundsAndClamping::test_get_curr_stat_caps_at_race_class_ceiling_not_flat_25`.

### `DB-002` — ✅ FIXED (2.14.166)

- **Python**: `mud/spawning/reset_handler.py:421`
- **ROM C**: `src/db.c:1703` (`reset_room` M-reset global check)
- **Gap**: ROM skips an M-reset spawn via `if (pMobIndex->count >= pReset->arg2)` —
  unconditional, so `arg2 == 0` (`count(0) >= 0`) means the mob is **never**
  spawned. Python guarded the check with `global_limit > 0`, so an `arg2 == 0`
  reset fell through and spawned. **Reachable in shipped data**: `canyon.are`'s
  `M 0 9202 0 9204 0` (the deliberately disabled cyclops) spawned a cyclops in
  room 9204 that ROM never creates (confirmed empirically).
- **Fix**: removed the `global_limit > 0` guard → `if proto_count >= global_limit:`.
- **Tests**: `tests/test_db_resets_rom_parity.py::test_m_reset_global_limit_zero_never_spawns`; full suite 5880 passed.

### `ARITH-206` — ✅ FIXED (2.14.167)

- **Python**: `mud/spawning/reset_handler.py:405`
- **ROM C**: `src/db.c:1715-1723` (`reset_room` M-reset room check)
- **Gap** (documented "needs follow-up", now resolved): ROM's room check
  `if (count >= pReset->arg4)` uses arg4 raw, so `arg4 == 0` means "never place
  here" (NOT "unlimited"). Python's `max(1, room_limit)` floor turned `arg4 == 0`
  into "spawn up to 1".
- **Fix**: removed the floor; the existing `if room_limit <= 0: continue` guard
  now handles `arg4 == 0` ROM-faithfully. Unreachable in current data (the only
  `arg4 == 0` M-reset is the cyclops, already skipped at the global check), so
  zero regression — ROM-correct edge behavior + future-proof.
- **Tests**: `tests/test_db_resets_rom_parity.py::test_m_reset_room_limit_zero_never_spawns`; full suite 5881 passed.

## Outstanding (filed durably — do NOT lose)

- **`DB-003` — 🔄 OPEN, needs investigation** (`docs/parity/DB_C_AUDIT.md`).
  O-reset semantics diverge from ROM two ways: (a) Python allows `desired_total`
  copies per room (`room_obj_targets`) where ROM places one per room
  (`count_obj_list > 0` skip); (b) Python imposes a synthetic
  `_resolve_reset_limit(arg2)` global cap (`reset_handler.py:524-525`) that ROM's
  O-reset does not have (ROM ignores arg2 for O — `src/db.c:1773-1796`). Reachable
  (most O-resets carry non-`{0,-1}` arg2; many obj_vnums span multiple rooms).
  **Filed, not closed**: looks possibly-intentional, the fix is an entangled
  two-way world-population change with broad blast radius, and GitNexus MCP was
  down (no impact analysis). Needs a dedicated audit session.
- **`ARITH-207` vs `ARITH-209` — documentation contradiction.** The P-reset
  `max(1, int(reset.arg4 or 1))` floor (`reset_handler.py:676`) is called
  `ARITH-207 ❌ MISSING` in the audit table but `ARITH-209 ⛔ N/A` (intentionally
  kept) by the in-code comment. Not closed — resolve the conflict before acting.
- **`ARITH-208` — confirmed unreachable.** No mob proto in shipped data has a
  negative HP/mana dice bonus (checked all of `mob_registry`), and removing the
  `max(0, dice+bonus)` floor would risk a "mob spawns with negative HP → instantly
  dead" path. Left as-is; not a clean gap.

## Files Modified

- `mud/commands/shop.py` — BUY-010 keeper coin split via `c_div`/`c_mod`.
- `mud/models/character.py` — ARITH-114 `get_curr_stat` routed through ceiling helper.
- `mud/handler.py` — new `get_curr_stat_max` helper.
- `mud/spawning/reset_handler.py` — DB-002 (global guard) + ARITH-206 (room floor).
- `tests/test_shops.py`, `tests/test_player_stats.py`, `tests/test_db_resets_rom_parity.py` — 4 new failing-first tests.
- `docs/parity/ACT_OBJ_C_AUDIT.md` — BUY-010 row; `docs/parity/audits/ARITHMETIC_BOUNDARY.md` — ARITH-114, ARITH-206 rows ✅; `docs/parity/DB_C_AUDIT.md` — DB-002 ✅, DB-003 OPEN.
- `CHANGELOG.md` — 4 Fixed entries.
- `pyproject.toml` — 2.14.163 → 2.14.167.

## Test Status

- Full suite: **5881 passed, 4 skipped** (after the final ARITH-206 commit; run
  fresh after each of the two CRITICAL/world-reset changes — ARITH-114 and the
  two reset-handler edits).
- `ruff check` clean on all touched files.
- `gitnexus_detect_changes` run for BUY-010 and ARITH-114 (scope as expected);
  **skipped for DB-002/ARITH-206 — GitNexus MCP server disconnected mid-session**
  (scope verified via impact analysis + full suite instead, per AGENTS.md fallback).

## Next Steps

1. **`DB-003`** — dedicated audit of O-reset semantics vs ROM `reset_room`
   (`src/db.c:1773-1796`): confirm ROM intent for arg2/per-room, scope the fix,
   triage world-population fallout. This is the highest-value open reset gap.
2. Resolve the **ARITH-207/209** documentation contradiction.
3. **GitNexus MCP** was down at session end — a fresh session should confirm the
   server reconnects (CLI reindex alone won't restore MCP query tools) before
   relying on `gitnexus_impact` / `detect_changes`.
4. Otherwise continue the cross-file / divergence-class sweep (signed-math Layer B
   was productive this session; the remaining documented ARITH ❌ rows are either
   unreachable or contradictorily-documented — see Outstanding).
