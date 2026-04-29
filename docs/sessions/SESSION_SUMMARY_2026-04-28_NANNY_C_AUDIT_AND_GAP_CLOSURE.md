# Session Summary — 2026-04-28 — `nanny.c` parity audit & gap closure

## Scope

Audited `src/nanny.c` (ROM login state machine, 16 CON_* states) against the Python equivalents in `mud/net/connection.py` and `mud/account/account_service.py`. Produced `docs/parity/NANNY_C_AUDIT.md` with stable IDs `NANNY-001..NANNY-014`, then closed/verified 11 of the 14 gaps via the rom-gap-closer TDD flow. Three IMPORTANT gaps requiring larger refactoring were deferred with explicit follow-up notes.

## Outcomes

### `NANNY-001` — ✅ FIXED
- **ROM C**: `src/nanny.c:269-274` (`close_socket(d)` on bad password — one attempt only)
- **Python**: `mud/net/connection.py:_run_account_login`
- **Fix**: BAD_CREDENTIALS branch now `return None` instead of `continue`, disconnecting on first wrong password (also covers reconnect path).
- **Tests**: `test_account_login_disconnects_on_wrong_password`

### `NANNY-002` — ✅ FIXED
- **ROM C**: `src/nanny.c:197-205` (`IS_SET(ch->act, PLR_DENY)` → "Denying access to …" log + `You are denied access.` + close)
- **Python**: `mud/net/connection.py:_select_character`
- **Fix**: New `is_character_denied_access` helper; PLR_DENY check wired into both load branches at character-selection time (account-with-multiple-characters model differs from ROM's single-character file, so check moved from CON_GET_NAME).
- **Tests**: `test_denied_character_is_blocked_from_login`

### `NANNY-003` — ✅ VERIFIED (audit correction)
- **ROM C**: `src/nanny.c:581` (`learned[gsn_recall] = 50`)
- **Python**: `mud/models/character.py:from_orm` (lines 1052-1053) clamps `learned["recall"]` to ≥50 on every character load.
- **Tests**: `test_new_character_starts_with_recall_skill_at_50_percent`

### `NANNY-004` — ✅ VERIFIED (audit correction)
- **ROM C**: `src/nanny.c:653` (`learned[weapon_gsn] = 40`)
- **Python**: `mud/models/character.py:from_orm` (lines 1047-1051) seeds picked weapon's skill via `_STARTING_WEAPON_SKILL_BY_VNUM`.
- **Tests**: `test_chosen_weapon_skill_seeded_at_40_percent`

### `NANNY-005` — ✅ VERIFIED (audit correction)
- **ROM C**: `src/nanny.c:769` (`perm_stat[class.attr_prime] += 3`)
- **Python**: Already implemented in `mud/account/account_service.py:finalize_creation_stats` and locked in by `tests/test_nanny_rom_parity.py::test_prime_attribute_bonus_formula`.

### `NANNY-006` — ✅ FIXED
- **ROM C**: `src/nanny.c:791-802` (`IS_IMMORTAL ? ROOM_VNUM_CHAT : ROOM_VNUM_TEMPLE`)
- **Python**: `mud/net/connection.py:default_login_room_vnum` + room fallback in `handle_connection`.
- **Fix**: New `ROOM_VNUM_CHAT = 1200` constant (ROM `src/merc.h:1250`); `is_admin` characters with no saved room land in chat room, mortals in temple.
- **Tests**: `test_immortal_without_saved_room_routes_to_chat_room`

### `NANNY-007` — ✅ FIXED
- **ROM C**: `src/nanny.c:804` (`act("$n has entered the game.", ch, NULL, NULL, TO_ROOM)`)
- **Python**: `mud/net/connection.py:broadcast_entry_to_room`
- **Fix**: New helper using `act_format` for `$n` substitution; excludes the actor; wired into `handle_connection` after the character is in-room.
- **Tests**: `test_login_broadcasts_entry_to_room`

### `NANNY-011` — ✅ FIXED
- **ROM C**: `src/nanny.c:396-405` (file-format poisoner — reject `~` in passwords)
- **Python**: `mud/net/connection.py:_prompt_new_password`
- **Fix**: Added `~` scan between length check and confirm prompt; emits ROM message "New password not acceptable, try again." Practical risk gone (DB backend) but parity preserved.
- **Tests**: `test_new_password_rejects_tilde`

### `NANNY-012` — ✅ FIXED
- **ROM C**: `src/nanny.c:188` (`check_parse_name`, defined in `src/comm.c`)
- **Python**: `mud/account/account_service.py:is_valid_account_name`
- **Fix**: Minimum length raised from 2 → 3; reserved-name set gained `god` and `imp`.
- **Tests**: `test_name_validator_matches_rom_check_parse_name`

### `NANNY-013` — ✅ VERIFIED (audit correction)
- **ROM C**: `src/nanny.c:772-775` (`hit=max_hit; mana=max_mana; move=max_move`)
- **Python**: Covered by `from_orm` initialising `max_*` from `perm_*` plus `hit` from saved `hp` (a fresh character is persisted with `hp=perm_hit=100`); NANNY-014 reset_char further guarantees max_* are restored on every login.
- **Tests**: `test_first_login_resources_at_max`

### `NANNY-014` — ✅ FIXED
- **ROM C**: `src/nanny.c:760` (`reset_char(ch)` before MOTD)
- **Python**: `mud/net/connection.py:apply_login_state_refresh` → `mud/handler.py:reset_char`
- **Fix**: Login flow invokes `reset_char` on every successful login, restoring `max_hit/max_mana/max_move` from `pcdata.perm_*`, zeroing transient `mod_stat[]/hitroll/damroll/saving_throw`, and re-applying equipment affects. Wired into both branches of `handle_connection`. Also corrected a latent `AttributeError` in `mud/handler.py` where `range(int(WearLocation.MAX))` was unreachable until reset_char became live; replaced with literal `19` matching ROM `MAX_WEAR` (`src/merc.h:1356`).
- **Tests**: `test_login_finalization_invokes_reset_char`, `test_login_state_refresh_is_a_noop_for_npcs`

### Deferred (out of session scope)

- `NANNY-008` (IMPORTANT) — pet follows owner on login (`src/nanny.c:810-815`). Requires async pet-load refactor.
- `NANNY-009` (IMPORTANT) — `title_table[class][level][sex]` data + `set_title` first-login call. Requires porting ROM data tables.
- `NANNY-010` (IMPORTANT) — CON_BREAK_CONNECT Y-path should iterate ALL descriptors, not just one. Requires descriptor-list iteration.

## Files Modified

- `mud/net/connection.py` — new helpers (`default_login_room_vnum`, `is_character_denied_access`, `broadcast_entry_to_room`, `apply_login_state_refresh`); `~` rejection in `_prompt_new_password`; PLR_DENY checks; immortal/mortal room fallback; `reset_char` invocation on login.
- `mud/handler.py` — fixed unreachable `WearLocation.MAX` reference (replaced with `19`, ROM `MAX_WEAR`).
- `mud/models/constants.py` — added `ROOM_VNUM_CHAT = 1200`.
- `mud/account/account_service.py` — `_RESERVED_NAMES` adds `god`, `imp`; minimum length 3.
- `tests/integration/test_nanny_login_parity.py` — new file, 11 integration tests covering the closures above.
- `docs/parity/NANNY_C_AUDIT.md` — created; rows for NANNY-001..014 flipped/annotated.
- `CHANGELOG.md` — added Fixed entries for every closed/verified gap.
- `pyproject.toml` — `2.6.18` → `2.6.19`.

## Test Status

- `pytest tests/integration/test_nanny_login_parity.py` — 11/11 passing.
- Pre-existing baseline lint/test failures unrelated to this session were verified with `git stash`.

## Next Steps

- `NANNY-008` (pet-on-login): port pet-load + follower setup; integration test that verifies a saved pet appears in the owner's room.
- `NANNY-009` (title_table): port ROM data tables, call `set_title` at level-0→1 promotion.
- `NANNY-010` (CON_BREAK_CONNECT): descriptor-list iteration on Y-path.
- After NANNY-008/009/010 close, flip the `nanny.c` row in `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` from ⚠️ Partial → ✅ AUDITED.
- Otherwise pick the next P2/P3 file from the tracker (`ban.c` or OLC).
