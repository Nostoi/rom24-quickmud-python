# Session Summary — 2026-05-22 — `nanny.c` creation transcript and retry parity

## Scope

Continued the `nanny.c` trust rebuild on the live new-character creation flow.
Two slices landed: (1) restoration of the ROM-exact happy-path creation
prompts (race / sex / class / weapon, plus password and greeting parsing),
and (2) closure of every invalid-entry retry wording gap plus the
customization-menu transcript drift. ROM source-of-truth is `src/nanny.c`
lines 396-657; comparisons follow Mode B (transcript differential) per
`docs/superpowers/specs/2026-05-21-rom-differential-testing-design.md`.

## Outcomes

### Slice 1 — happy-path creation prompts (commit `8a747af`)

- **Restored ROM wording** in `mud/net/connection.py`:
  - `"New character."` line before password prompt
  - `"Give me a password for <Name>:"` and `"Please retype password:"`
  - ROM race / sex / class / weapon creation prompts
- **Removed non-ROM prompts**:
  - `"Creating new character 'X'."` line (was non-ROM scaffolding)
  - stat-reroll and hometown prompts (ROM `nanny.c:476-478` derives
    `perm_stat` from `pc_race_table[race].stats[i]`; ROM has no
    stat-reroll or hometown selection in the new-character flow)
- **Fixed greeting parsing** so the pre-login greeting no longer leaks the
  embedded MOTD block before `Name:`.
- **Tests updated**: `tests/test_websocket_server.py`,
  `tests/test_account_auth.py`, `tests/test_telnet_server.py`,
  `tests/integration/test_nanny_login_parity.py`.

### Slice 2 — invalid-entry retry + customization transcript (commit `cc04b85`)

Six gaps closed under stable IDs `NANNY-RETRY-001..006` in
`docs/parity/NANNY_C_AUDIT.md`:

#### `NANNY-RETRY-001` — ✅ FIXED — race invalid wording

- **Python**: `mud/net/connection.py:_prompt_for_race`
- **ROM C**: `src/nanny.c:460-471`
- **Gap**: Sent `"That's not a valid race."` (ROM: `"That is not a valid race."`); listing prefix used bare `\n` instead of ROM `\n\r`.
- **Fix**: Wording matches ROM; listing prefix now `"The following races are available:\n\r  "`.
- **Test**: `tests/integration/test_nanny_login_parity.py::test_race_invalid_retry_wording`

#### `NANNY-RETRY-002` — ✅ VERIFIED — race "help" branch wording

- **Python**: `mud/net/connection.py:_prompt_for_race`
- **ROM C**: `src/nanny.c:444-453`
- **Fix**: Help-branch and invalid-branch re-prompt wordings already correct (`"What is your race (help for more information)? "` vs `"What is your race? (help for more information) "`); regression test added.
- **Test**: `tests/integration/test_nanny_login_parity.py::test_race_help_branch_reprompt_wording`

#### `NANNY-RETRY-003` — ✅ FIXED — class invalid wording

- **Python**: `mud/net/connection.py:_prompt_for_class`
- **ROM C**: `src/nanny.c:538-539`
- **Gap**: Sent `"That's not a valid class."` and re-prompted with the full class list (ROM sends `"That's not a class."` + `"What IS your class? "` with capital `IS`).
- **Fix**: Wording corrected and retry prompt switched to `"What IS your class? "`.
- **Test**: `tests/integration/test_nanny_login_parity.py::test_class_invalid_retry_wording`

#### `NANNY-RETRY-004` — ✅ FIXED — customize Y/N retry wording

- **Python**: `mud/net/connection.py:_prompt_customization_choice`, `_prompt_yes_no`
- **ROM C**: `src/nanny.c:626-628`
- **Gap**: Customize invalid retry sent generic `"Please answer Y or N."` (ROM: `"Please answer (Y/N)? "`).
- **Fix**: Added `retry_message` kwarg to `_prompt_yes_no`; customize callsite now passes ROM-exact wording. Other Y/N callsites keep existing retry text.
- **Test**: `tests/integration/test_nanny_login_parity.py::test_customize_invalid_reprompt_wording`

#### `NANNY-RETRY-005` — ✅ FIXED — weapon prompt CRLF

- **Python**: `mud/net/connection.py:_prompt_for_weapon`
- **ROM C**: `src/nanny.c:611-624`
- **Gap**: Weapon-pick prompt used bare `\n` separators (ROM `\n\r`).
- **Fix**: Prompt rebuilt with ROM `\n\r` line endings before `"Your choice? "`.
- **Test**: `tests/integration/test_nanny_login_parity.py::test_weapon_prompt_uses_crlf`

#### `NANNY-RETRY-006` — ✅ FIXED — weapon invalid CRLF

- **Python**: `mud/net/connection.py:_prompt_for_weapon`
- **ROM C**: `src/nanny.c:638-649`
- **Gap**: Weapon-invalid retry prompt used bare `\n` (ROM `\n\r`).
- **Fix**: Retry path matches ROM separator.
- **Test**: `tests/integration/test_nanny_login_parity.py::test_weapon_invalid_uses_crlf`

## Files Modified

- `mud/net/connection.py` — happy-path and invalid-path creation prompts + greeting parser
- `mud/network/websocket_stream.py` — MOTD prompt classification for the greeting band
- `tests/integration/test_nanny_login_parity.py` — added `NANNY-RETRY-001..006` transcript-parity tests
- `tests/test_account_auth.py` — updated race-help and customization fixtures for ROM-exact wording / new `_prompt_yes_no` signature
- `tests/test_telnet_server.py` — refreshed for new transcript ordering
- `tests/test_websocket_server.py` — refreshed for new transcript ordering
- `docs/parity/NANNY_C_AUDIT.md` — added `NANNY-RETRY-001..006` rows to Phase 3 (all ✅ FIXED / VERIFIED)
- `CHANGELOG.md` — `[Unreleased]` updated with the two slices
- `pyproject.toml` — 2.8.31 → 2.8.32

## Test Status

- Targeted creation/login band (`tests/integration/test_nanny_login_parity.py tests/test_account_auth.py tests/test_telnet_server.py tests/test_websocket_server.py`): **96 passed, 1 skipped**.
- Full suite (`./venv/bin/python -m pytest -q --timeout=60`): **4599 passed, 4 skipped** (+6 vs prior baseline 4593/4; zero regressions).
- `ruff check` on touched files: no new errors (pre-existing baseline only).
- `gitnexus_detect_changes()`: LOW risk; FTS warnings unrelated to the changes (index is stale, see Next Steps).

## Next Steps

Continue Plan Task 4 (`docs/superpowers/plans/2026-05-21-parity-trust-rebuild-reaudit.md`)
into the `save.c` boundary slice:

1. DB row state after completed creation (Mode C — scenario state).
2. Post-login `logon` semantics and first-command output after reconnect (Mode B — transcript).
3. Save → reload → retained state verification on the real telnet/websocket path, not helper-only fixtures.

Operational follow-ups:

- `log/orphaned_helps.txt` is a runtime-generated file that keeps appearing in `git status`; add it to `.gitignore` in a small repo-hygiene commit.
- GitNexus index is stale (`last indexed: 0dd803e`). Run `npx gitnexus analyze --skip-agents-md` to re-index before the next session relies on `gitnexus_impact` / `gitnexus_detect_changes`.
