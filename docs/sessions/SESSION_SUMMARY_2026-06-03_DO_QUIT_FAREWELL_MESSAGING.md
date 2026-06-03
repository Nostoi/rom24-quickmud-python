# Session Summary — 2026-06-03 — do_quit farewell messaging (GL-037 + QUIT-001)

## Scope

Picked up from `SESSION_STATUS.md`'s next-task #1: close **GL-037**, the small
idle-autoquit messaging gap surfaced by the prior session while closing GL-035.
Closing it (and reading the interactive `do_quit` for the canonical farewell
string) immediately surfaced a second, related divergence — the interactive
`do_quit` returns the wrong farewell — which was filed as **QUIT-001** and then
closed in the same session. Both are `do_quit` TO_CHAR/TO_ROOM messaging
parity, version `2.12.96 → 2.12.97`.

## Outcomes

### `GL-037` — ✅ FIXED (2.12.97)

- **Python**: `mud/game_loop.py:_auto_quit_character`
- **ROM C**: `src/act_comm.c:1481-1482` (`do_quit` farewell + `act(TO_ROOM)`)
- **Gap**: GL-037 — idle autoquit of a *connected* player did not emit ROM
  `do_quit`'s "Alas, all good things must come to an end." (TO_CHAR) nor
  broadcast "$n has left the game." (TO_ROOM). GL-035 (2.12.94) routes the
  connected idler's teardown through the clean-disconnect `finally`
  (`mud/net/connection.py:2037`), which sends neither line.
- **Fix**: `_auto_quit_character` now emits both ROM lines at the **top** of the
  function — before the connected/link-dead branch and before scheduling the
  transport close — so the TO_CHAR send task is queued ahead of the close and
  the TO_ROOM broadcast lands in the current (limbo) room. On the link-dead leg
  the TO_CHAR routes to the discarded mailbox (no socket), a harmless no-op
  equivalent to ROM `send_to_char`'s `desc==NULL` short-circuit. Verified no
  double-broadcast: the clean-disconnect `finally` sends neither line.
- **Tests**: `tests/integration/test_inv038_idle_timer_input_reset.py::test_connected_idle_autoquit_emits_do_quit_messaging`
  (recording fake conn asserts "Alas…" reached the quitter; mailbox witness in
  limbo asserts "Idler has left the game."). Also added `send_line` to the
  existing GL-035 test's `_FakeConn` so the new emission's fire-and-forget send
  task doesn't raise. File: 7/7 passing.

### `QUIT-001` — ✅ FIXED (2.12.97) — surfaced this session

- **Python**: `mud/commands/session.py:do_quit`
- **ROM C**: `src/act_comm.c:1481` (`send_to_char("Alas, all good things must come to an end.")`)
- **Gap**: QUIT-001 — the *interactive* `do_quit` returned "May your travels be
  safe." to the quitter instead of ROM's "Alas, all good things must come to an
  end." The TO_ROOM "$n has left the game." broadcast was already correct. The
  `ACT_COMM_C_AUDIT.md` do_quit row had wrongly marked this ✅ (a false-✅
  caught by reading ROM C, per the AGENTS.md re-verify rule).
- **Fix**: `do_quit` now returns the ROM line (delivered as the command result
  before the connection handler tears down the descriptor).
- **Tests**: `tests/integration/test_quit_broadcasts.py::test_quit_broadcasts_to_room`
  — the existing test had codified the divergent string (a test asserting
  non-ROM behavior is a test bug per AGENTS.md) and was corrected to assert the
  ROM farewell. File: 3/3 passing. Impact LOW (only caller `do_delete` discards
  the return).

## Files Modified

- `mud/game_loop.py` — `_auto_quit_character` emits ROM `do_quit` TO_CHAR+TO_ROOM (GL-037)
- `mud/commands/session.py` — `do_quit` returns ROM "Alas…" farewell (QUIT-001)
- `tests/integration/test_inv038_idle_timer_input_reset.py` — new GL-037 test; `_FakeConn.send_line` added
- `tests/integration/test_quit_broadcasts.py` — assert ROM farewell string (QUIT-001)
- `docs/parity/UPDATE_C_AUDIT.md` — GL-037 row → ✅ FIXED (2.12.97)
- `docs/parity/ACT_COMM_C_AUDIT.md` — added QUIT-001 row (✅ FIXED), corrected the do_quit false-✅
- `CHANGELOG.md` — added GL-037 + QUIT-001 Fixed entries
- `pyproject.toml` — 2.12.96 → 2.12.97

## Test Status

- `tests/integration/test_inv038_idle_timer_input_reset.py` — 7/7
- `tests/integration/test_quit_broadcasts.py` — 3/3
- Full suite: **5380 passed, 4 skipped** (was 5379; +1 new test)
- `ruff check .` + `ruff format --check .` clean repo-wide; 5 pre-commit hooks pass
- `test_all_commands.py` — 1 pre-existing attribute error (`exits` /
  `SimpleNamespace` stub lacks `exit_info`), unrelated to this session

## Commits

- `de870f61` fix(parity): UPDATE_C_AUDIT:GL-037 — idle autoquit emits do_quit farewell + room departure
- `a6bed27c` fix(parity): ACT_COMM_C:QUIT-001 — interactive do_quit sends ROM "Alas…" farewell

Not pushed (master, local). Push requires explicit user request.

## Next Steps

No open engine bug remains. Per-file audit tracker still has no ⚠️/❌ rows, so
cross-file invariants + the divergence-class roster (`/rom-divergence-sweep`)
remain the active passes. Candidates (carried forward from prior status):

1. `diff_harness` Hypothesis widening — the only enumeration-independent path to
   *unknown* divergences.
2. New cross-INV probe (affect-tick / group-follower / position-transition edge).
3. Housekeeping: INV tracker consolidation (31 rows, past the ~20 soft cap).

## Outstanding

- None newly open this session — QUIT-001 (surfaced mid-session) was closed in
  the same session. GL-037 (the prior session's follow-up) is closed.
