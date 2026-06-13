# Session Summary — 2026-06-12 — xdist flake fixes (test-isolation hardening)

## Scope

Continuation of the cross-file-invariants pass. The per-file audit tracker is
exhausted (only deferred track-only DB2 rows remain), and the two known xdist
flakes were the highest-value outstanding items in `SESSION_STATUS.md`. Both were
diagnosed to root cause and fixed. **Neither is a production parity bug** — both
are test-isolation defects (a test reading shared global state it didn't isolate,
and a test pinning the wrong RNG primitive).

---

## Outcomes

### `test_hpcnt_fires_exactly_once_per_violence_tick` — ✅ FIXED (2.14.23)

- **Test**: `tests/integration/test_hpcnt_once_per_pulse.py`
- **Root cause**: `violence_tick` walks the **global** `character_registry`
  (`mud/game_loop.py:1590`, `for ch in list(reversed(character_registry))`). The
  integration conftest seeds RNG but does **not** isolate `character_registry`.
  A fighting NPC leaked by a sibling test on the same xdist worker fired its own
  `mp_hprct_trigger`, inflating `len(calls)` past the asserted 1.
- **Fix**: snapshot and replace the registry contents **in place**
  (`character_registry[:] = [attacker, victim]`) so the pulse sees only the
  test's two actors, restoring `character_registry[:] = saved_registry` in the
  `finally`. In-place mutation (not rebind) matters — `violence_tick` holds the
  list by reference via module import.

### `test_ac_clamping_for_negative_values` — ✅ FIXED (2.14.23)

- **Test**: `tests/test_combat_rom_parity.py`
- **Root cause**: ROM's to-hit roll is `number_bits(5)` (`src/fight.c:508`,
  `while ((diceroll = number_bits(5)) >= 20)`), **not** `number_percent`, and a
  natural `diceroll == 0` is an automatic miss regardless of hitroll/AC
  (`src/fight.c:510`, mirrored at `mud/combat/engine.py:598`). The test pinned
  `number_percent`, which has no effect on the d20 to-hit decision, so leaked
  global RNG state landed on `diceroll == 0` ~1/20 runs and flaked the
  `"miss" not in result` assertion under `-n auto`.
- **Fix**: pin `mud.utils.rng_mm.number_bits` to 19 (the auto-hit roll —
  `diceroll != 19` guard means 19 always hits) for a deterministic hit.
- **Diagnosis proof**: a standalone repro with `number_bits` pinned to 0 yields
  `"You miss Victim."`; pinned to 19 yields `"You scratch Victim."`.

## Files Modified

- `tests/integration/test_hpcnt_once_per_pulse.py` — registry isolation
- `tests/test_combat_rom_parity.py` — pin `number_bits` not `number_percent`
- `CHANGELOG.md` — `[2.14.23]` Fixed entries
- `pyproject.toml` — 2.14.22 → 2.14.23

## Test Status

- `pytest -n0 tests/integration/test_hpcnt_once_per_pulse.py` — 2/2 passing
- `pytest -n0 tests/test_combat_rom_parity.py` — 10/10; `-n auto` — 10/10
- Combat-area parallel sweep (`-k "hpcnt or violence or combat or fight"`) —
  244 passed, 1 skipped
- `ruff check` on changed files — clean

### `MOBCMD-019` — `mob remember <unresolved>` left a stale mprog_target — ✅ FIXED (2.14.24)

- **Python**: `mud/mob_cmds.py:1270-1277` (`do_mpremember`)
- **ROM C**: `src/mob_cmds.c:1155-1164`
- **Gap**: ROM assigns `ch->mprog_target = get_char_world(ch, arg)`
  **unconditionally** for a non-empty argument, so a failed lookup (NULL) clears
  the remembered target. Python early-returned on a failed lookup, leaving a
  stale previous target — `$q`/`$Q` mobprog substitution codes would then
  resolve to a departed character.
- **Fix**: assign `_find_char_world(target_name)` unconditionally for non-empty
  args; the empty-arg `bug()` branch still leaves the target untouched.
- **Tests**: `tests/integration/test_mob_cmds_remember.py` (4 new, incl. the
  failing-before clears-stale-target case). mob_cmds + mobprog suites: 91/91.
- **Sibling sweep**: grepped all `get_char_world`/`get_char_room`/`get_obj_here`
  assignments in `src/mob_cmds.c` — line 1160 is the only one assigning to a
  *persistent* field; every other assigns to a local and guard-returns on NULL
  (which Python mirrors correctly). No sibling divergences in this file.

### `INV-047` — `extract_char` mprog_target quirk (single-path) — ✅ ENFORCED (2.14.25)

- **Python**: `mud/mob_cmds.py:_extract_character`
- **ROM C**: `src/handler.c:2151-2157`
- **Gap**: ROM's `extract_char` `char_list` walk nullifies two single-target
  pointers — `reply` (already mirrored) and `mprog_target`. The latter is a
  faithfully-replicated 2.4b6 quirk: it tests `ch->mprog_target == wch` (the
  *extracted* char's target) and clears `wch->mprog_target` (that target's OWN
  pointer) — so it wipes the remembered target of whoever the extracted char was
  targeting and does NOT clear mobs pointing AT the extracted char. Python left
  it a `# would go here if needed` TODO.
- **Fix**: mirror the buggy line verbatim (not the "corrected"
  `wch->mprog_target == ch` form).
- **Tests**: `tests/integration/test_inv047_extract_clears_mprog_target.py` (2 —
  pins both halves).

### `INV-047` (multi-path) — cleanup on every extract path — ✅ ENFORCED (2.14.26)

- **Python**: `mud/combat/death.py:clear_extract_target_refs` (new shared helper);
  wired into `mob_cmds.py:_extract_character`,
  `game_loop.py:_auto_quit_character` (link-dead/void-quit leg), and
  `connection.py:_disconnect_extract_cleanup` (telnet + websocket clean-disconnect).
- **ROM C**: `src/handler.c:2151-2157` (one `extract_char`).
- **Gap**: ROM has a single `extract_char`; the Python port split extraction
  across call sites, so the PC-quit and socket-disconnect legs leaked dangling
  `reply`/`mprog_target` pointers — the same multi-path class INV-020 closed for
  `nuke_pets`/`die_follower`. The single-path 2.14.25 fix only covered
  `_extract_character`.
- **Fix**: extract the cleanup into `clear_extract_target_refs` and invoke it
  from all three extract paths (ROM loop-then-unlink order preserved).
- **Tests**: `tests/integration/test_inv047_extract_paths_clear_refs.py` (4 —
  quit leg ×2 + disconnect leg ×2). Broader extract/death suites: 38/38.

### `INV-020` step (iv) — `stop_fighting(both=True)` on quit + disconnect legs — ✅ ENFORCED (2.14.27)

- **Python**: `mud/game_loop.py:_auto_quit_character`,
  `mud/net/connection.py:_disconnect_extract_cleanup`.
- **ROM C**: `src/handler.c:2121` (final step of the `extract_char` cleanup chain).
- **Gap**: ROM's `extract_char` ends with `stop_fighting(ch, TRUE)` — `fBoth`
  clears `fighting` on the extracted char AND every char fighting it. The
  mob-extract leg (`_extract_character`) already did this, but the two PC-extract
  legs (link-dead void-quit, socket disconnect) ran only steps i–iii + the
  INV-047 ref-clear, leaving a mob with a dangling `fighting` pointer at the
  unlinked PC — dereferenced on the next combat tick. Found by walking ROM's
  4-step chain against each Python extract path (the same multi-path audit that
  produced INV-047); INV-020's own row enumerated step (iv) but the quit/disconnect
  legs silently omitted it.
- **Fix**: both legs now call `stop_fighting(char, both=True)` after the INV-047
  ref-clear, before the room/registry unlink (ROM loop-then-unlink order). All
  four extract legs now run the full chain.
- **Tests**: `tests/integration/test_inv020_extract_quit_cleanup.py` (+2:
  `test_void_quit_stops_attackers_fighting`,
  `test_disconnect_stops_attackers_fighting`; file now 6/6). Targeted
  extract/fighting regression: 56/56.

## Next Steps

Cross-file invariants remains the active pass. Remaining candidate probes:

1. **Mob memory / hunt** — `src/fight.c` ATTACK_BACK + the hunt/track loop vs the
   Python AI tick (not yet probed).
2. **Position-transition edges** — `update_pos` / `stop_fighting` ordering across
   damage, sleep, rest, and death (cross-INV candidate).

Confirmed-faithful (do not re-probe without new evidence): weather/time fan-out,
`update_handler` pulse cadence (locked by `tests/test_game_loop_order.py` +
`tests/integration/test_weather_time.py`).
