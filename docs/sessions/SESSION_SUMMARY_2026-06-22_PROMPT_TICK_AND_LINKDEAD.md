# Session Summary — 2026-06-22 — Prompt-after-tick (INV-053) + net-death link-dead (class 14)

## Scope

Started from a user question about connection handling: are HP/mana/move updates
on game ticks pushed to the client, or only sent when the client sends text — and
how did the original ROM telnet handle it? That investigation surfaced two real
divergences, both closed this session:

1. **INV-053** — the prompt (which carries HP/mana/move) was not re-emitted after
   tick-generated output, so combat/spell HP changes didn't reach an idle PC's
   prompt line until their next command.
2. **Divergence-class 14** — a genuine socket drop removed the character
   immediately (`do_quit` semantics) instead of keeping it **link-dead** in the
   world like ROM `close_socket`. The user then asked to scope and address it.

## Outcomes

### `INV-053` — ✅ ENFORCED (PROMPT-AFTER-TICK-OUTPUT)

- **ROM C**: `src/comm.c:868-883`, `1376-1377` — `game_loop_unix` re-appends
  `bust_a_prompt` on every pulse that produced output for a descriptor
  (`d->fcommand || d->outtop > 0`). `char_update` regen is silent
  (`src/update.c:698-711`), so idle regen correctly emits no prompt.
- **Python**: `mud/game_loop.py:async_game_loop` wraps `game_tick()` in
  `begin_tick_output()/end_tick_output()`; the delivery chokepoints
  (`mud/utils/messaging.py:push_message`, `mud/net/protocol.py:broadcast_room`/
  `broadcast_global`) mark recipients via `note_tick_delivery`; after the tick,
  `mud/net/connection.py:schedule_tick_prompts` emits one fresh prompt per
  marked, still-connected PC (queued after the message tasks).
- **Fix**: tick output → fresh prompt; silent regen → no prompt (parity-correct).
- **Tests**: `tests/integration/test_inv053_prompt_after_tick_output.py` (4) — green.
- **Commit**: `8baa7662`. Filed as INV-053 in the cross-file tracker.

### `Divergence-class 14` — ✅ CLOSED (net-death link-dead lifecycle)

- **ROM C**: `src/comm.c:1075-1093` (`close_socket` keeps a `CON_PLAYING` char in
  `char_list` with `ch->desc = NULL` on a drop), `src/comm.c:1836` +
  `src/nanny.c:281` (`check_reconnect` rebinds **after** the password is
  verified — `nanny.c:270-274` rejects wrong passwords first, so no credential
  bypass), `src/update.c:738/682` (void@12 min / autoquit@30 min).
- **Python**:
  - `mud/net/connection.py:_finalize_disconnect` routes a disconnect three ways —
    forced takeover (transfer, unchanged), `_quit_requested` (full extract via
    `_disconnect_extract`, prior behavior), and a genuine link drop to
    `_disconnect_linkdead` (lost-link broadcast + `WIZ_LINKS` wiznet, null
    `desc`/`connection`, set `Character.link_dead`, release account marker, KEEP
    char in room + `character_registry`). Both `handle_connection*` finally
    blocks delegate to it.
  - `mud/net/connection.py:_find_linkdead_character` + the rebind branch in
    `_select_character` rebind a returning player to the lingering instance and
    clear `link_dead`.
  - `mud/game_loop.py:_auto_quit_character` sets `_quit_requested` before
    scheduling the connected close so idle-autoquit extracts (not lingers).
  - New `mud/models/character.py:Character.link_dead` field (transient, never
    persisted).
- **Net effect**: link-dead chars are now idled by `char_update`
  (void@12/autoquit@30 — the INV-038/`_auto_quit_character` link-dead leg is now
  production-reachable), attackable while away, and reconnect rebinds the same
  instance (combat/position/transient affects preserved).
- **Tests**: `tests/integration/test_class14_linkdead_lifecycle.py` (6) +
  rewritten `tests/integration/test_inv009_registry_disconnect_cleanup.py`
  (link drop → one lingering link-dead entry; reconnect → same instance; no
  duplicate — INV-009's no-duplicate invariant preserved via the new mechanism).
- **Commits**: `8aab0cef` (rebind machinery + field, inert) and `3681c40b`
  (linger + reconnect + autoquit flag + test reconciliation + docs).

### Bug caught during verification (would have shipped)

- The first rebind heuristic matched any `desc is None` char in the registry —
  too broad. The registry transiently holds `desc=None` chars that are NOT
  ROM-link-dead (a just-quit char mid-teardown, the ANSI-persistence round-trip
  in `test_account_auth`), so the rebind wrongly intercepted their next login and
  hung. Fixed by gating on the explicit `link_dead` flag (set only by the linger
  path), which also makes "link-dead" a precise state instead of a guess.

## Files Modified

- `mud/game_loop.py` — INV-053 tick-output wrapping + `schedule_tick_prompts`
  call; class-14 autoquit `_quit_requested` flag.
- `mud/utils/messaging.py` — INV-053 tick-output tracking
  (`begin/end_tick_output`, `note_tick_delivery`, `drain_prompt_dirty`,
  `reset_prompt_dirty`).
- `mud/net/protocol.py` — INV-053 `note_tick_delivery` on `broadcast_room`/
  `broadcast_global`.
- `mud/net/connection.py` — INV-053 `schedule_tick_prompts`/`_send_tick_prompt`;
  class-14 `_finalize_disconnect`/`_disconnect_linkdead`/`_disconnect_extract`,
  `_find_linkdead_character`, `_select_character` rebind branch, both finally
  blocks delegated.
- `mud/models/character.py` — `link_dead` field.
- `tests/conftest.py` — autouse `_reset_tick_prompt_state` (INV-053).
- `tests/integration/test_inv053_prompt_after_tick_output.py` — new (4).
- `tests/integration/test_class14_linkdead_lifecycle.py` — new (6).
- `tests/integration/test_inv009_registry_disconnect_cleanup.py` — rewritten for
  link-dead.
- `tests/integration/test_nanny_saveload_runtime_path.py`,
  `tests/test_websocket_server.py`, `tests/test_account_auth.py` — 9
  reconnect/disk-round-trip tests now `quit` explicitly between sessions
  (ROM-faithful + removes a same-event-loop-tick reconnect race).
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-053 row added; INV-009
  mechanism pointer updated.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — class 14 row (filed, then CLOSED).
- `CHANGELOG.md` — Added (class 14) / Fixed (INV-053) / Documented entries.
- `pyproject.toml` — 2.14.208 → 2.14.211.

## Test Status

- Full suite: **6034 passed, 4 skipped** (clean gate run, ~5 min).
- `ruff check` / `ruff format` — clean on all touched files.
- Note: `gitnexus_detect_changes` could not run — the GitNexus MCP server
  disconnected mid-session. Change scope was verified via `git status` (only the
  expected files) and the green full suite; the CLI reindex
  (`npx gitnexus analyze --skip-agents-md`) was re-run to refresh the on-disk
  graph.

## Known limitation (documented, not fixed)

Class-14 rebind requires the char to be flagged `link_dead`, which is set by the
*async* disconnect `finally`. A client (or test) reconnecting within the **same
event-loop tick** — before that teardown runs — races among three
`_select_character` outcomes (takeover-prompt / rebind / fresh-load). Production
is safe (the web client backs off ≥1 s before reconnecting). Reconnect-flavor
tests were made deterministic with an explicit `quit`. Serializing
disconnect/login on a per-name lock is separate hardening, deliberately out of
scope (recorded in the roster class-14 row).

## Next Steps

- Optional class-14 hardening: a per-name disconnect/login lock to remove the
  same-tick reconnect race entirely (would let reconnect tests drop the explicit
  `quit` if ever desired). Low priority — production is unaffected.
- Continue cross-file invariants / differential-harness widening (the prior
  active pass): the death-lifecycle probes from the earlier 2026-06-22 session
  (`PLR_AUTOSAC` after death, `PLR_AUTOSPLIT`) remain open.
