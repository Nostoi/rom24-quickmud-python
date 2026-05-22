# Session Summary — 2026-05-22 — `nanny.c` reconnect runtime-path parity (`score` / `look` / prompt)

## Scope

Continued Plan Task 4 (parity trust rebuild) by closing the **remaining
post-reconnect runtime-path verification** bullets on the live websocket
path. Prior work had asserted DB row state + password prompt on reconnect
but did not lock in what the player actually sees on the first command
after re-entering the game. This session adds three transcript-parity
regressions covering `score`, `look`, and the initial in-game prompt.

ROM source-of-truth: `src/act_info.c:1037-1116` (do_look),
`src/act_info.c:1477-1507` (do_score), `src/comm.c:1437-1443` (default
prompt), all driven via `src/nanny.c:760` (reset_char + char_to_room at
end of CON_READ_MOTD). Comparisons follow Mode B (transcript
differential) per `docs/superpowers/specs/2026-05-21-rom-differential-testing-design.md`.

## Outcomes

### `NANNY-RECONNECT-001` — ✅ VERIFIED — `score` after reconnect

- **Python**: `mud/commands/session.py:do_score` + `mud/net/connection.py:apply_login_state_refresh`
- **ROM C**: `src/act_info.c:1477-1507`, invoked after `reset_char` from `src/nanny.c:760`
- **Gap**: previously, only DB row + password prompt were exercised on the live websocket reconnect path. No transcript assertion that title / race / sex / class / resources lines came out ROM-exact on the first command after re-entry.
- **Fix**: regression test added; no implementation drift found.
- **Test**: `tests/test_websocket_server.py::test_websocket_reconnect_score_matches_rom_act_info_lines` asserts
  - ROM title line: `"You are <name> the Apprentice of Magic, level 1, N years old (M hours)."`
  - ROM race/sex/class line: `"Race: elf  Sex: male  Class: mage"`
  - Hit/mana/move at full (NANNY-014 `reset_char` restored from `perm_*`).
- **Commit**: `ba79d82`

### `NANNY-RECONNECT-002` — ✅ VERIFIED — `look` after reconnect

- **Python**: `mud/commands/inspection.py:do_look` + `mud/models/room.py`
- **ROM C**: `src/act_info.c:1037-1116`, invoked via `char_to_room` at end of `CON_READ_MOTD`
- **Gap**: no live websocket assertion that the initial `look` after reconnect rendered from the canonical loaded room (vs. a stale pre-disconnect snapshot).
- **Fix**: regression test added; no implementation drift found.
- **Test**: `tests/test_websocket_server.py::test_websocket_reconnect_look_matches_room_registry_not_cached_snapshot` reconnects, snapshots the live `character_registry` entry's `room.name` and first non-empty description line, then sends `look` and asserts both appear in the live transcript.
- **Commit**: `6622775`

### `NANNY-RECONNECT-003` — ✅ VERIFIED — first prompt after reconnect

- **Python**: `mud/utils/prompt.py:_bust_default_prompt` + `mud/net/connection.py:apply_login_state_refresh`
- **ROM C**: `src/comm.c:1437-1443` (default `"{p<%dhp %dm %dmv>{x %s"`) via `src/nanny.c:760` (reset_char on login)
- **Gap**: no assertion that the first in-game prompt after reconnect reflected the loaded character's hp/mana/move (vs. 0/0/0 defaults or stale snapshot).
- **Fix**: regression test added; no implementation drift found in the prompt path.
- **Test**: `tests/test_websocket_server.py::test_websocket_reconnect_initial_prompt_reflects_loaded_resources` captures the first post-MOTD prompt, then sends `score` on the same session and parses live hit/mana/move from the ROM resources line. Asserts (a) prompt has ROM `<Nhp Nm Nmv>` shape (not defaults), (b) prompt values equal what `score` reports on the same session (self-consistent), (c) live `hit == max_hit` after reconnect (NANNY-014 `reset_char` ran).
- **Commit**: `600d9d5`

## Files Modified

- `tests/test_websocket_server.py` — three transcript-parity tests for NANNY-RECONNECT-001..003
- `docs/parity/NANNY_C_AUDIT.md` — added rows for NANNY-RECONNECT-001..003 (all ✅ VERIFIED)
- `CHANGELOG.md` — `[Unreleased]` entries for the three slices
- `pyproject.toml` — version bump (handoff commit)
- `docs/sessions/SESSION_STATUS.md` — refreshed pointer (handoff commit)

## Test Status

- Targeted (`tests/test_websocket_server.py`): all reconnect tests green.
- Full suite (`./venv/bin/python -m pytest -q --timeout=60`): **4602 passed, 4 skipped** (+3 vs. prior baseline 4599/4; zero regressions).
- `gitnexus_detect_changes()` not re-run — the GitNexus index has been stale since commit `0dd803e` (still warned by the PostToolUse hook). All three commits touch only `tests/`, `docs/`, and `CHANGELOG.md` (no production code changes), so the typical impact-analysis surface does not apply. Re-index with `npx gitnexus analyze --skip-agents-md` before the next session relies on `gitnexus_impact`.

## Follow-ups for the next session

1. **Character registry hygiene (probable bug)**. While debugging
   NANNY-RECONNECT-003, an earlier iteration of the test compared the
   first post-MOTD prompt (which rendered `100hp`) against the result of
   `next(c for c in character_registry if c.name == "Prompto")` (which
   reported `hit=20`). The two readings disagreed for `hit` only;
   `mana`/`move` matched. Hypothesis: the pre-disconnect Character
   object is still in `character_registry` when the reconnect session
   binds a freshly-loaded one, and the name lookup is winning the stale
   entry. Worth a dedicated audit slice — likely an INV-NNN
   cross-file invariant ("REGISTRY-MEMBERSHIP" already exists; this may
   warrant a new "REGISTRY-RECONNECT-DEDUP"). The current test sidesteps
   the issue by reading live values via `score` on the same session;
   that's correct for the transcript-parity assertion, but does not fix
   the underlying registry duplication.

2. **Plan Task 4 — save → reload → retained state on real server paths**.
   Still open. Existing helper tests cover this in isolation; runtime-path
   coverage on the live websocket reconnect is the remaining bullet.

3. **`gitnexus analyze --skip-agents-md`** before the next session that
   needs `gitnexus_impact` or `gitnexus_detect_changes`.

4. **`log/orphaned_helps.txt`** keeps accumulating runtime noise. Tracked
   in git; consider `git rm --cached` + ignore in a future hygiene
   commit. Restored at session start and again at each commit boundary.
