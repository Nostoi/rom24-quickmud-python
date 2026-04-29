# Session Summary — 2026-04-29 — `comm.c` audit phases 1–3 + 4 gap closures

## Scope

Picked up at master `8544fb4` (v2.6.36) immediately after `board.c` wrapped
up the previous session. The tracker had `comm.c` flagged
`❌ Not Audited 50% — Networking different arch`, but reading the file
showed substantial non-networking parity surface (`bust_a_prompt`,
`act_new`, `colour`, `check_parse_name`, `stop_idling`, `fix_sex`,
`show_string`) that the broad "no audit needed" ruling had bundled with
the networking carve-out.

This session ran phases 1–3 of `/rom-parity-audit comm.c`, producing
`docs/parity/COMM_C_AUDIT.md` with 9 stable gap IDs (COMM-001..COMM-009),
then closed the four highest-impact gaps via `/rom-gap-closer`. The
networking layer (`main`, `init_socket`, `game_loop_*`, descriptor I/O,
telnet protocol) is confirmed deferred-by-design per the asyncio rewrite.

## Outcomes

### `COMM-001` — ✅ FIXED — `bust_a_prompt` rendering (CRITICAL)

- **Python**: new `mud/utils/prompt.py:bust_a_prompt(char) -> str`; wired into `mud/net/connection.py:1698,1923`.
- **ROM C**: `src/comm.c:1420-1595`.
- **Fix**: implemented the ROM token expander (`%h %H %m %M %v %V %x %X %g %s %a %r %R %z %% %e %c %o %O`), default `<%dhp %dm %dmv> %s` fallback when `ch->prompt` is unset, `COMM_AFK` short-circuit. `do_prompt` (`mud/commands/auto_settings.py`) now writes the format string to `Character.prompt` (mirrors ROM `ch->prompt`) instead of `PCData.prompt` (which in ROM is the colour triplet). `send_prompt` applies ANSI rendering so `{p…{x` colour wrappers don't leak. Five existing tests in `test_player_prompt.py` / `test_player_auto_settings.py` / `test_config_commands.py` updated to assert the correct field.
- **Tests**: 8 new cases in `tests/integration/test_prompt_rom_parity.py`; full prompt/config aggregate suite **128/128 green**.
- **Commit**: `1b1d603`.

### `COMM-003` — ✅ FIXED — `check_parse_name` length floor 3 → 2 (IMPORTANT)

- **Python**: `mud/account/account_service.py:591` — `< 3` flipped to `< 2`.
- **ROM C**: `src/comm.c:1729` (`if (strlen (name) < 2) return FALSE;`).
- **Fix**: ROM allows two-letter names (e.g. `Bo`); Python rejected them. Updated NANNY-012's `test_name_validator_matches_rom_check_parse_name` which had locked in the wrong threshold with a docstring misreading ROM.
- **Tests**: existing `test_name_validator_matches_rom_check_parse_name` rewritten to assert `Bo`-accepted / `a`-rejected; `tests/test_account_auth.py` (52 tests) all green.
- **Commit**: `1e00596`.

### `COMM-004` — ✅ FIXED — Mob-keyword collision rejection (IMPORTANT)

- **Python**: new `mud/account/account_service.py:is_valid_character_name`; switched call sites in `account_service.create_character` and `mud/net/connection.py:_run_character_creation_flow`. Exported from `mud/account/__init__.py`.
- **ROM C**: `src/comm.c:1782-1796`.
- **Fix**: layered the new validator on top of `is_valid_account_name` and added the mob-prototype-keyword collision check (using `mud.world.char_find.is_name`). `is_valid_account_name` keeps syntactic-only semantics so account-name validation (a Python addition with no ROM analogue) still works for existing accounts that may match mob keywords.
- **Test fallout**: `tests/test_account_auth.py` used stock RPG names (`Zeus`, `Nomad`, `Queen`, `Guardian`) that legitimately collide with real game mobs. ROM rejects those too. Per AGENTS.md "test contradicting ROM C is a bug in the test", renamed to invented tokens (`Borogon`, `Plumlux`, `Pelvex`, `Quorblix`).
- **Tests**: new `test_name_validator_rejects_mob_keyword_collision` in `tests/integration/test_nanny_login_parity.py`; aggregate 65/65 green.
- **Commit**: `9ef5b20`.

### `COMM-006` — ✅ FIXED — Clan-name rejection (MINOR)

- **Python**: `mud/account/account_service.py:is_valid_character_name` — added `CLAN_TABLE` iteration before the mob loop.
- **ROM C**: `src/comm.c:1713-1718`.
- **Fix**: case-insensitive exact-match against `CLAN_TABLE` entries. `rom`/`ROM` and `loner` now both rejected at character creation.
- **Tests**: new `test_name_validator_rejects_clan_name` in `tests/integration/test_nanny_login_parity.py`.
- **Commit**: `bbf09cf`.

## Files Modified

- `mud/utils/prompt.py` — new file, ROM `bust_a_prompt` port.
- `mud/account/account_service.py` — length floor flip, new `is_valid_character_name`, mob-keyword + clan checks.
- `mud/account/__init__.py` — export `is_valid_character_name`.
- `mud/commands/auto_settings.py` — `do_prompt` stores on `Character.prompt`.
- `mud/net/connection.py` — wire `bust_a_prompt` into both telnet game-loop sites; `send_prompt` applies ANSI rendering; switch character-creation flow to `is_valid_character_name`.
- `tests/integration/test_prompt_rom_parity.py` — new file (8 tests).
- `tests/integration/test_nanny_login_parity.py` — NANNY-012 rewritten + new COMM-004 / COMM-006 tests.
- `tests/integration/test_config_commands.py` — `pcdata.prompt` → `char.prompt` assertions.
- `tests/test_player_prompt.py` / `tests/test_player_auto_settings.py` — same assertion fix.
- `tests/test_account_auth.py` — colliding-name renames (`Zeus`/`Nomad`/`Queen`/`Guardian` → invented tokens).
- `docs/parity/COMM_C_AUDIT.md` — new file (9 gap IDs); rows COMM-001/003/004/006 flipped to ✅.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — `comm.c` flipped from ❌ Not Audited 50% → ⚠️ Partial 75%; the P3-6 detail block rewritten.
- `CHANGELOG.md` — Added/Fixed entries per gap.
- `pyproject.toml` — 2.6.36 → 2.6.37.

## Test Status

- `pytest tests/integration/test_prompt_rom_parity.py tests/integration/test_nanny_login_parity.py tests/integration/test_config_commands.py tests/test_account_auth.py tests/test_player_auto_settings.py tests/test_player_prompt.py` — **128/128 green** (final run).
- Pre-existing ~30-failure baseline (`test_olc_save`, `test_building`, `test_commands`, `test_logging_admin`, `test_mobprog_triggers`) untouched.

## Open `comm.c` gaps (next session)

| ID | Severity | Subject |
|----|----------|---------|
| COMM-002 | IMPORTANT | `page_to_char` / `show_string` interactive pager (largest remaining scope; needs a per-descriptor paging state machine in `mud/net/connection.py`) |
| COMM-005 | MINOR | `check_parse_name` double-newbie-alert sweep + `wiznet` notice |
| COMM-007 | MINOR | `_stop_idling` should use `act("$n has returned from the void.")` PERS-aware text rather than literal name |
| COMM-008 | MINOR | ANSI translator missing `{D {* {/ {- {{` tokens |
| COMM-009 | MINOR | Standalone `fix_sex(char)` helper for spell-affect callsites |

## Next Intended Task

Close COMM-002 (`show_string` pager) — it's the last IMPORTANT-severity
`comm.c` gap and is the most player-visible remaining one (long help /
score / who output currently emits in one shot, no `[Hit Return to
continue]` interactive break at `ch->lines`). Then sweep through
COMM-007 / COMM-008 / COMM-009 in a single follow-on pass and flip
`comm.c` to ✅ AUDITED on the tracker.
