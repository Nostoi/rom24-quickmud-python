# META Audit: BROADCAST_COVERAGE (Class 1)
## Scope
This audit checks every command registered in `mud/commands/dispatcher.py` (284 registrations, 283 unique slot names — `clantalk` is an alias of `clan` and shares one row) against its ROM 2.4b6 C counterpart in `src/`. For each command we count the ROM `act(...)` / `act_new(...)` call sites bucketed by terminal arg (`TO_ROOM` / `TO_VICT` / `TO_NOTVICT` / `TO_ALL`; `TO_CHAR` is ignored because it maps to the Python function's return value) and compare against the Python implementation's broadcast indicators (`broadcast_room`, `broadcast_global`, `room.broadcast`, `act_format`, raw `act(`, `messages.append`, `send_to_char(victim|target|recipient)`, `for x in room.people`, `send_to_room`, `act_to_room`).

**Depth limitation.** This is a *shallow* mechanical pass: counts are extracted by regex from the function body (no AST, no per-branch flow analysis). A ✅ row means the Python function emits at least as many non-TO_CHAR broadcast hits as the ROM function — it does NOT prove every branch covers the right target/template. ❌/⚠️ rows are real gap candidates and warrant manual verification, but the ✅ majority is a pinning regression record, not a deep proof.
## Method
1. Enumerate `Command("name", do_X, …)` registrations in `mud/commands/dispatcher.py` (284 hits).
2. For each handler `do_X`/`cmd_X`, locate the ROM C function by name (`grep -n "^void do_X " src/*.c`).
3. Parse the ROM C function body (string-literal-stripped to avoid the `"{a…"` color-code brace bug) and count `act(...)`/`act_new(...)` call sites by terminal arg.
4. Parse the Python function body and count broadcast indicators (10 patterns: see Scope).
5. Assign status: ✅ if ROM_non_TO_CHAR == 0 OR py_total ≥ ROM_non_TO_CHAR; ⚠️ if 0 < py_total < ROM_non_TO_CHAR; ❌ if py_total == 0 and ROM_non_TO_CHAR > 0; N/A if no ROM counterpart.
6. Notes column flags ROM line refs and the dominant Python broadcast helper for verification.

Cross-file invariants referenced: **INV-008** (single-delivery — broadcast does not double-fire to the actor), **INV-016** (spell position-transition broadcasts), **INV-025** (TRIG_ACT mob script dispatch from broadcasts).

**Worked precedents** in the 2.9.x cluster: 2.9.18 (`do_buy` BCAST-001), 2.9.19 (`do_follow`/`add_follower` BCAST-002), 2.9.20 (`do_group` BCAST-003) — all detected the same pattern this audit enumerates.
## Per-command audit
Counts shown as `ROM` (TO_ROOM / TO_VICT / TO_NOTVICT / TO_ALL) vs `Py total` (sum across all broadcast indicators). One row per dispatcher slot.

| # | Command | Python entry | ROM C ref | TO_ROOM | TO_VICT | TO_NOTVICT | TO_ALL | Py total | Status | Notes |
|---|---------|--------------|-----------|---------|---------|------------|--------|----------|--------|-------|
| 1 | `@goto` | `mud/commands/build.py:3930` | `src/act_wiz.c:905` | 0 | 4 | 0 | 0 | 0 | ✅ COVERED | **BCAST-001** — FALSE POSITIVE. Same handler as `do_goto` (admin alias). `do_goto` in `imm_commands.py:164` already broadcasts via `_act_room(old_room, ...)` (bamfout) and `_act_room(location, ...)` (bamfin) at lines 196, 198, 208, 210. The audit's body-only static scan missed `_act_room` as a broadcast helper. Helper-transitivity caveat applies. |
| 2 | `clone` | `mud/commands/imm_search.py:375` | `src/act_wiz.c:2296` | 2 | 0 | 0 | 0 | 0 | ⚠️ BLOCKED by WIZLOAD-001 (obj path) | **BCAST-002** — ROM has 2 non-TO_CHAR act(). Object path: blocked — `do_clone` imports `spawn_obj` from `mud.spawning.obj_spawner` which doesn't exist (canonical: `spawn_object`); ImportError on every clone-object call. Mob path is functionally reachable (uses `spawn_mob` which exists) but the TO_ROOM `$n has created $N.` broadcast still needs adding; could be closed in isolation but the BCAST row stays ⚠️ until WIZLOAD-001 unblocks the object path. Adjacent (out of scope for BCAST): return strings `"You clone $p."` / `"You clone $N."` are unsubstituted ROM template literals — `$p`/`$N` are not expanded to the clone's short_descr. |
| 3 | `close` | `mud/commands/doors.py:181` | `src/act_move.c:425` | 3 | 0 | 0 | 0 | 3 | ✅ FIXED (2.9.59) | **BCAST-003** — Pre-fix `do_close` returned only the actor "Ok." / "You close $p." string with zero `broadcast_room` calls. Added portal/container TO_ROOM `$n closes $p.` (act_move.c:492, 515), door TO_ROOM `$n closes the $d.` (act_move.c:534), and linked-room per-person `The $d closes.` (act_move.c:545-547). Symmetric to BCAST-016. Regression: `tests/integration/test_close_broadcasts.py` (4/4). |
| 4 | `dirt` | `mud/commands/combat.py:839` | `src/fight.c:2349` | 1 | 1 | 0 | 0 | 2 | ✅ COVERED (2.9.59) | **BCAST-004** — FALSE POSITIVE. Probe (2.9.59) confirmed `mud/skills/handlers.py:3018-3026` already emits TO_ROOM `"$n is blinded by the dirt in their eyes!"` via `broadcast_room` and TO_VICT `"$n kicks dirt in your eyes!"` via `_send_to_char`. The audit's static scan inspected `combat.py:do_dirt` (the dispatcher entry point) but the broadcasts live in the skill handler. Helper-transitivity caveat (audit looked at the wrong file). |
| 5 | `disarm` | `mud/commands/combat.py:963` | `src/fight.c:2995` | 0 | 1 | 1 | 0 | 2 | ✅ COVERED (2.9.59) | **BCAST-005** — FALSE POSITIVE. Probe (2.9.59) confirmed `mud/skills/handlers.py:3108-3134` already emits TO_VICT + TO_NOTVICT on all three ROM branches (success, failure, NOREMOVE). The audit's static scan inspected `combat.py:do_disarm` but the broadcasts live in the skill handler. Helper-transitivity caveat. |
| 6 | `enter` | `mud/commands/movement.py:47` | `src/act_enter.c:43` | 5 | 0 | 0 | 0 | 0 | ❌ | **BCAST-006** — ROM has 5 non-TO_CHAR act() but Python has 0 broadcast hits. Py indicators: (no broadcast hits) |
| 7 | `envenom` | `mud/commands/remaining_rom.py:177` | `src/act_obj.c:820` | 2 | 0 | 0 | 0 | 2 | ✅ COVERED (2.9.60) | **BCAST-007** — FALSE POSITIVE. `mud/commands/remaining_rom.py:do_envenom` dispatches to `mud/skills/handlers.py:envenom`, which emits both ROM TO_ROOM acts: food/drink path `"$n treats $p with deadly poison."` (handlers.py:3742, ROM act_obj.c:887) and weapon path `"$n coats $p with deadly venom."` (handlers.py:3847, ROM act_obj.c:946). Audit's static scan inspected the dispatcher, not the handler. Same helper-transitivity caveat as BCAST-004/005/026. |
| 8 | `goto` | `mud/commands/imm_commands.py:164` | `src/act_wiz.c:905` | 0 | 4 | 0 | 0 | 0 | ✅ COVERED | **BCAST-008** — FALSE POSITIVE (verified 2.9.58). `do_goto` calls `_act_room(old_room, char, bamfout)` and `_act_room(location, char, bamfin)` — the helper at `imm_commands.py:473-481` iterates `room.people` and delivers via `_send_to_char`. ROM emits both default and pcdata-bamf variants per direction; Python emits exactly one per direction depending on whether bamfin/bamfout is set, which is the equivalent contract. |
| 9 | `group` | `mud/commands/group_commands.py:165` | `src/act_comm.c:1736` | 0 | 3 | 2 | 0 | 0 | ❌ | **BCAST-009** — ROM has 5 non-TO_CHAR act() but Python has 0 broadcast hits. Py indicators: (no broadcast hits) |
| 10 | `gtell` | `mud/commands/group_commands.py:303` | `src/act_comm.c:1948` | 0 | 1 | 0 | 0 | 0 | ❌ | **BCAST-010** — ROM has 1 non-TO_CHAR act() but Python has 0 broadcast hits. Py indicators: (no broadcast hits) |
| 11 | `incognito` | `mud/commands/imm_display.py:54` | `src/act_wiz.c:4375` | 3 | 0 | 0 | 0 | 3 | ✅ FIXED (2.9.58) | **BCAST-011** — Toggle-off (uncloak) had no broadcast; level-set branch had no broadcast. Added `_act_room` calls on both paths. Toggle-on already correct (incognito does not block in-room can_see). Regression: `tests/integration/test_incognito_broadcasts.py` (3/3). |
| 12 | `invis` | `mud/commands/imm_display.py:18` | `src/act_wiz.c:4329` | 3 | 0 | 0 | 0 | 3 | ✅ FIXED (2.9.58) | **BCAST-012** — Pre-fix all three TO_ROOM broadcasts silently dropped: (a) toggle-off said "fades back into existence" vs ROM "fades into existence"; (b) toggle-on and (c) level-set set `invis_level` BEFORE calling `_act_room`, but `_act_room` enforces `can_see_character` so witnesses below trust never saw the fade-out. Re-ordered to broadcast BEFORE invis_level commit + added missing level-set broadcast + fixed wording. Regression: `tests/integration/test_invis_broadcasts.py` (3/3). |
| 13 | `lock` | `mud/commands/doors.py:276` | `src/act_move.c:539` | 3 | 0 | 0 | 0 | 3 | ✅ FIXED (2.9.59) | **BCAST-013** — Pre-fix `do_lock` returned only "*Click*" with zero `broadcast_room` calls. Added portal/container TO_ROOM `$n locks $p.` (act_move.c:622, 655) and door TO_ROOM `$n locks the $d.` (act_move.c:690). ROM does NOT broadcast to the linked room on lock (line 697 silently SET_BITs `pexit_rev->exit_info`); Python pins this asymmetry. Regression: `tests/integration/test_lock_broadcasts.py` (3/3). |
| 14 | `mload` | `mud/commands/imm_load.py:52` | `src/act_wiz.c:2447` | 1 | 0 | 0 | 0 | 0 | ⚠️ BLOCKED by WIZLOAD-001 | **BCAST-014** — ROM has 1 non-TO_CHAR act() but Python has 0 broadcast hits. **Blocked**: `do_mload` cannot reach the broadcast point because its registry lookup (`mud/commands/imm_load.py:68`) reads `registry.mob_prototypes` which doesn't exist (canonical attribute is `mob_registry`). Function always early-returns "No mob has that vnum." See WIZLOAD-001 in the Blocked rows section below. |
| 15 | `oload` | `mud/commands/imm_load.py:95` | `src/act_wiz.c:2479` | 1 | 0 | 0 | 0 | 0 | ⚠️ BLOCKED by WIZLOAD-001 | **BCAST-015** — ROM has 1 non-TO_CHAR act() but Python has 0 broadcast hits. **Blocked**: same root cause as BCAST-014 — `do_oload` (line 121) reads `registry.obj_prototypes` which doesn't exist (canonical: `obj_registry`). Function always early-returns "No object has that vnum." See WIZLOAD-001. |
| 16 | `open` | `mud/commands/doors.py:97` | `src/act_move.c:313` | 3 | 0 | 0 | 0 | 3 | ✅ FIXED (2.9.59) | **BCAST-016** — Pre-fix `do_open` returned only the actor "Ok." / "You open $p." string with zero `broadcast_room` calls. Added portal/container TO_ROOM `$n opens $p.` (act_move.c:384, 412), door TO_ROOM `$n opens the $d.` (act_move.c:436), and linked-room per-person `The $d opens.` (act_move.c:447-448). Regression: `tests/integration/test_door_broadcasts.py` (4/4). |
| 17 | `order` | `mud/commands/group_commands.py:473` | `src/act_comm.c:1650` | 0 | 1 | 0 | 0 | 0 | ❌ | **BCAST-017** — ROM has 1 non-TO_CHAR act() but Python has 0 broadcast hits. Py indicators: (no broadcast hits) |
| 18 | `quit` | `mud/commands/session.py:36` | `src/act_comm.c:1430` | 1 | 0 | 0 | 0 | 1 | ✅ FIXED (2.9.60) | **BCAST-018** — Pre-fix `do_quit` returned "May your travels be safe." and set `_quit_requested`; the room saw nothing. Added TO_ROOM `$n has left the game.` (act_comm.c:1482) via `broadcast_room(room, ..., exclude=ch)` after save but before the disconnect flag. The fight/below-STUNNED guards still short-circuit before the broadcast (matches ROM). Regression: `tests/integration/test_quit_broadcasts.py` (3/3, including 2 negative-pin tests for the blocked-quit paths). |
| 19 | `reply` | `mud/commands/communication.py:244` | `src/act_comm.c:928` | 0 | 1 | 0 | 0 | 0 | ❌ | **BCAST-019** — ROM has 1 non-TO_CHAR act() but Python has 0 broadcast hits. Py indicators: (no broadcast hits) |
| 20 | `report` | `mud/commands/info.py:557` | `src/act_info.c:2588` | 1 | 0 | 0 | 0 | 1 | ✅ COVERED (2.9.60) | **BCAST-020** — FALSE POSITIVE. `mud/commands/info.py:do_report` at lines 583-595 manually iterates `room.people` and `desc.send(room_msg)` to every non-self character with `"$n says 'I have %d/%d hp ...xp.'"` — direct inline TO_ROOM broadcast (no named helper). Equivalent to `broadcast_room(room, msg, exclude=ch)` for the audit's coverage check. |
| 21 | `rest` | `mud/commands/position.py:209` | `src/act_move.c:1078` | 12 | 0 | 0 | 0 | 0 | ❌ | **BCAST-021** — ROM has 12 non-TO_CHAR act() but Python has 0 broadcast hits. Py indicators: (no broadcast hits) |
| 22 | `sit` | `mud/commands/position.py:290` | `src/act_move.c:1217` | 10 | 0 | 0 | 0 | 0 | ❌ | **BCAST-022** — ROM has 10 non-TO_CHAR act() but Python has 0 broadcast hits. Py indicators: (no broadcast hits) |
| 23 | `sleep` | `mud/commands/position.py:371` | `src/act_move.c:1343` | 4 | 0 | 0 | 0 | 0 | ❌ | **BCAST-023** — ROM has 4 non-TO_CHAR act() but Python has 0 broadcast hits. Py indicators: (no broadcast hits) |
| 24 | `stand` | `mud/commands/position.py:111` | `src/act_move.c:967` | 8 | 0 | 0 | 0 | 0 | ❌ | **BCAST-024** — ROM has 8 non-TO_CHAR act() but Python has 0 broadcast hits. Py indicators: (no broadcast hits) |
| 25 | `surrender` | `mud/commands/combat.py:548` | `src/fight.c:3222` | 0 | 1 | 1 | 0 | 2 | ✅ FIXED (2.9.58) | **BCAST-025** — Pre-fix only TO_CHAR was returned; opponent and bystanders got nothing. Added `send_to_char_buffered` delivery of TO_VICT "$n surrenders to you!" and TO_NOTVICT "$n tries to surrender to $N!" before `stop_fighting`. Regression: `tests/integration/test_surrender_broadcasts.py`. |
| 26 | `trip` | `mud/commands/combat.py:880` | `src/fight.c:2501` | 1 | 1 | 1 | 0 | 2 | ✅ COVERED (2.9.59) | **BCAST-026** — FALSE POSITIVE. Probe (2.9.59) confirmed `mud/skills/handlers.py:7691-7701` already emits TO_VICT `"$n trips you..."` via `_send_to_char` and TO_NOTVICT via a manual `room.people` loop. The audit's static scan inspected `combat.py:do_trip` but the broadcasts live in the skill handler. Helper-transitivity caveat. |
| 27 | `unlock` | `mud/commands/doors.py:373` | `src/act_move.c:674` | 3 | 0 | 0 | 0 | 3 | ✅ FIXED (2.9.59) | **BCAST-027** — Pre-fix `do_unlock` returned only "*Click*" with zero `broadcast_room` calls. Added portal/container TO_ROOM `$n unlocks $p.` (act_move.c:757, 790) and door TO_ROOM `$n unlocks the $d.` (act_move.c:825). ROM does NOT broadcast to the linked room on unlock (line 832); Python pins this asymmetry. Symmetric to BCAST-013. Regression: `tests/integration/test_unlock_broadcasts.py` (3/3). |
| 28 | `value` | `mud/commands/shop.py:1018` | `src/act_obj.c:2904` | 0 | 4 | 0 | 0 | 0 | ❌ | **BCAST-028** — ROM has 4 non-TO_CHAR act() but Python has 0 broadcast hits. Py indicators: (no broadcast hits) |
| 29 | `violate` | `mud/commands/imm_server.py:163` | `src/act_wiz.c:968` | 0 | 4 | 0 | 0 | 4 | ✅ COVERED (2.9.60) | **BCAST-029** — FALSE POSITIVE on the *act-emission* axis. `mud/commands/imm_server.py:do_violate` (lines 193-205) calls `_act_room(old_room, char, bamfout_or_default)` and `_act_room(location, char, bamfin_or_default)` — the helper at `imm_commands.py:473-481` iterates `room.people` and delivers to each non-self member. ROM emits 4 per-person TO_VICT acts (bamfout/default × 2 rooms); Python covers the structural equivalent. **Separate fidelity bug noted**: ROM's per-person loop is `get_trust(rch) >= ch->invis_level` gated; Python's `_act_room` has no trust gate, so wiz-invis actors appear in every broadcast regardless of witness trust. Filed as **INV-027 candidate ACT-INVIS-TRUST-GATE** (Watch list, `CROSS_FILE_INVARIANTS_TRACKER.md`). |
| 30 | `bash` | `mud/commands/combat.py:345` | `src/fight.c:2223` | 0 | 2 | 2 | 0 | 1 | ⚠️ | **BCAST-030** — Python broadcast hits (1) < ROM non-TO_CHAR (4). Py indicators: messages.append=1 |
| 31 | `buy` | `mud/commands/shop.py:719` | `src/act_obj.c:2470` | 3 | 6 | 0 | 0 | 3 | ⚠️ | **BCAST-031** — Python broadcast hits (3) < ROM non-TO_CHAR (9). Py indicators: room.broadcast=2 messages.append=1 |
| 32 | `force` | `mud/commands/imm_commands.py:293` | `src/act_wiz.c:4111` | 0 | 4 | 0 | 0 | 1 | ⚠️ | **BCAST-032** — Python broadcast hits (1) < ROM non-TO_CHAR (4). Py indicators: send_to_char_victim=1 |
| 33 | `give` | `mud/commands/give.py:21` | `src/act_obj.c:634` | 0 | 4 | 2 | 0 | 5 | ⚠️ | **BCAST-033** — Python broadcast hits (5) < ROM non-TO_CHAR (6). Py indicators: act_format=3 act(=1 messages.append=1 |
| 34 | `pick` | `mud/commands/doors.py:470` | `src/act_move.c:809` | 3 | 0 | 0 | 0 | 1 | ⚠️ | **BCAST-034** — Python broadcast hits (1) < ROM non-TO_CHAR (3). Py indicators: for_room_people=1 |
| 35 | `purge` | `mud/commands/imm_load.py:160` | `src/act_wiz.c:2532` | 1 | 0 | 2 | 0 | 2 | ⚠️ | **BCAST-035** — Python broadcast hits (2) < ROM non-TO_CHAR (3). Py indicators: for_room_people=1 send_to_char_victim=1 |
| 36 | `recall` | `mud/commands/session.py:328` | `src/act_move.c:1529` | 3 | 0 | 0 | 0 | 2 | ⚠️ | **BCAST-036** — Python broadcast hits (2) < ROM non-TO_CHAR (3). Py indicators: room.broadcast=2 |
| 37 | `sell` | `mud/commands/shop.py:873` | `src/act_obj.c:2810` | 1 | 4 | 0 | 0 | 2 | ⚠️ | **BCAST-037** — Python broadcast hits (2) < ROM non-TO_CHAR (5). Py indicators: room.broadcast=1 messages.append=1 |
| 38 | `steal` | `mud/commands/thief_skills.py:78` | `src/act_obj.c:2126` | 0 | 1 | 1 | 0 | 1 | ⚠️ | **BCAST-038** — Python broadcast hits (1) < ROM non-TO_CHAR (2). Py indicators: broadcast_room=1 |
| 39 | `transfer` | `mud/commands/imm_commands.py:218` | `src/act_wiz.c:772` | 2 | 1 | 0 | 0 | 1 | ⚠️ | **BCAST-039** — Python broadcast hits (1) < ROM non-TO_CHAR (3). Py indicators: send_to_char_victim=1 |
| 40 | `@aedit` | `mud/commands/build.py:1838` | `src/olc.c:660` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 41 | `@asave` | `mud/commands/build.py:1686` | `src/olc_save.c:829` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 42 | `@hedit` | `mud/commands/build.py:4025` | `src/hedit.c:264` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 43 | `@medit` | `mud/commands/build.py:2829` | `src/olc.c:865` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 44 | `@mstat` | `mud/commands/build.py:3866` | `src/act_wiz.c:1511` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 45 | `@oedit` | `mud/commands/build.py:2116` | `src/olc.c:791` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 46 | `@ostat` | `mud/commands/build.py:3805` | `src/act_wiz.c:1187` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 47 | `@redit` | `mud/commands/build.py:1509` | `src/olc.c:710` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 48 | `@rstat` | `mud/commands/build.py:3734` | `src/act_wiz.c:1090` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 49 | `@who` | `mud/commands/admin_commands.py:27` | `src/act_info.c:1964` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 50 | `advance` | `mud/commands/imm_admin.py:19` | `src/act_wiz.c:2610` | 0 | 0 | 0 | 0 | 3 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered. Py: send_to_char_victim=3 |
| 51 | `aedit` | `mud/commands/build.py:1838` | `src/olc.c:660` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 52 | `affects` | `mud/commands/affects.py:122` | `src/act_info.c:1670` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 53 | `afk` | `mud/commands/misc_player.py:22` | `src/act_comm.c:219` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 54 | `alia` | `mud/commands/typo_guards.py:60` | `src/alias.c:82` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 55 | `alias` | `mud/commands/alias_cmds.py:59` | `src/alias.c:88` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 56 | `alist` | `mud/commands/imm_olc.py:422` | `src/olc.c:1397` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 57 | `allow` | `mud/commands/admin_commands.py:319` | `src/ban.c:243` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 58 | `answer` | `mud/commands/communication.py:471` | `src/act_comm.c:539` | 0 | 1 | 0 | 0 | 1 | ✅ | Python hits (1) ≥ ROM (1) — shallow OK. Py: broadcast_global=1 |
| 59 | `asave` | `mud/commands/build.py:1686` | `src/olc_save.c:829` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 60 | `at` | `mud/commands/imm_commands.py:115` | `src/act_wiz.c:853` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 61 | `auction` | `mud/commands/communication.py:311` | `src/act_comm.c:253` | 0 | 1 | 0 | 0 | 1 | ✅ | Python hits (1) ≥ ROM (1) — shallow OK. Py: broadcast_global=1 |
| 62 | `autoall` | `mud/commands/auto_settings.py:67` | `src/act_info.c:804` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 63 | `autoassist` | `mud/commands/auto_settings.py:103` | `src/act_info.c:702` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 64 | `autoexit` | `mud/commands/auto_settings.py:122` | `src/act_info.c:719` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 65 | `autogold` | `mud/commands/auto_settings.py:141` | `src/act_info.c:736` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 66 | `autolist` | `mud/commands/auto_settings.py:14` | `src/act_info.c:617` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 67 | `autoloot` | `mud/commands/auto_settings.py:160` | `src/act_info.c:753` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 68 | `autosac` | `mud/commands/auto_settings.py:179` | `src/act_info.c:770` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 69 | `autosplit` | `mud/commands/auto_settings.py:198` | `src/act_info.c:787` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 70 | `backstab` | `mud/commands/combat.py:286` | `src/fight.c:2746` | 0 | 0 | 0 | 0 | 1 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered. Py: messages.append=1 |
| 71 | `ban` | `mud/commands/admin_commands.py:311` | `src/ban.c:233` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 72 | `berserk` | `mud/commands/combat.py:473` | `src/fight.c:2134` | 1 | 0 | 0 | 0 | 1 | ✅ | Python hits (1) ≥ ROM (1) — shallow OK. Py: messages.append=1 |
| 73 | `board` | `mud/commands/notes.py:202` | `src/board.c:696` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 74 | `brandish` | `mud/commands/magic_items.py:182` | `src/act_obj.c:1943` | 3 | 0 | 0 | 0 | 6 | ✅ | Python hits (6) ≥ ROM (3) — shallow OK. Py: act_format=5 for_room_people=1 |
| 75 | `brief` | `mud/commands/auto_settings.py:217` | `src/act_info.c:835` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 76 | `bug` | `mud/commands/feedback.py:54` | `src/act_comm.c:1401` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 77 | `cast` | `mud/commands/combat.py:704` | `src/magic.c:264` | 0 | 0 | 0 | 0 | 1 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered. Py: messages.append=1 |
| 78 | `channels` | `mud/commands/channels.py:26` | `src/act_comm.c:74` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 79 | `clan` | `mud/commands/communication.py:535` | `src/act_comm.c:654` | 0 | 1 | 0 | 0 | 1 | ✅ | Python hits (1) ≥ ROM (1) — shallow OK. Py: broadcast_global=1 |
| 80 | `clantalk` | `mud/commands/communication.py:535` | `src/act_comm.c:654` | 0 | 1 | 0 | 0 | 1 | ✅ | Python hits (1) ≥ ROM (1) — shallow OK. Py: broadcast_global=1 |
| 81 | `colour` | `mud/commands/auto_settings.py:322` | `src/act_comm.c:1990` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 82 | `combine` | `mud/commands/auto_settings.py:249` | `src/act_info.c:916` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 83 | `compact` | `mud/commands/auto_settings.py:233` | `src/act_info.c:849` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 84 | `compare` | `mud/commands/compare.py:15` | `src/act_info.c:2230` | 0 | 0 | 0 | 0 | 2 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered. Py: act_format=1 act(=1 |
| 85 | `consider` | `mud/commands/consider.py:13` | `src/act_info.c:2402` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 86 | `copyover` | `mud/commands/imm_server.py:92` | `src/act_wiz.c:4412` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 87 | `count` | `mud/commands/info_extended.py:112` | `src/act_info.c:2161` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 88 | `credits` | `mud/commands/info.py:530` | `src/act_info.c:2332` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 89 | `deaf` | `mud/commands/remaining_rom.py:139` | `src/act_comm.c:185` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 90 | `delet` | `mud/commands/player_config.py:158` | `src/act_comm.c:25` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 91 | `delete` | `mud/commands/player_config.py:95` | `src/act_comm.c:31` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 92 | `deny` | `mud/commands/admin_commands.py:458` | `src/act_wiz.c:490` | 0 | 0 | 0 | 0 | 1 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered. Py: send_to_char_victim=1 |
| 93 | `description` | `mud/commands/character.py:136` | `src/act_info.c:2509` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 94 | `disconnect` | `mud/commands/imm_punish.py:208` | `src/act_wiz.c:534` | 0 | 0 | 0 | 0 | 1 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered. Py: act(=1 |
| 95 | `down` | `mud/commands/movement.py:43` | `src/act_move.c:258` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 96 | `drink` | `mud/commands/consumption.py:148` | `src/act_obj.c:1132` | 2 | 0 | 0 | 0 | 6 | ✅ | Python hits (6) ≥ ROM (2) — shallow OK. Py: broadcast_room=2 act_format=2 act(=2 |
| 97 | `drop` | `mud/commands/inventory.py:594` | `src/act_obj.c:471` | 5 | 0 | 0 | 0 | 10 | ✅ | Python hits (10) ≥ ROM (5) — shallow OK. Py: broadcast_room=5 act_format=5 |
| 98 | `east` | `mud/commands/movement.py:31` | `src/act_move.c:226` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 99 | `eat` | `mud/commands/consumption.py:21` | `src/act_obj.c:1255` | 2 | 0 | 0 | 0 | 4 | ✅ | Python hits (4) ≥ ROM (2) — shallow OK. Py: broadcast_room=2 act_format=2 |
| 100 | `echo` | `mud/commands/imm_display.py:146` | `src/act_wiz.c:647` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 101 | `emote` | `mud/commands/communication.py:595` | `src/act_comm.c:1041` | 1 | 0 | 0 | 0 | 6 | ✅ | Python hits (6) ≥ ROM (1) — shallow OK. Py: act(=5 messages.append=1 |
| 102 | `equipment` | `mud/commands/inventory.py:834` | `src/act_info.c:2196` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 103 | `examine` | `mud/commands/info_extended.py:14` | `src/act_info.c:1278` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 104 | `exits` | `mud/commands/inspection.py:141` | `src/act_info.c:1349` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 105 | `fill` | `mud/commands/liquids.py:15` | `src/act_obj.c:936` | 1 | 0 | 0 | 0 | 3 | ✅ | Python hits (3) ≥ ROM (1) — shallow OK. Py: broadcast_room=1 act_format=1 act(=1 |
| 106 | `flag` | `mud/commands/remaining_rom.py:401` | `src/flags.c:21` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 107 | `flee` | `mud/commands/combat.py:587` | `src/fight.c:2820` | 1 | 0 | 0 | 0 | 1 | ✅ | Python hits (1) ≥ ROM (1) — shallow OK. Py: messages.append=1 |
| 108 | `follow` | `mud/commands/group_commands.py:109` | `src/act_comm.c:1502` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 109 | `freeze` | `mud/commands/imm_admin.py:106` | `src/act_wiz.c:2824` | 0 | 0 | 0 | 0 | 2 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered. Py: send_to_char_victim=2 |
| 110 | `gain` | `mud/commands/remaining_rom.py:189` | `src/skills.c:21` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 111 | `get` | `mud/commands/inventory.py:386` | `src/act_obj.c:170` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 112 | `gossip` | `mud/commands/communication.py:343` | `src/act_comm.c:310` | 0 | 1 | 0 | 0 | 1 | ✅ | Python hits (1) ≥ ROM (1) — shallow OK. Py: broadcast_global=1 |
| 113 | `grats` | `mud/commands/communication.py:375` | `src/act_comm.c:367` | 0 | 1 | 0 | 0 | 1 | ✅ | Python hits (1) ≥ ROM (1) — shallow OK. Py: broadcast_global=1 |
| 114 | `groups` | `mud/commands/remaining_rom.py:261` | `src/skills.c:827` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 115 | `guild` | `mud/commands/remaining_rom.py:355` | `src/act_wiz.c:169` | 0 | 0 | 0 | 0 | 3 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered. Py: send_to_char_victim=3 |
| 116 | `heal` | `mud/commands/healer.py:204` | `src/healer.c:18` | 1 | 0 | 0 | 0 | 1 | ✅ | Python hits (1) ≥ ROM (1) — shallow OK. Py: broadcast_room=1 |
| 117 | `hedit` | `mud/commands/build.py:4025` | `src/hedit.c:264` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 118 | `help` | `mud/commands/help.py:252` | `src/act_info.c:1788` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 119 | `hide` | `mud/commands/thief_skills.py:38` | `src/act_move.c:1494` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 120 | `holylight` | `mud/commands/admin_commands.py:412` | `src/act_wiz.c:4345` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 121 | `immtalk` | `mud/commands/communication.py:566` | `src/act_comm.c:707` | 0 | 1 | 0 | 0 | 1 | ✅ | Python hits (1) ≥ ROM (1) — shallow OK. Py: broadcast_global=1 |
| 122 | `imotd` | `mud/commands/misc_info.py:23` | `src/act_info.c:595` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 123 | `inventory` | `mud/commands/inventory.py:818` | `src/act_info.c:2187` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 124 | `kick` | `mud/commands/combat.py:132` | `src/fight.c:2955` | 0 | 0 | 0 | 0 | 1 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered. Py: messages.append=1 |
| 125 | `kill` | `mud/commands/combat.py:94` | `src/fight.c:2618` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 126 | `list` | `mud/commands/shop.py:636` | `src/act_obj.c:2712` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 127 | `load` | `mud/commands/imm_load.py:18` | `src/act_wiz.c:2417` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 128 | `log` | `mud/commands/admin_commands.py:352` | `src/act_wiz.c:2879` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 129 | `look` | `mud/commands/inspection.py:125` | `src/act_info.c:995` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 130 | `medit` | `mud/commands/build.py:2829` | `src/olc.c:865` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 131 | `mfind` | `mud/commands/imm_search.py:88` | `src/act_wiz.c:1753` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 132 | `mob` | `mud/commands/remaining_rom.py:507` | `src/mob_cmds.c:51` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 133 | `motd` | `mud/commands/misc_info.py:11` | `src/act_info.c:590` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 134 | `mpdump` | `mud/commands/mobprog_tools.py:126` | `src/mob_cmds.c:189` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 135 | `mpedit` | `mud/commands/imm_olc.py:517` | `src/olc_mpcode.c:96` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 136 | `mpstat` | `mud/commands/mobprog_tools.py:100` | `src/mob_cmds.c:125` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 137 | `mset` | `mud/commands/imm_set.py:48` | `src/act_wiz.c:3303` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 138 | `mstat` | `mud/commands/build.py:3866` | `src/act_wiz.c:1511` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 139 | `murde` | `mud/commands/typo_guards.py:27` | `src/fight.c:2673` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 140 | `murder` | `mud/commands/murder.py:28` | `src/fight.c:2681` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 141 | `music` | `mud/commands/communication.py:503` | `src/act_comm.c:596` | 0 | 1 | 0 | 0 | 1 | ✅ | Python hits (1) ≥ ROM (1) — shallow OK. Py: broadcast_global=1 |
| 142 | `mwhere` | `mud/commands/imm_search.py:240` | `src/act_wiz.c:1908` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 143 | `newlock` | `mud/commands/admin_commands.py:70` | `src/act_wiz.c:3121` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 144 | `nochannels` | `mud/commands/imm_punish.py:19` | `src/act_wiz.c:287` | 0 | 0 | 0 | 0 | 2 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered. Py: send_to_char_victim=2 |
| 145 | `noemote` | `mud/commands/imm_punish.py:55` | `src/act_wiz.c:2936` | 0 | 0 | 0 | 0 | 2 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered. Py: send_to_char_victim=2 |
| 146 | `nofollow` | `mud/commands/player_config.py:38` | `src/act_info.c:947` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 147 | `noloot` | `mud/commands/player_config.py:17` | `src/act_info.c:930` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 148 | `north` | `mud/commands/movement.py:23` | `src/act_move.c:218` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 149 | `noshout` | `mud/commands/imm_punish.py:91` | `src/act_wiz.c:2984` | 0 | 0 | 0 | 0 | 2 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered. Py: send_to_char_victim=2 |
| 150 | `nosummon` | `mud/commands/player_config.py:63` | `src/act_info.c:965` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 151 | `note` | `mud/commands/notes.py:253` | `src/board.c:662` | 0 | 0 | 0 | 0 | 4 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered. Py: room.broadcast=2 act(=2 |
| 152 | `notell` | `mud/commands/imm_punish.py:130` | `src/act_wiz.c:3037` | 0 | 0 | 0 | 0 | 2 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered. Py: send_to_char_victim=2 |
| 153 | `oedit` | `mud/commands/build.py:2116` | `src/olc.c:791` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 154 | `ofind` | `mud/commands/imm_search.py:118` | `src/act_wiz.c:1799` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 155 | `oset` | `mud/commands/imm_set.py:366` | `src/act_wiz.c:3900` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 156 | `ostat` | `mud/commands/build.py:3805` | `src/act_wiz.c:1187` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 157 | `outfit` | `mud/commands/inventory.py:896` | `src/act_wiz.c:224` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 158 | `owhere` | `mud/commands/imm_search.py:181` | `src/act_wiz.c:1844` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 159 | `pardon` | `mud/commands/imm_punish.py:166` | `src/act_wiz.c:592` | 0 | 0 | 0 | 0 | 2 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered. Py: send_to_char_victim=2 |
| 160 | `password` | `mud/commands/character.py:20` | `src/act_info.c:2761` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 161 | `peace` | `mud/commands/imm_commands.py:392` | `src/act_wiz.c:3084` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 162 | `pecho` | `mud/commands/imm_display.py:257` | `src/act_wiz.c:723` | 0 | 0 | 0 | 0 | 2 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered. Py: send_to_char_victim=2 |
| 163 | `permban` | `mud/commands/admin_commands.py:315` | `src/ban.c:238` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 164 | `play` | `mud/commands/player_info.py:67` | `src/music.c:197` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 165 | `pmote` | `mud/commands/imm_emote.py:171` | `src/act_comm.c:1070` | 0 | 0 | 0 | 0 | 1 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered. Py: act(=1 |
| 166 | `pose` | `mud/commands/communication.py:647` | `src/act_comm.c:1379` | 1 | 0 | 0 | 0 | 4 | ✅ | Python hits (4) ≥ ROM (1) — shallow OK. Py: broadcast_room=1 act_format=3 |
| 167 | `pour` | `mud/commands/liquids.py:107` | `src/act_obj.c:1004` | 2 | 1 | 1 | 0 | 6 | ✅ | Python hits (6) ≥ ROM (4) — shallow OK. Py: broadcast_room=1 act_format=3 messages.append=2 |
| 168 | `practice` | `mud/commands/advancement.py:66` | `src/act_info.c:2610` | 2 | 0 | 0 | 0 | 4 | ✅ | Python hits (4) ≥ ROM (2) — shallow OK. Py: room.broadcast=2 messages.append=2 |
| 169 | `prefi` | `mud/commands/alias_cmds.py:120` | `src/act_wiz.c:4366` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 170 | `prefix` | `mud/commands/alias_cmds.py:126` | `src/act_wiz.c:4372` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 171 | `prompt` | `mud/commands/auto_settings.py:391` | `src/act_info.c:877` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 172 | `protect` | `mud/commands/imm_server.py:131` | `src/act_wiz.c:2044` | 0 | 0 | 0 | 0 | 2 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered. Py: send_to_char_victim=2 |
| 173 | `put` | `mud/commands/obj_manipulation.py:63` | `src/act_obj.c:321` | 4 | 0 | 0 | 0 | 8 | ✅ | Python hits (8) ≥ ROM (4) — shallow OK. Py: broadcast_room=4 act_format=4 |
| 174 | `qmconfig` | `mud/commands/admin_commands.py:96` | `src/act_wiz.c:4599` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 175 | `quaff` | `mud/commands/obj_manipulation.py:483` | `src/act_obj.c:1830` | 1 | 0 | 0 | 0 | 3 | ✅ | Python hits (3) ≥ ROM (1) — shallow OK. Py: broadcast_room=1 act_format=1 act(=1 |
| 176 | `question` | `mud/commands/communication.py:439` | `src/act_comm.c:482` | 0 | 1 | 0 | 0 | 1 | ✅ | Python hits (1) ≥ ROM (1) — shallow OK. Py: broadcast_global=1 |
| 177 | `qui` | `mud/commands/typo_guards.py:16` | `src/act_comm.c:1422` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 178 | `quiet` | `mud/commands/remaining_rom.py:157` | `src/act_comm.c:202` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 179 | `quote` | `mud/commands/communication.py:407` | `src/act_comm.c:424` | 0 | 1 | 0 | 0 | 1 | ✅ | Python hits (1) ≥ ROM (1) — shallow OK. Py: broadcast_global=1 |
| 180 | `read` | `mud/commands/info_extended.py:99` | `src/act_info.c:1273` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 181 | `reboo` | `mud/commands/typo_guards.py:38` | `src/act_wiz.c:1977` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 182 | `reboot` | `mud/commands/imm_server.py:26` | `src/act_wiz.c:1985` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 183 | `recho` | `mud/commands/imm_display.py:178` | `src/act_wiz.c:673` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 184 | `recite` | `mud/commands/magic_items.py:110` | `src/act_obj.c:1875` | 1 | 0 | 0 | 0 | 3 | ✅ | Python hits (3) ≥ ROM (1) — shallow OK. Py: act_format=2 act(=1 |
| 185 | `redit` | `mud/commands/build.py:1509` | `src/olc.c:710` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 186 | `remove` | `mud/commands/obj_manipulation.py:281` | `src/act_obj.c:1705` | 0 | 0 | 0 | 0 | 2 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered. Py: act(=2 |
| 187 | `rent` | `mud/commands/misc_info.py:271` | `src/act_comm.c:1415` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 188 | `replay` | `mud/commands/misc_player.py:42` | `src/act_comm.c:234` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 189 | `rescue` | `mud/commands/combat.py:193` | `src/fight.c:2882` | 0 | 1 | 1 | 0 | 2 | ✅ | Python hits (2) ≥ ROM (2) — shallow OK. Py: messages.append=2 |
| 190 | `resets` | `mud/commands/imm_olc.py:238` | `src/olc.c:1182` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 191 | `restore` | `mud/commands/imm_load.py:230` | `src/act_wiz.c:2737` | 0 | 3 | 0 | 0 | 3 | ✅ | Python hits (3) ≥ ROM (3) — shallow OK. Py: send_to_char_victim=3 |
| 192 | `return` | `mud/commands/imm_admin.py:275` | `src/act_wiz.c:2231` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 193 | `rset` | `mud/commands/imm_set.py:442` | `src/act_wiz.c:4007` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 194 | `rstat` | `mud/commands/build.py:3734` | `src/act_wiz.c:1090` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 195 | `rules` | `mud/commands/misc_info.py:33` | `src/act_info.c:600` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 196 | `sacrifice` | `mud/commands/obj_manipulation.py:378` | `src/act_obj.c:1730` | 2 | 0 | 0 | 0 | 5 | ✅ | Python hits (5) ≥ ROM (2) — shallow OK. Py: broadcast_room=2 act_format=2 for_room_people=1 |
| 197 | `save` | `mud/commands/session.py:18` | `src/act_comm.c:1488` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 198 | `say` | `mud/commands/communication.py:140` | `src/act_comm.c:745` | 1 | 0 | 0 | 0 | 3 | ✅ | Python hits (3) ≥ ROM (1) — shallow OK. Py: act(=2 messages.append=1 |
| 199 | `scan` | `mud/commands/inspection.py:10` | `src/scan.c:25` | 2 | 0 | 0 | 0 | 7 | ✅ | Python hits (7) ≥ ROM (2) — shallow OK. Py: broadcast_room=2 act(=4 for_room_people=1 |
| 200 | `score` | `mud/commands/session.py:62` | `src/act_info.c:1433` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 201 | `scroll` | `mud/commands/player_info.py:13` | `src/act_info.c:517` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 202 | `set` | `mud/commands/imm_set.py:13` | `src/act_wiz.c:3183` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 203 | `shout` | `mud/commands/communication.py:255` | `src/act_comm.c:772` | 0 | 1 | 0 | 0 | 6 | ✅ | Python hits (6) ≥ ROM (1) — shallow OK. Py: broadcast_global=1 act(=3 messages.append=1 send_to_char_victim=1 |
| 204 | `show` | `mud/commands/player_info.py:49` | `src/act_info.c:863` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 205 | `shutdow` | `mud/commands/typo_guards.py:49` | `src/act_wiz.c:2011` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 206 | `shutdown` | `mud/commands/imm_server.py:58` | `src/act_wiz.c:2017` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 207 | `skills` | `mud/commands/misc_info.py:173` | `src/skills.c:358` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 208 | `sla` | `mud/commands/imm_load.py:350` | `src/fight.c:3094` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 209 | `slay` | `mud/commands/imm_load.py:296` | `src/fight.c:3102` | 0 | 1 | 1 | 0 | 2 | ✅ | Python hits (2) ≥ ROM (2) — shallow OK. Py: act(=1 send_to_char_victim=1 |
| 210 | `slookup` | `mud/commands/imm_search.py:148` | `src/act_wiz.c:3141` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 211 | `smote` | `mud/commands/imm_emote.py:25` | `src/act_wiz.c:335` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 212 | `sneak` | `mud/commands/thief_skills.py:17` | `src/act_move.c:1464` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 213 | `snoop` | `mud/commands/imm_admin.py:147` | `src/act_wiz.c:2078` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 214 | `socials` | `mud/commands/misc_info.py:53` | `src/act_info.c:565` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 215 | `sockets` | `mud/commands/imm_search.py:302` | `src/act_wiz.c:4070` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 216 | `south` | `mud/commands/movement.py:27` | `src/act_move.c:234` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 217 | `spells` | `mud/commands/misc_info.py:221` | `src/skills.c:233` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 218 | `split` | `mud/commands/group_commands.py:337` | `src/act_comm.c:1827` | 0 | 1 | 0 | 0 | 1 | ✅ | Python hits (1) ≥ ROM (1) — shallow OK. Py: messages.append=1 |
| 219 | `sset` | `mud/commands/imm_set.py:305` | `src/act_wiz.c:3228` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 220 | `stat` | `mud/commands/imm_search.py:501` | `src/act_wiz.c:1027` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 221 | `story` | `mud/commands/misc_info.py:43` | `src/act_info.c:605` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 222 | `string` | `mud/commands/imm_set.py:489` | `src/act_wiz.c:3735` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 223 | `switch` | `mud/commands/imm_admin.py:198` | `src/act_wiz.c:2160` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 224 | `tell` | `mud/commands/communication.py:183` | `src/act_comm.c:822` | 0 | 1 | 0 | 0 | 2 | ✅ | Python hits (2) ≥ ROM (1) — shallow OK. Py: act(=2 |
| 225 | `telnetga` | `mud/commands/auto_settings.py:456` | `src/act_info.c:2831` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 226 | `time` | `mud/commands/info.py:401` | `src/act_info.c:1727` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 227 | `title` | `mud/commands/character.py:106` | `src/act_info.c:2480` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 228 | `train` | `mud/commands/advancement.py:236` | `src/act_move.c:1598` | 3 | 0 | 0 | 0 | 6 | ✅ | Python hits (6) ≥ ROM (3) — shallow OK. Py: room.broadcast=3 act(=3 |
| 229 | `trust` | `mud/commands/imm_admin.py:68` | `src/act_wiz.c:2695` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 230 | `typo` | `mud/commands/feedback.py:82` | `src/act_comm.c:1408` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 231 | `up` | `mud/commands/movement.py:39` | `src/act_move.c:250` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 232 | `visible` | `mud/commands/thief_skills.py:57` | `src/act_move.c:1515` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 233 | `vnum` | `mud/commands/imm_search.py:48` | `src/act_wiz.c:1714` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 234 | `wake` | `mud/commands/position.py:426` | `src/act_move.c:1421` | 0 | 1 | 0 | 0 | 5 | ✅ | Python hits (5) ≥ ROM (1) — shallow OK. Py: act_format=3 messages.append=1 send_to_char_victim=1 |
| 235 | `wear` | `mud/commands/equipment.py:121` | `src/act_obj.c:1664` | 0 | 0 | 0 | 0 | 4 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered. Py: broadcast_room=3 act_format=1 |
| 236 | `weather` | `mud/commands/info.py:488` | `src/act_info.c:1762` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 237 | `west` | `mud/commands/movement.py:35` | `src/act_move.c:242` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 238 | `where` | `mud/commands/info.py:272` | `src/act_info.c:2340` | 0 | 0 | 0 | 0 | 3 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered. Py: act_format=2 act(=1 |
| 239 | `who` | `mud/commands/info.py:79` | `src/act_info.c:1964` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 240 | `whois` | `mud/commands/info_extended.py:142` | `src/act_info.c:1866` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 241 | `wimpy` | `mud/commands/remaining_rom.py:108` | `src/act_info.c:2728` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 242 | `wizlist` | `mud/commands/help.py:347` | `src/act_info.c:610` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 243 | `wizlock` | `mud/commands/admin_commands.py:60` | `src/act_wiz.c:3100` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 244 | `wiznet` | `(not found)` | `src/act_wiz.c:40` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered. Py: (no Python body found) |
| 245 | `worth` | `mud/commands/info_extended.py:265` | `src/act_info.c:1409` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 246 | `yell` | `mud/commands/communication.py:685` | `src/act_comm.c:1007` | 0 | 1 | 0 | 0 | 4 | ✅ | Python hits (4) ≥ ROM (1) — shallow OK. Py: act(=3 send_to_char_victim=1 |
| 247 | `zap` | `mud/commands/magic_items.py:263` | `src/act_obj.c:2033` | 3 | 1 | 1 | 0 | 10 | ✅ | Python hits (10) ≥ ROM (5) — shallow OK. Py: act_format=10 |
| 248 | `zecho` | `mud/commands/imm_display.py:215` | `src/act_wiz.c:699` | 0 | 0 | 0 | 0 | 0 | ✅ | ROM emits no non-TO_CHAR act() — trivially covered |
| 249 | `@hesave` | `mud/commands/build.py:4327` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 250 | `@spawn` | `mud/commands/admin_commands.py:48` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 251 | `@teleport` | `mud/commands/admin_commands.py:36` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 252 | `@vlist` | `mud/commands/build.py:3955` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 253 | `areas` | `mud/commands/info.py:243` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 254 | `bamfin` | `mud/commands/imm_display.py:84` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 255 | `bamfout` | `mud/commands/imm_display.py:115` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 256 | `banlist` | `mud/commands/admin_commands.py:348` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 257 | `bs` | `mud/commands/remaining_rom.py:532` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 258 | `cgossip` | `mud/commands/communication.py:737` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 259 | `color` | `(not found)` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 260 | `commands` | `mud/commands/info.py:59` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 261 | `config` | `mud/commands/misc_player.py:68` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 262 | `dump` | `mud/commands/imm_server.py:212` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 263 | `edit` | `mud/commands/imm_olc.py:456` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 264 | `empty` | `mud/commands/liquids.py:296` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 265 | `gecho` | `mud/commands/imm_emote.py:208` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 266 | `hesave` | `mud/commands/build.py:4327` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 267 | `idea` | `mud/commands/feedback.py:68` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 268 | `imc` | `mud/commands/imc.py:38` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 269 | `info` | `mud/commands/player_info.py:211` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 270 | `memory` | `mud/commands/imm_search.py:343` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 271 | `olc` | `mud/commands/imm_olc.py:456` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 272 | `peek` | `mud/commands/misc_player.py:157` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 273 | `permit` | `mud/commands/misc_player.py:110` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 274 | `poofin` | `mud/commands/imm_display.py:84` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 275 | `poofout` | `mud/commands/imm_display.py:115` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 276 | `qmread` | `mud/commands/remaining_rom.py:578` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 277 | `teleport` | `mud/commands/remaining_rom.py:543` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 278 | `unalias` | `mud/commands/alias_cmds.py:100` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 279 | `unban` | `mud/commands/admin_commands.py:343` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 280 | `unread` | `mud/commands/misc_player.py:217` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 281 | `vlist` | `mud/commands/build.py:3955` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 282 | `wizhelp` | `mud/commands/info.py:69` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |
| 283 | `wizinvis` | `mud/commands/imm_display.py:49` | `(no ROM do_* match)` | 0 | 0 | 0 | 0 | 0 | N/A | No ROM C counterpart (Python-only or admin utility) |

## Summary

| Metric | Count |
|--------|-------|
| Commands audited | 283 of ~284 dispatcher slots (all unique handler names) |
| ROM `act()` non-TO_CHAR sites scanned | 205 |
| ✅ COVERED | 209 (73%) |
| ⚠️ PARTIAL | 10 |
| ❌ MISSING | 29 |
| N/A (no ROM counterpart) | 35 |

## Caveats

- **Indicator-count parity ≠ behavioral parity.** A ✅ row only means the regex-counted broadcast helpers in the Python body sum to ≥ the ROM `act()` non-TO_CHAR count. It does **not** guarantee each ROM site has a matching Python site on the same code path, with the right target, template, or position floor. Treat ✅ rows as 'no obvious deficit' — every ⚠️/❌ row is a confirmed concern.
- **Helper hiding.** Some Python paths call into helpers that broadcast (e.g. `open_obj`/`close_obj` in `mud/world/movement.py`, `extract_obj`, `damage()`, `stop_follower`, `act_format` in `mud/utils/act.py`). The indicator scan walks only the `do_*` body, not transitively. A ❌ may still be covered when the body delegates to a helper that broadcasts — manual confirmation required before filing each `BCAST-NNN` as a real gap. Door commands (`open`/`close`/`lock`/`unlock`) are the canonical case: ROM emits the broadcast inline; Python factored it into helpers — check `mud/world/movement.py` before treating the ❌ rows as gaps.
- **Position commands.** `do_rest`/`do_sit`/`do_sleep`/`do_stand` have ROM broadcast-per-furniture-state branches (8–12 sites in one switch). Python may use a single position-transition helper that selects the message via a lookup. These ❌ rows are most likely real gaps but need to be checked against any position-helper module.
- **Combat-skill commands.** `do_bash`/`do_trip`/`do_dirt`/`do_disarm`/`do_surrender`/`do_rescue` — ROM emits the hit/miss broadcasts directly via `act()`. In Python the broadcast may be delegated to `damage()` / `one_hit()` / the combat engine. Worth a deep verification before promoting to `fix(parity)` commits.
- **`@goto` alias.** Same handler as `cmd_goto` (admin variant). Counts as one gap, not two — the ❌ row is bookkeeping for the admin path.

## Top gap candidates (priority for next session)

Ranked by user-visible impact and likelihood the ❌/⚠️ is a real gap (not a helper-hidden hit):

1. **`do_group` — `act_comm.c:1736`** (R=0 V=3 NV=2, Py=0) — ROM emits TO_VICT + TO_NOTVICT on add and remove. INV-016/SINGLE-DELIVERY-adjacent. *Note: 2.9.20 already shipped a fix per the draft sketch; the regex misses it because the Python broadcast may live in a helper. Re-verify whether `do_group` body or its helper now emits.*
2. **`do_disarm` / `do_trip` / `do_dirt` / `do_surrender` — `fight.c`** — every combat skill has TO_VICT + TO_NOTVICT broadcasts (the hit-feedback for victim and bystanders). If these route through `damage()` they are covered; otherwise each is a 2-broadcast gap visible to bystanders.
3. **`do_reply` — `act_comm.c:928`** (V=1, Py=0) — ROM sends `$N tells you '$T'` TO_VICT. Python's `do_tell` was fixed in 2.9.17; `do_reply` shares the contract and may have been missed.
4. **`do_buy` / `do_sell` — `act_obj.c:2470/2810`** (V=6/4, Py=3/2 — ⚠️) — Pet-shop branch in `do_buy` emits TO_VICT for the new pet's owner; shopkeeper-vict broadcasts may be missing. 2.9.18 fixed the TO_ROOM half; the TO_VICT half is incompletely covered.
5. **`do_goto` / `@goto` — `act_wiz.c:905`** (V=4, Py=0) — ROM emits poofin / `$n appears in the room.` TO_VICT for occupants of the destination, plus poofout for origin. Immortal command — bystanders see the wrong (or no) movement narration.
6. **`do_violate` / `do_force` — `act_wiz.c:968/4111`** (V=4 each, Py=0–1) — admin-broadcasts the action to the target. Used for moderation; missing broadcast = no audit trail to the affected player.
7. **`do_invis` / `do_incognito` — `act_wiz.c:4252/4298`** (R=3, Py=0) — ROM emits 'X slowly fades into thin air.' TO_ROOM (and inverse on visible). Immortal visibility transition; bystanders are silently surprised.
8. **`do_envenom` — `act_obj.c:820`** (R=2, Py=0) — TO_ROOM `$n coats $p with deadly venom.` Plain-sight skill that ROM publishes; Python silently succeeds.
9. **`do_value` — `act_obj.c:2904`** (V=4, Py=0) — shopkeeper TO_VICT haggling responses. Player-facing but cosmetic.
10. **`do_quit` — `act_comm.c:1430`** (R=1, Py=0) — ROM emits `$n has left the game.` TO_ROOM. Currently Python may rely on a session-close event; if so, bystanders may not see the departure broadcast in real time.

## Blocked rows

Pre-existing parity bugs that prevent the listed BCAST rows from being closed via the normal `rom-gap-closer` path. Surface these in the next-session SUMMARY's "Outstanding" so they get picked up.

### WIZLOAD-001 — wiz-load/clone surface registry+import name mismatches (surfaced 2026-05-27, expanded same day)

Three layered name bugs in the wiz-load/clone command cluster, all surfaced
during the Class 1 BCAST burn-down. Each is silent: either an empty
`getattr` default short-circuits before the broken line, or the inline
import sits in a never-reached branch in test coverage.

**Bug 1 — `do_mload` registry-lookup name typo** (`mud/commands/imm_load.py:68`):
- Reads `getattr(registry, "mob_prototypes", {}).get(vnum)`. Attribute
  doesn't exist on `mud/registry.py` (canonical: `mob_registry`).
- `do_mload(char, "<any vnum>")` always returns `"No mob has that vnum."`.

**Bug 2 — `do_oload` registry-lookup name typo + double-broken import**
(`mud/commands/imm_load.py:121, 126-127`):
- Line 121: reads `getattr(registry, "obj_prototypes", {}).get(vnum)`.
  Attribute doesn't exist (canonical: `obj_registry`).
- Lines 126-127: imports `spawn_obj` from `mud.spawning.obj_spawner` and
  calls `spawn_obj(vnum, level)`. The function is named `spawn_object`,
  takes only `vnum` (no `level` arg). `do_oload` would `ImportError`
  even if the registry lookup were fixed.

**Bug 3 — `do_clone` object-branch broken import**
(`mud/commands/imm_search.py:417, 424`):
- Same `spawn_obj` ImportError as Bug 2. Mob branch (line 472, `spawn_mob`)
  is fine — `spawn_mob` exists.

**ROM C references**: `src/act_wiz.c:2510 do_mload`,
`src/act_wiz.c:2553 do_oload`, `src/act_wiz.c:2397 do_clone` (obj branch).

**Blocks**: BCAST-014 (do_mload), BCAST-015 (do_oload), BCAST-002
(do_clone object branch — mob branch unblocked but still ⚠️ until both
paths can be closed in one row flip).

**Fix shape** (one commit per bug, or one bundle since they all live in
two adjacent files):
1. `imm_load.py:65` → `from mud.registry import mob_registry`; line 68 →
   `mob_index = mob_registry.get(vnum)`. Drop the `getattr` defensive
   wrapper.
2. `imm_load.py:118` → `from mud.registry import obj_registry`; line 121
   → `obj_index = obj_registry.get(vnum)`; line 126 → `from
   mud.spawning.obj_spawner import spawn_object`; line 127 → `obj =
   spawn_object(vnum)`. Drop the unused `level` arg from the call;
   `spawn_object` doesn't accept it. The `level` variable computed
   upstream becomes dead code (`do_oload` ROM behavior re-applies
   level post-spawn via separate code — verify against ROM
   `src/act_wiz.c:2553-2570` before deciding whether to keep the
   level computation or strip it).
3. `imm_search.py:417` → `from mud.spawning.obj_spawner import
   spawn_object`; line 424 → `clone = spawn_object(vnum)`. Same fix
   shape as Bug 2 (no `level` arg).
4. Add 3 regression tests (one per command): register a known
   prototype in `mob_registry`/`obj_registry`, assert the command
   returns `"Ok.\\n\\r"` / `"You clone $p."` (and surface the
   adjacent BCAST-002 row note about the unsubstituted `$p`/`$N`
   template literals — likely worth a separate FORMAT-001-style ID).
5. After WIZLOAD-001 lands, the standard `rom-gap-closer` pass on
   BCAST-002/014/015 closes the broadcast gaps on top (~1-2
   broadcasts each).

**Effort**: ~25 lines + 3 lookup-fix tests for WIZLOAD-001, then 3
standard BCAST gap-closers. Could be a single bundled commit if all
three commands are validated together, but the new bug-handling
discipline prefers one stable ID per root cause — bundling is fine
here because they're three instances of one mechanical typo pattern.

## Methodology limits & follow-up

The scan produced 29 ❌ and 10 ⚠️ rows out of 248 commands with a ROM counterpart (35 N/A excluded). The high ❌ rate vs the 2.9.x worked-precedent count (4 gaps across `do_say`/`do_buy`/`do_follow`/`do_group`) almost certainly contains false positives from helper hiding (door commands, combat skills, position-transition commands). The next session should:

1. Walk the ❌/⚠️ list in priority order from above.
2. For each, confirm the helper chain (`grep` callers of `broadcast_room` / `act_format` from the `do_*` body, including transitive helpers).
3. Promote confirmed gaps to single-commit `fix(parity)` via `rom-gap-closer` with stable IDs `BCAST-001` … `BCAST-NNN` as numbered in the table above.
4. Convert false-positive ❌ rows to ✅ with a 'covered via `<helper>` delegation' note so the next regex sweep doesn't re-flag them.
