# Session Summary — 2026-05-22 — INV-009 REGISTRY-DISCONNECT-CLEANUP

## Scope

Followed up the 2.8.33 NANNY-RECONNECT slice by investigating the
`character_registry` reconnect-duplication oddity flagged there. The
hypothesis ("stale pre-disconnect entry never removed") turned out to
have a second root cause as well: an in-session promote-from-bare-row
duplication. Fixed both, locked it in as a new cross-file invariant
(INV-009), and shipped as 2.8.34.

ROM source-of-truth: `src/comm.c:close_socket` + `src/nanny.c` keep
`char_list` to at most one entry per player name at a time. Reconnects
rebind via `check_reconnect`; clean quit removes via `extract_char`.

## Outcomes

### `INV-009` — ✅ ENFORCED — REGISTRY-DISCONNECT-CLEANUP

Two root causes, one invariant:

#### Cause A — in-session promote-from-bare-row duplication

- **Python**: `mud/account/account_manager.py:load_character`
- **Trigger**: during new-character creation, `_select_character`
  (`mud/net/connection.py:1737`) loads the level=0 bare-row Character
  written by `create_account` and appends it to `character_registry`.
  After the nanny menu finalises creation, the reload at
  `connection.py:1828` loads the promoted level=1 Character and
  appends it again — the bare-row entry is never removed.
- **Observed**: probe test showed two `Regista` entries after a single
  create+disconnect cycle: `(hit=20, level=0)` and `(hit=100, level=1)`.
- **Fix**: `load_character` now dedupes by `name` on append — drops any
  prior `character_registry` entry with the same name before adding the
  freshly-loaded one. This matches ROM's "one player object per name in
  char_list" invariant.

#### Cause B — cross-session leak on clean disconnect

- **Python**: `mud/net/connection.py` websocket + telnet disconnect `finally` blocks
- **Trigger**: the disconnect cleanup already saves the character,
  removes them from their room, and releases the account — effectively
  `do_quit` semantics — but never removes from `character_registry`.
- **Fix**: added registry removal inside the existing
  `if char: if not forced_disconnect:` block at both call sites.
  Forced disconnects (descriptor takeover via `_disconnect_session`)
  skip removal — the live Character transfers to the new descriptor.

#### Test

- `tests/integration/test_inv009_registry_disconnect_cleanup.py::test_inv009_registry_has_single_entry_after_disconnect_and_reconnect`
  reproduces both cases on the live websocket path and asserts:
  - 0 `Regista` entries after a clean disconnect.
  - exactly 1 `Regista` entry while a reconnected session is active.

#### Why advisor probe mattered

An earlier read suggested the bug might be "stale-only" (registry holds
a fresh-loaded entry but not the live one). Two interpretations had
**opposite** fixes — add-on-reconnect vs. remove-on-disconnect. The
probe (`[len(matches), [(c.hit, id(c)) for c in matches]]`) confirmed
duplication AND a within-session bare-row → promoted leak the cross-
session hypothesis would have missed. Without the probe, the fix would
have been incomplete.

## Files Modified

- `mud/account/account_manager.py` — `load_character` dedupes by name on append (Cause A).
- `mud/net/connection.py` — registry removal in both disconnect `finally` blocks (Cause B).
- `tests/integration/test_inv009_registry_disconnect_cleanup.py` — new enforcement test.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — added INV-009 row.
- `CHANGELOG.md` — `[2.8.34]` section with the fix detail.
- `pyproject.toml` — 2.8.33 → 2.8.34 (patch — bug fix).
- `docs/sessions/SESSION_STATUS.md` — refreshed pointer.

## Test Status

- Targeted (`tests/integration/test_inv009_registry_disconnect_cleanup.py`): 1/1 passing.
- Full suite (`./venv/bin/python -m pytest -q --timeout=60`): **4603 passed, 4 skipped** (+1 vs prior baseline 4602/4; zero regressions).
- `gitnexus analyze --skip-agents-md` re-ran at start of session (38,820 nodes, 64,808 edges). The 32 KB scope-extractor failures persist on the documented file list; `mud/account/account_manager.py` and `mud/net/connection.py` are both on it, so `gitnexus_impact` cannot be trusted on `load_character` / disconnect symbols. Verified via grep + full suite instead.

## Next Steps

1. **Plan Task 4 — save → reload → retained state on real server paths.**
   Still open. A natural next slice: write a Mode-B/Mode-C test that
   changes wimpy / prompt template / equipment in-session, disconnects,
   reconnects, and verifies the live state matches the in-session state
   pre-disconnect. Pattern: same as the NANNY-RECONNECT trio in 2.8.33.

2. **`log/orphaned_helps.txt` repo hygiene.** Still drifting on test
   runs. Likely best resolved as `git rm --cached` + `.gitignore` entry
   in a small future commit.

3. **Re-verify INV-003 / INV-009 interaction on the telnet path.** Only
   the websocket path is in the new test. The telnet disconnect block
   was patched in the same edit (identical structure), and the full
   suite covers telnet via `tests/test_telnet_server.py` — green — but a
   dedicated INV-009-on-telnet test would tighten the gate.
