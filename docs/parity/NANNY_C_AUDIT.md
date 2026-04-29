# NANNY.C Parity Audit — ROM 2.4b6 → QuickMUD

**Created**: 2026-04-28
**Status**: 🔄 Phase 3 — gap inventory complete, closures pending
**Coverage**: 1 ROM function (`nanny()`, 824 lines, 16 connection-state cases) mapped to Python; 14 gaps identified (8 CRITICAL, 5 IMPORTANT, 1 MINOR)

ROM source: `src/nanny.c`
Python entry points: `mud/net/connection.py` (login & creation flow), `mud/account/account_service.py` (creation logic, name validation), `mud/account/account_manager.py` (load/persist), `mud/handler.py` (`reset_char`).

---

## Phase 1: Function Inventory

`nanny.c` contains a single public function — `nanny(DESCRIPTOR_DATA *d, char *argument)` — implemented as a giant `switch (d->connected)` state machine. The Python port spreads the cases across async prompt handlers in `mud/net/connection.py` and creation logic in `mud/account/account_service.py`.

| ROM State (case) | ROM Lines | Python Counterpart | File:Line | Status |
|---|---|---|---|---|
| `CON_ANSI` | 143-178 | `_prompt_ansi_preference` | `mud/net/connection.py:481` | ✅ AUDITED |
| `CON_GET_NAME` | 180-262 | `_run_account_login` / `_select_character` | `mud/net/connection.py:789, 1374` | ⚠️ PARTIAL — see NANNY-002 |
| `CON_GET_OLD_PASSWORD` | 264-303 | `_run_account_login` (password loop) | `mud/net/connection.py:812` | ⚠️ PARTIAL — see NANNY-001 |
| `CON_BREAK_CONNECT` | 307-352 | `_select_character` (reconnect path) | `mud/net/connection.py:1420` | ⚠️ PARTIAL — see NANNY-010 |
| `CON_CONFIRM_NEW_NAME` | 354-380 | `_run_character_creation_flow` | `mud/net/connection.py:1303` | ✅ AUDITED |
| `CON_GET_NEW_PASSWORD` | 382-411 | `_prompt_new_password` | `mud/net/connection.py:768` | ⚠️ PARTIAL — see NANNY-011 |
| `CON_CONFIRM_NEW_PASSWORD` | 413-439 | `_prompt_new_password` (confirmation) | `mud/net/connection.py:776` | ✅ AUDITED |
| `CON_GET_NEW_RACE` | 441-499 | `_prompt_for_race` + race apply in `create_character` | `mud/net/connection.py:885`, `mud/account/account_service.py:939` | ✅ AUDITED |
| `CON_GET_NEW_SEX` | 502-531 | `_prompt_for_sex` | `mud/net/connection.py:914` | ✅ AUDITED |
| `CON_GET_NEW_CLASS` | 533-554 | `_prompt_for_class` + `announce_wiznet_new_player` | `mud/net/connection.py:927, 155` | ✅ AUDITED |
| `CON_GET_ALIGNMENT` | 556-588 | `_prompt_for_alignment` | `mud/net/connection.py:940` | ⚠️ PARTIAL — see NANNY-003 |
| `CON_DEFAULT_CHOICE` | 590-630 | `_prompt_customization_choice` | `mud/net/connection.py:957` | ✅ AUDITED |
| `CON_PICK_WEAPON` | 632-657 | `_prompt_for_weapon` | `mud/net/connection.py:1257` | ⚠️ PARTIAL — see NANNY-004 |
| `CON_GEN_GROUPS` | 659-711 | `_run_customization_menu` | `mud/net/connection.py:967` | ✅ AUDITED |
| `CON_READ_IMOTD` | 713-717 | `_send_login_motd` (immortal branch) | `mud/net/connection.py:597` | ✅ AUDITED |
| `CON_NOTE_*` | 722-740 | external note handlers | `mud/notes.py` | N/A (delegated) |
| `CON_READ_MOTD` (level 0 branch) | 742-790 | `_finalize_login` / `give_school_outfit` | `mud/net/connection.py:1554`, `mud/commands/inventory.py:142` | ⚠️ PARTIAL — see NANNY-005 |
| `CON_READ_MOTD` (room routing) | 791-802 | login room placement | `mud/account/account_manager.py:119` | ⚠️ PARTIAL — see NANNY-006 |
| `CON_READ_MOTD` (entry broadcast) | 804-815 | — | — | ❌ MISSING — see NANNY-007, NANNY-008 |
| `check_parse_name` | (called from 188) | `is_valid_account_name` | `mud/account/account_service.py:572` | ⚠️ PARTIAL — see NANNY-012 |
| `reset_char` (called from 760) | (handler.c) | `reset_char` exists but unwired on login | `mud/handler.py:1046` | ❌ MISSING — see NANNY-014 |
| `set_title` / `title_table` | (called from 778-780) | — | — | ❌ MISSING — see NANNY-009 |

---

## Phase 2: Function-by-Function Verification

### `CON_GET_NAME` (lines 180-262)

ROM uppercases the first letter, runs `check_parse_name`, calls `load_char_obj` (sets `fOld` based on file existence), then runs **four gates**:

1. `IS_SET(ch->act, PLR_DENY)` → log + close (line 197-205).
2. `check_ban(host, BAN_PERMIT) && !IS_SET(ch->act, PLR_PERMIT)` → site-banned close (207-214).
3. `check_reconnect(d, name, FALSE)` (216) — if returns true, treat as old.
4. Else if `wizlock && !IS_IMMORTAL(ch)` → wizlocked close (222-227).

For new players: `newlock` close (241-246), `BAN_NEWBIES` close (248-255), then `CON_CONFIRM_NEW_NAME` prompt.

Python: `_run_account_login` and `_select_character` cover wizlock/newlock/BAN_PERMIT/BAN_NEWBIES via `mud/account/account_service.py:820-828`. **The PLR_DENY gate is not wired** even though `PlayerFlag.DENY` exists (`mud/models/constants.py:416`). See NANNY-002.

### `CON_GET_OLD_PASSWORD` (lines 264-303)

ROM:
- `if (strcmp(crypt(argument, pwd), pwd)) { send "Wrong password.", close_socket; return; }` (269-274).
- One attempt; failure closes the socket. No retry counter.
- On success: `check_playing` (kick & punt) + `check_reconnect` checks; log + `wiznet WIZ_SITES` "%s@%s has connected." (284-286); `PLR_COLOUR` toggled from `d->ansi` (288-291); `do_help imotd` if immortal else `do_help motd`, transition to `CON_READ_IMOTD` / `CON_READ_MOTD`.

Python `_run_account_login` (`mud/net/connection.py:812-826`) loops on wrong-password and allows retries. See NANNY-001. WIZ_SITES broadcast and PLR_COLOUR toggle ARE present (`announce_wiznet_login` at 127, `_apply_colour_preference` at 496).

### `CON_GET_NEW_PASSWORD` / `CON_CONFIRM_NEW_PASSWORD` (lines 382-439)

ROM enforces ≥5 chars (387-393) and rejects passwords whose `crypt()` output contains `~` (file-format poisoner; 396-405). Python `_prompt_new_password` (`mud/net/connection.py:768-782`) enforces 5-char minimum but does not scan for `~`. Python uses a SQLite/DB backend, so the file-format risk does not apply directly — gap is preserved as MINOR for completeness. See NANNY-011.

### `CON_GET_NEW_RACE` (lines 441-499)

ROM applies race effects in this order: `ch->race`, `perm_stat[i] = pc_race_table[race].stats[i]`, `affected_by |= race.aff`, `imm_flags |= race.imm`, `res_flags |=`, `vuln_flags |=`, `form`, `parts`, then `group_add` for up to 5 race skills, `pcdata->points = pc_race_table[race].points`, `size`. Python applies the same fields in `mud/account/account_service.py:939-956` and `finalize_creation_stats`. ✅ Verified.

### `CON_GET_NEW_SEX` (lines 502-531)

ROM sets BOTH `ch->sex` and `ch->pcdata->true_sex`. Python sets both at `mud/account/account_service.py:946-947`. ✅ Verified.

### `CON_GET_NEW_CLASS` (lines 533-554)

ROM logs `"%s@%s new player."`, broadcasts `"Newbie alert!  $N sighted."` (WIZ_NEWBIE) and the log line (WIZ_SITES). Python `announce_wiznet_new_player` (`mud/net/connection.py:155-194`) replicates both. ✅ Verified.

### `CON_GET_ALIGNMENT` (lines 556-588) + post-alignment block

ROM sets alignment to exactly `750 / 0 / -750` (G/N/E), then runs:

```
group_add(ch, "rom basics", FALSE);
group_add(ch, class_table[ch->class].base_group, FALSE);
ch->pcdata->learned[gsn_recall] = 50;
```

Python `_prompt_for_alignment` uses the exact 750/0/-750 values (`mud/net/connection.py:949-953`) ✅; `mud/account/account_service.py:918-920` adds "rom basics", base group, default group, but **does not initialize `learned[gsn_recall] = 50`**. See NANNY-003.

### `CON_PICK_WEAPON` (lines 632-657)

ROM validates `ch->pcdata->learned[*weapon_table[weapon].gsn] > 0` and on success sets `learned[*weapon_table[weapon].gsn] = 40` (line 653). Python `_prompt_for_weapon` (`mud/net/connection.py:1257-1270`) records the weapon choice but does **not** set the learned skill level to 40. See NANNY-004.

### `CON_GEN_GROUPS` done branch (lines 659-711)

ROM checks `points < 40 + race.points` minimum, reports creation points + exp/level, and applies training compensation: `if (points < 40) train = (40 - points + 1) / 2`. Python `account_service.py:433-435` (`train_value`) implements `(40 - creation_points + 1) // 2` correctly (Python integer floor division matches C signed division for non-negative operands). ✅ Verified.

### `CON_READ_MOTD` — first-login (level 0) block (lines 762-790)

ROM, on `level == 0`:

```c
ch->perm_stat[class_table[ch->class].attr_prime] += 3;     /* prime stat bonus */
ch->level   = 1;
ch->exp     = exp_per_level(ch, ch->pcdata->points);
ch->hit     = ch->max_hit;
ch->mana    = ch->max_mana;
ch->move    = ch->max_move;
ch->train   = 3;
ch->practice = 5;
sprintf(buf, "the %s", title_table[ch->class][ch->level][ch->sex==SEX_FEMALE?1:0]);
set_title(ch, buf);
do_function(ch, &do_outfit, "");
obj_to_char(create_object(get_obj_index(OBJ_VNUM_MAP), 0), ch);
char_to_room(ch, get_room_index(ROOM_VNUM_SCHOOL));
do_function(ch, &do_help, "newbie info");
```

Python:
- `practice=5, train=3` set in creation (`mud/account/account_service.py:929-930`). ✅
- `give_school_outfit` (`mud/commands/inventory.py:142-198`) gives outfit + `OBJ_VNUM_MAP = 3162`. ✅
- Starting room SCHOOL applied via `starting_room_vnum`. ✅
- **Missing**: `perm_stat[attr_prime] += 3` first-login bonus. See NANNY-005.
- **Missing**: `set_title("the …")` — `title_table` data is not present in the port. See NANNY-009.

### `CON_READ_MOTD` — resource refresh + `reset_char` (lines 760, 772-775)

Every login (new and returning) calls `reset_char(ch)` (760) which recomputes max stats / armor / hit / mana / move from current equipment + race/class. New chars also explicitly set `hit = max_hit; mana = max_mana; move = max_move`. Python's `reset_char` exists in `mud/handler.py:1046` but is **not invoked on the login path** (`mud/net/connection.py:1521-1800`). Resources are loaded from saved values without refresh. See NANNY-013, NANNY-014.

### `CON_READ_MOTD` — room routing (lines 791-802)

```c
else if (ch->in_room  != NULL) char_to_room(ch, ch->in_room);
else if (IS_IMMORTAL(ch))      char_to_room(ch, get_room_index(ROOM_VNUM_CHAT));   /* 1200 */
else                            char_to_room(ch, get_room_index(ROOM_VNUM_TEMPLE)); /* 3001 */
```

Python `mud/account/account_manager.py:119-128` restores from `was_in_room` or falls back to TEMPLE (3001), but does **not route immortals to ROOM_VNUM_CHAT (1200)** when no saved room exists. See NANNY-006.

### `CON_READ_MOTD` — entry broadcast + pet (lines 804-815)

ROM:

```c
act("$n has entered the game.", ch, NULL, NULL, TO_ROOM);
do_function(ch, &do_look, "auto");
wiznet("$N has left real life behind.", ch, NULL, WIZ_LOGINS, WIZ_SITES, get_trust(ch));

if (ch->pet != NULL) {
    char_to_room(ch->pet, ch->in_room);
    act("$n has entered the game.", ch->pet, NULL, NULL, TO_ROOM);
}
```

Python sends MOTD + auto-look + WIZ_LOGINS broadcast (`announce_wiznet_login` at `mud/net/connection.py:114`). **Missing**: the per-room `act("$n has entered the game.", TO_ROOM)` broadcast for the player and their pet, and the pet does not follow the player into the room on login. See NANNY-007, NANNY-008.

### `CON_BREAK_CONNECT` (lines 307-352)

ROM, on `Y`: scans all descriptors and `close_socket` on every duplicate matching `ch->name` (or `original->name` for switched immortals), then attempts `check_reconnect`. Python `_select_character` (`mud/net/connection.py:1420-1443`) handles a single duplicate session but does not iterate the full descriptor list. See NANNY-010.

### `check_parse_name` (called from line 188)

ROM enforces length 3–12, alpha-only, and rejects reserved tokens including `all auto immortal self someone something the you loner none god imp`. Python `is_valid_account_name` (`mud/account/account_service.py:572-613`) enforces 2–12 (vs ROM 3–12) and omits `god` and `imp` from the reserved list. See NANNY-012.

---

## Phase 3: Gaps

| Gap ID | Severity | ROM C ref | Python ref | Description | Status |
|---|---|---|---|---|---|
| `NANNY-001` | CRITICAL | `nanny.c:269-274` | `mud/net/connection.py:812-826` | Wrong-password loop allows retries; ROM closes the socket on first failure. | 🔄 OPEN |
| `NANNY-002` | CRITICAL | `nanny.c:197-205` | `mud/account/account_service.py:820` | `PlayerFlag.DENY` is defined but not checked on character load — denied players can still log in. | ✅ FIXED — `is_character_denied_access` helper added; checked in both load paths of `_select_character`. Logs `Denying access to <name>@<host>.` and sends `You are denied access.` Test: `tests/integration/test_nanny_login_parity.py::test_denied_character_is_blocked_from_login`. |
| `NANNY-003` | CRITICAL | `nanny.c:581` | `mud/account/account_service.py:918-920` | `learned[gsn_recall] = 50` not initialized after class/alignment selection — new chars cannot recall reliably. | 🔄 OPEN |
| `NANNY-004` | CRITICAL | `nanny.c:653` | `mud/net/connection.py:1257-1270` | `CON_PICK_WEAPON` does not set `learned[weapon_gsn] = 40` — chosen weapon proficiency is 0%. | 🔄 OPEN |
| `NANNY-005` | CRITICAL | `nanny.c:769` | `mud/net/connection.py:1554` | First-login `perm_stat[class.attr_prime] += 3` bonus not applied. | 🔄 OPEN |
| `NANNY-006` | CRITICAL | `nanny.c:791-802` | `mud/account/account_manager.py:119-128` | Returning immortal without saved room is not routed to `ROOM_VNUM_CHAT (1200)`; falls through to TEMPLE. | 🔄 OPEN |
| `NANNY-007` | CRITICAL | `nanny.c:804` | `mud/net/connection.py:1554-1601` | `act("$n has entered the game.", TO_ROOM)` broadcast missing on login — other players in the room never see arrivals. | ✅ FIXED — `broadcast_entry_to_room` helper added; called in both non-reconnecting branches of `handle_connection`. Test: `tests/integration/test_nanny_login_parity.py::test_login_broadcasts_entry_to_room`. |
| `NANNY-014` | CRITICAL | `nanny.c:760` | `mud/handler.py:1046` (defined but unwired) | `reset_char(ch)` not invoked on login; max stats / hit / mana / move / armor not recomputed from equipment. | ✅ FIXED — `apply_login_state_refresh` wired into both branches of `handle_connection`; latent `WearLocation.MAX` typo in `reset_char` corrected to `19` (ROM `MAX_WEAR`). Test: `tests/integration/test_nanny_login_parity.py`. |
| `NANNY-008` | IMPORTANT | `nanny.c:810-815` | — | Pet does not follow owner into room on login (`char_to_room(pet, in_room)` + entry act missing). | 🔄 OPEN |
| `NANNY-009` | IMPORTANT | `nanny.c:778-780` | — | `title_table[class][level][sex]` data and `set_title("the …")` first-login call missing — new chars get no class title. | 🔄 OPEN |
| `NANNY-010` | IMPORTANT | `nanny.c:307-352` | `mud/net/connection.py:1420-1443` | `CON_BREAK_CONNECT` Y-path doesn't iterate the full descriptor list; only closes one duplicate session. | 🔄 OPEN |
| `NANNY-012` | IMPORTANT | `nanny.c:188` (`check_parse_name`) | `mud/account/account_service.py:572-613` | Name validator allows length 2 (ROM minimum is 3) and is missing `god` / `imp` from reserved-name list. | 🔄 OPEN |
| `NANNY-013` | IMPORTANT | `nanny.c:772-775` | `mud/net/connection.py:1554` | First-login `hit=max_hit; mana=max_mana; move=max_move; exp=exp_per_level(ch,points)` not explicitly applied at MOTD completion. | 🔄 OPEN |
| `NANNY-011` | MINOR | `nanny.c:396-405` | `mud/net/connection.py:768-782` | New password is not scanned for `~` characters (ROM file-format poisoner check). Python uses a DB backend; preserved for parity completeness. | 🔄 OPEN |

---

## Phase 4: Gap Closures

(Pending — invoke `rom-gap-closer` per ID. One gap = one failing test = one commit.)

---

## Phase 5: Completion Summary

(Pending — flip tracker row when all CRITICAL/IMPORTANT gaps are closed.)
