# Session Summary — 2026-06-03 — INV-038 idle-timer reset on input

## Scope

Continued from `SESSION_STATUS.md` after INV-037. Active mode remains cross-file
invariants via probe-then-scope under the divergence-class completeness lens.
Chosen probe: affect-tick / `char_update` lifecycle edges around ROM
`src/update.c:char_update` and the player idle `ch->timer` mechanic.

## Probe Result

ROM tracks PC idleness with `ch->timer`:

- `src/update.c:char_update` increments it once per tick for **every**
  non-immortal PC, regardless of whether a descriptor is attached
  (`++ch->timer >= 12` → disappear into the void / limbo, lines 738-752).
- The autosave/autoquit second loop quits the character when the
  **pre-increment** timer exceeds 30 (`src/update.c:682-683` sets `ch_quit` at
  the top of the loop, *before* the increment).
- The timer is reset to 0 **only** on descriptor input (`src/comm.c:605`, before
  `interpret`), on reconnect (`src/comm.c:1856`), and on return-from-void
  (`src/comm.c:1918`) — never on the game tick.

The Python port diverged on two coupled points:

1. `mud/game_loop.py:char_update` reset `character.timer = 0` on **every** tick
   whenever a descriptor was present.
2. A tree-wide grep (`char.timer = 0` across all of `mud/`) confirmed there was
   **no** reset-on-input path anywhere — the only resets were the per-tick one,
   reconnect, void-return, and death.

Net effect: a connected player's idle timer never accumulated, so the
idle→void (≥12) and idle→autoquit (>30) anti-AFK mechanics were **dead for
everyone logged in**. Only linkdead (desc-less) characters idled out.

## Outcome — INV-038 (✅ ENFORCED, 2.12.86)

Filed `INV-038 IDLE-TIMER-RESET-ON-INPUT` in
`docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`.

Added `tests/integration/test_inv038_idle_timer_input_reset.py` (RED before fix):
- `test_connected_idle_player_climbs_timer_and_voids` — a connected (desc-present)
  PC accumulates idle time and disappears into the void at timer 12; past 30 it
  stays connected in limbo (autoquit deferred — see GL-035).
- `test_linkdead_idle_player_autoquits` — a link-dead (`desc is None`) PC past 30
  is auto-quit by `char_update`.
- `test_input_read_resets_idle_timer` — `_read_player_command` zeroes the playing
  character's timer when a line arrives (ROM `comm.c:605`).

The fix is intentionally two-part and coupled (a partial fix would void *active*
players):

- **`mud/game_loop.py:char_update`** — removed the per-tick `timer = 0` for
  connected PCs. Now increments the timer for every non-immortal PC, voids at
  `>= 12` (connected or not), and keeps autosave gated on `desc != NULL` +
  rotation slot. The pre-increment `> 30` autoquit (ROM `ch_quit`) is gated to
  link-dead (`desc is None`) characters only.
- **`mud/net/connection.py:_read_player_command`** — resets
  `session.character.timer` to 0 whenever `readline()` returns a line for a
  non-NPC playing character. This is the single shared chokepoint for telnet,
  SSH, and websocket flows (verified via `gitnexus_impact` upstream).

### Out-of-scope gaps/divergences filed

- **GL-035 (❌ OPEN)** — connected-player idle autoquit. ROM's `do_quit`
  synchronously `close_socket`s the descriptor; `_auto_quit_character` runs in the
  synchronous tick and cannot `await conn.close()`, so autoquit is gated to
  link-dead chars to avoid zombying the session (char removed from registry while
  the `handle_connection` coroutine stays parked on `readline`). Faithful closure
  needs a tick→connection disconnect signal that wakes the parked coroutine.
  **Surfaced by advisor review of the first INV-038 commit — the connected
  autoquit path was newly reachable and would have regressed into a zombie
  session.**
- **GL-034 (❌ OPEN)** — ROM auto-quits at most **one** idle PC per tick (`ch_quit`
  single pointer, last-in-`char_list`-wins); Python quits all candidates. Low
  practical impact, kept out of this narrow fix.

## Files Modified

- `mud/game_loop.py` — `char_update` idle-timer accumulation + pre-increment
  autoquit; autosave decoupled from the timer reset.
- `mud/net/connection.py` — `_read_player_command` resets the idle timer on input.
- `tests/integration/test_inv038_idle_timer_input_reset.py` — new RED/GREEN guard.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — new INV-038 row.
- `docs/parity/UPDATE_C_AUDIT.md` — new GL-034 row (OPEN).
- `CHANGELOG.md` — Added entry for INV-038.
- `pyproject.toml` — version `2.12.85` → `2.12.86`.
- `docs/sessions/SESSION_STATUS.md` — refreshed canonical pointer.

## Test Status

- `pytest -n0 tests/integration/test_inv038_idle_timer_input_reset.py` — failed
  RED before fix, 2 passed after.
- `pytest -n0 tests/test_game_loop.py tests/test_game_loop_order.py
  tests/test_char_update_rom_parity.py tests/test_player_conditions.py
  tests/test_networking_telnet.py tests/test_telnet_server.py` — 92 passed,
  1 skipped.
- Full suite: **5369 passed, 4 skipped** (347s parallel) — zero regressions.
- `ruff check mud/game_loop.py mud/net/connection.py
  tests/integration/test_inv038_idle_timer_input_reset.py` — clean.
- `gitnexus_impact` on `char_update` and `_read_player_command` — both LOW risk.
- `gitnexus_detect_changes(scope="all")` — LOW risk, 0 affected processes.

## Next Steps

Candidate next passes:

1. **GL-034** — match ROM's single-quit-per-tick autoquit fan-out (select only
   the last `character_registry` entry with pre-increment `timer > 30`). Small,
   self-contained `/rom-gap-closer` candidate.
2. `diff_harness` Hypothesis widening
   (`tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md`) — highest-ceiling,
   multi-day, the only enumeration-independent path to *unknown* divergences.
3. New cross-INV probe area — another affect-tick or group/follower-chain edge.
4. Housekeeping: INV tracker consolidation (now 31 active rows, past the ~20
   soft cap).
