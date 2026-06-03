# Session Summary — 2026-06-03 — cancellation dispel roll + infravision actor + idle autoquit (GL-035/034)

## Scope

Continued from `SESSION_STATUS.md` after the INV-038 idle-timer session. Closed
the one remaining open engine bug (`MAGIC-009`, the cancellation handoff) via
`/rom-gap-closer`, then — on user request — addressed the three gaps surfaced by
that thread: `MAGIC-015` (infravision actor), `GL-035` (connected idle autoquit),
and `GL-034` (one-per-tick autoquit fan-out). Five commits, pushed to `master`.

## Outcomes

### `MAGIC-009` — ✅ FIXED (2.12.92)

- **Python**: `mud/skills/handlers.py:1868` (`cancellation`) + inner `_cancel_effect`
- **ROM C**: `src/magic.c:1033-1203` (`spell_cancellation`) + `:243-284` (`saves_dispel`/`check_dispel`)
- **Gap**: cancellation stripped **every** spell effect unconditionally, ignoring
  the caster `level` — a level-1 caster reliably cancelled a level-50 effect.
- **Fix**: `_cancel_effect` now delegates to the already-ROM-faithful
  `check_dispel(level, target, effect_name)` (the proven `dispel_magic`/
  `cure_blindness`/`slow` pattern), so each effect rolls
  `saves_dispel(dis_level, af.level, af.duration)` and can fail (decrementing
  `af.level`). The "victim gets NO save" ROM comment refers only to the absent
  *upfront wholesale* `saves_spell`, not the per-effect rolls (the original
  misread). Duplicate wear-off send dropped (`check_dispel` already sends it).
- **Tests**: `tests/test_spell_cancellation_rom_parity.py::test_cancellation_respects_saves_dispel`
  (RED before fix); 3 false-parity legacy tests realigned to ROM via RNG control;
  3 INV-025 PERS-masking tests force the dispel to succeed. `dispel_magic`
  unaffected.

### `MAGIC-015` — ✅ FIXED (2.12.93)

- **Python**: `mud/skills/handlers.py:5573` (`infravision`)
- **ROM C**: `src/magic.c:3583-3609` (`spell_infravision`, line 3598)
- **Gap**: room line passed `target` as the `$n` actor with `exclude=target`;
  ROM passes `ch` (the caster) and `TO_ROOM` excludes only the caster — so a
  cross-cast (`caster != victim`, valid for `TAR_CHAR_DEFENSIVE`) rendered the
  victim's name where ROM shows the caster's, and wrongly excluded the victim.
- **Fix**: `act_to_room(room, "$n's eyes glow red.", caster, exclude=caster)`,
  broadcast before the victim's personal line (ROM order). Self-cast unchanged.
  Also resolved a pre-existing **ID collision** — the infravision gap had been
  duplicate-numbered `MAGIC-009`; renumbered `MAGIC-015`.
- **Tests**: `tests/integration/test_magic015_infravision_caster_actor.py` (2).

### `GL-035` — ✅ FIXED (2.12.94)

- **Python**: `mud/game_loop.py` `_auto_quit_character` + `char_update` + new `_schedule_connection_close`
- **ROM C**: `src/update.c:682-683`,`897-900` (`ch_quit` → `do_quit`); `src/act_comm.c:1462` (`do_quit`)
- **Gap**: INV-038 gated autoquit to link-dead (`desc is None`) chars because the
  synchronous tick cannot `await conn.close()`; a connected idler voided to limbo
  at `timer >= 12` then parked there forever.
- **Fix**: the autoquit gate drops the `desc is None` restriction; a connected
  idler now has its live connection closed via a scheduled
  `asyncio.create_task(conn.close())` (fire-and-forget, `MESSAGE_DELIVERY`
  pattern) — the parked `readline` returns `None` so the playing loop's `finally`
  runs the full ROM `do_quit`-equivalent teardown. The tick does not also extract
  (avoids a double-remove race); link-dead idlers keep the synchronous extract.
- **Tests**: `test_connected_idle_player_autoquits_via_async_close` (fake conn,
  real loop) + `test_server_side_close_wakes_parked_readline` (real `TelnetStream`
  over a `socket.socketpair` — **proves** the EOF wake-chain, not assumes it).

### `GL-034` — ✅ FIXED (2.12.95; ordering corrected 2.12.96)

- **Python**: `mud/game_loop.py:char_update`
- **ROM C**: `src/update.c:665-683`,`897-900` (`ch_quit`); `src/nanny.c:757-758`, `src/db.c:2256-2257` (char_list prepend)
- **Gap**: Python collected every `timer > 30` char and quit them all the same
  tick; ROM's `ch_quit` is a single pointer → at most one autoquit per tick.
- **Fix**: track a single `autoquit_candidate` (not a list). **Ordering
  corrected post-advisor-review**: ROM *prepends* to `char_list`, so walking
  head→tail lands `ch_quit` on the **oldest** idle char; `character_registry` is
  append-ordered (oldest first), so the selection is **first-wins**, not
  last-wins (last-wins would quit the newest, reversed from ROM).
- **Tests**: `test_only_one_idle_player_autoquits_per_tick` (oldest/first quits
  this tick, the newer next tick).

### Out-of-scope gap filed

- **`GL-037` (❌ OPEN)** — the GL-035 close-transport path runs the clean-disconnect
  `finally`, which does **not** replicate ROM `do_quit`'s "Alas, all good things
  must come to an end." (TO_CHAR) / "$n has left the game." (TO_ROOM) messaging.
  Low impact (the quitter is idle/gone; the room broadcast would land in limbo).
  Filed in `UPDATE_C_AUDIT.md`; surfaced by advisor review while closing GL-035.

## Files Modified

- `mud/skills/handlers.py` — `cancellation`/`_cancel_effect` → `check_dispel`; `infravision` room actor → caster.
- `mud/game_loop.py` — `char_update` autoquit gate + single first-wins candidate; `_auto_quit_character` connected/link-dead branch; new `_schedule_connection_close`; `import asyncio`.
- `tests/test_spell_cancellation_rom_parity.py` — RED test + 4 legacy realignments (RNG-controlled).
- `tests/integration/test_inv025_cancellation_act_pers_masking.py` — force dispel success (3 masking tests).
- `tests/integration/test_magic015_infravision_caster_actor.py` — new (2).
- `tests/integration/test_inv038_idle_timer_input_reset.py` — GL-035/034 tests + wake-chain proof; realigned the connected-idler void test.
- `docs/parity/MAGIC_C_AUDIT.md` — flipped `MAGIC-009`, `MAGIC-015` → ✅; renumbered the collision.
- `docs/parity/UPDATE_C_AUDIT.md` — flipped `GL-035`, `GL-034` → ✅; filed `GL-037` (OPEN).
- `CHANGELOG.md` — Fixed entries for MAGIC-009/015, GL-034/035.
- `pyproject.toml` — `2.12.91` → `2.12.96`.

## Test Status

- Per-area suites green at each step (dispel/cancellation 52; infravision 7; inv038 6).
- Full suite re-run after each gap: final **5379 passed, 4 skipped** (~159s parallel) — zero regressions.
- `ruff check .` + `ruff format --check .` clean repo-wide; all 5 pre-commit hooks pass.
- `gitnexus_impact` (`cancellation`, `_auto_quit_character`) — LOW; `gitnexus_detect_changes` — scope-clean, 0 affected processes.
- Index reindexed after push (44,793 nodes / 83,938 edges).

## Next Steps

The per-file audit tracker has no ⚠️/❌ rows; cross-file invariants + the
divergence-class roster remain the active pass. Concrete candidates:

1. **`GL-037`** — emit ROM `do_quit`'s farewell/room messaging on the idle-autoquit
   path specifically (not the generic socket-drop disconnect). Small `/rom-gap-closer`.
2. `diff_harness` Hypothesis widening (`tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md`)
   — the only enumeration-independent path to *unknown* divergences.
3. New cross-INV probe (affect-tick / group-follower / position-transition edge).
4. Housekeeping: INV tracker consolidation (31 active rows, past the ~20 soft cap).
