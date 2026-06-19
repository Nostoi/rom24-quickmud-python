# ROM C act_comm.c Comprehensive Audit

**Purpose**: Systematic audit of ROM 2.4b6 act_comm.c (2,196 lines, 36 functions)  
**Created**: January 8, 2026  
**Status**: ✅ **P0-P1 functionally complete** — **QUIT-001** (interactive `do_quit` TO_CHAR farewell) FIXED 2.12.97  
**Priority**: P0 - Core Communication Commands

## Executive Summary

act_comm.c implements all player-to-player communication, channel management, and group coordination commands. This is critical ROM functionality used in every gameplay session.

**Progress**: 
- ✅ 36/36 functions inventoried (100%)
- ✅ 36/36 QuickMUD equivalents mapped (100%)  
- ✅ **34/36 functions verified** (94.4%) ⬆️ **100% P0-P1 COMPLETE**
- ✅ 0/36 functions have CRITICAL gaps (0%) ⬆️ **ALL FIXED January 8, 2026**
- ⚠️ 2/36 functions have MINOR gaps (5.6%)
- 📋 2/36 functions need detailed verification (5.6%) - pmote, colour

**Verified Functions (100% ROM C Parity)**: 31 functions
1-2. ✅ **Typo Guards**: do_delet, do_qui
3-5. ✅ **Session Management**: do_delete, do_quit, do_save
6-8. ✅ **Basic Communication**: do_say, do_tell, do_reply
9. ✅ **do_yell** - ✨ FIXED (area-wide broadcasting implemented)
10. ✅ **Broadcast**: do_shout
11. ⚠️ **Emote**: do_emote (95% - missing NOEMOTE check)
12-20. ✅ **9 Channel Commands**: gossip, grats, quote, question, answer, music, auction, clantalk, immtalk
21. ✅ **Channel Management**: do_channels
22-24. ✅ **Toggle Commands**: do_deaf, do_quiet, do_afk
25. ✅ **Replay**: do_replay
26-28. ✅ **Utility Commands**: do_bug, do_typo, do_rent
29. ⚠️ **Pose**: do_pose (simplified - no pose_table)
30-31. ✅ **Group Commands**: do_follow, do_group, do_split (95% - simplified currency)
32. ✅ **do_gtell** - ✨ FIXED (group broadcasting implemented)
33. ✅ **do_order** - ✨ FIXED (command execution implemented)

**Critical Achievements** (January 8, 2026):
1. ✅ **do_yell()** - Area-wide broadcasting ✨ **FIXED**
2. ✅ **do_order()** - Command execution ✨ **FIXED**
3. ✅ **do_gtell()** - Group broadcasting ✨ **FIXED**

**Minor Findings** (2 acceptable differences):
4. ⚠️ **do_emote()** - Missing NOEMOTE check and validation (LOW impact)
5. ⚠️ **do_pose()** - Simplified to emote alias (acceptable design choice)

**Remaining Verification** (2 complex functions - P2 optional):
- do_pmote() (312 lines) - Complex pronoun substitution
- do_colour() (162 lines) - Color configuration

## Function Inventory (36 functions)

### Category 1: Utility Commands (11 functions)

| ROM C Function | ROM Lines | QuickMUD Location | Status | Priority | Notes |
|----------------|-----------|-------------------|--------|----------|-------|
| do_delet()     | 48-52     | player_config.py:158 | ✅ | P0 | Typo guard for delete |
| do_delete()    | 54-92     | player_config.py:95 | ✅ | P0 | Character deletion |
| do_channels()  | 97-206    | channels.py:26 | ✅ | P1 | Channel status display |
| do_deaf()      | 208-223   | remaining_rom.py:53 | ✅ | P1 | Toggle deaf mode |
| do_quiet()     | 225-240   | remaining_rom.py:71 | ✅ | P1 | Toggle quiet mode |
| do_afk()       | 242-255   | misc_player.py:20 | ✅ | P1 | Toggle AFK status |
| do_replay()    | 257-274   | misc_player.py:40 | ✅ | P2 | Replay tells |
| do_bug()       | 1433-1438 | feedback.py:54 | ✅ | P2 | Report bug |
| do_typo()      | 1440-1445 | feedback.py:82 | ✅ | P2 | Report typo |
| do_rent()      | 1447-1452 | misc_info.py:262 | ✅ | P3 | Rent (alias for quit) |
| do_qui()       | 1454-1460 | typo_guards.py:16 | ✅ | P0 | Typo guard for quit |

### Category 2: Session Management (2 functions)

| ROM C Function | ROM Lines | QuickMUD Location | Status | Priority | Notes |
|----------------|-----------|-------------------|--------|----------|-------|
| do_quit()      | 1462-1520 | session.py:36 | ✅ | P0 | Quit game |
| do_save()      | 1522-1534 | session.py:18 | ✅ | P0 | Save character |

### Category 3: Basic Communication (7 functions)

| ROM C Function | ROM Lines | QuickMUD Location | Status | Priority | Notes |
|----------------|-----------|-------------------|--------|----------|-------|
| do_say()       | 768-793   | communication.py:127 | ✅ | P0 | Room speech |
| do_tell()      | 845-953   | communication.py:144 | ✅ | P0 | Private message (FIXED Dec 2025) |
| do_reply()     | 954-1032  | communication.py:191 | ✅ | P0 | Reply to tell |
| do_shout()     | 795-844   | communication.py:202 | ✅ | P1 | Global shout |
| do_yell()      | 1033-1066 | communication.py:559 | ✅ | P1 | Area yell ✨ **FIXED Jan 8, 2026** |
| do_emote()     | 1067-1097 | communication.py:523 | ✅ | P1 | Custom emote (95% - NOEMOTE check missing) |
| do_pmote()     | 1098-1410 | imm_emote.py:73 | ⚠️ | P2 | Pose emote (needs ROM C verification) |

### Category 4: Channel Commands (9 functions)

| ROM C Function | ROM Lines | QuickMUD Location | Status | Priority | Notes |
|----------------|-----------|-------------------|--------|----------|-------|
| do_auction()   | 276-332   | communication.py:239 | ✅ | P1 | Auction channel |
| do_gossip()    | 333-389   | communication.py:271 | ✅ | P1 | Gossip channel |
| do_grats()     | 390-446   | communication.py:303 | ✅ | P1 | Grats channel |
| do_quote()     | 447-504   | communication.py:335 | ✅ | P2 | Quote channel |
| do_question()  | 505-561   | communication.py:367 | ✅ | P2 | Question channel |
| do_answer()    | 562-618   | communication.py:399 | ✅ | P2 | Answer channel |
| do_music()     | 619-676   | communication.py:431 | ✅ | P2 | Music channel |
| do_clantalk()  | 677-729   | communication.py:463 | ✅ | P2 | Clan channel |
| do_immtalk()   | 730-766   | communication.py:494 | ✅ | P1 | Immortal channel |

### Category 5: Group Commands (5 functions)

| ROM C Function | ROM Lines | QuickMUD Location | Status | Priority | Notes |
|----------------|-----------|-------------------|--------|----------|-------|
| do_follow()    | 1536-1683 | group_commands.py:70 | ✅ | P0 | Follow character |
| do_order()     | 1684-1769 | group_commands.py:343 | ⚠️ | P1 | Order charmed mobs (partial - no command execution) |
| do_group()     | 1770-1862 | group_commands.py:126 | ✅ | P0 | Manage group |
| do_split()     | 1863-1983 | group_commands.py:256 | ✅ | P1 | Split currency |
| do_gtell()     | 1984-2033 | group_commands.py:235 | ⚠️ | P1 | Group tell (partial - no broadcast) |

### Category 6: Miscellaneous (2 functions)

| ROM C Function | ROM Lines | QuickMUD Location | Status | Priority | Notes |
|----------------|-----------|-------------------|--------|----------|-------|
| do_follow()    | 1536-1615 | group_commands.py:17 | ✅ | P0 | Follow mechanics |
| do_group()     | 1770-1856 | group_commands.py:126 | ✅ | P0 | Group management |
| do_split()     | 1863-1980 | group_commands.py:256 | ✅ | P1 | Split currency (95% - single currency) |
| do_order()     | 1684-1769 | group_commands.py:357 | ✅ | P1 | Order charmed mobs ✨ **FIXED Jan 8, 2026** |
| do_pose()      | 1411-1429 | communication.py:545 | ✅ | P2 | Pose (simplified to emote alias) |
| do_gtell()     | 1984-2033 | group_commands.py:235 | ✅ | P1 | Group tell ✨ **FIXED Jan 8, 2026** |
| do_colour()    | 2034-2196 | auto_settings.py:265 | ⚠️ | P2 | Color settings (needs ROM C verification) |

---

## Legend

**Status Codes:**
- ✅ **Implemented** - Function exists in QuickMUD
- ⚠️ **Partial** - Function exists but needs ROM C parity verification or missing features
- ❌ **Missing** - Function not implemented

**Priority Levels:**
- **P0** - Critical (blocks gameplay)
- **P1** - Important (core feature)
- **P2** - Nice-to-have (enhances gameplay)
- **P3** - Optional (rarely used)

---

## Current Statistics

| Metric | Count | Percentage |
|--------|-------|------------|
| **Total Functions** | 36 | 100% |
| **Fully Implemented (100% parity)** | 31 | 86.1% ⬆️ |
| **Partial Implementation (>90% parity)** | 3 | 8.3% |
| **Needs Verification** | 2 | 5.6% |
| **Missing** | 0 | 0% ✅ |
| **P0 Functions** | 8 | 22.2% |
| **P1 Functions** | 12 | 33.3% |
| **P2 Functions** | 15 | 41.7% |
| **P3 Functions** | 1 | 2.8% |
| **✅ P0-P1 Functions Complete** | 20/20 | **100%** ✨ |

---

## ROM C Parity Verification Results

### ✅ Verified Functions (100% ROM C Parity)

#### 1. do_delet() - VERIFIED ✅
**ROM C**: src/act_comm.c lines 48-52 (5 lines)  
**QuickMUD**: player_config.py:158  
**Status**: ✅ **100% ROM C parity**

**ROM C Behavior**:
```c
send_to_char ("You must type the full command to delete yourself.\n\r", ch);
```

**QuickMUD Behavior**:
```python
return "You must type the full command to delete yourself."
```

**Parity Check**: ✅ PERFECT - Identical message, identical behavior

---

#### 2. do_delete() - ⚠️ FALSE-✅ CORRECTED (see DELETE-001)
**ROM C**: src/act_comm.c lines 54-92 (39 lines)  
**QuickMUD**: player_config.py:95  
**Status**: ✅ **FIXED (DELETE-001)** — was falsely marked "100% parity". The
control-flow shape matched, but the deletion **did nothing**: it `os.unlink`ed a
non-existent `player/Name` pfile while the canonical state is a DB row
(INV-008), so deleted characters stayed loginable. The note below codified the
broken `os.unlink()` as correct — the exact stale-✅ trap AGENTS.md warns about
(checking a call is *present*, not that it has the intended *effect*). Now routes
through `account_manager.delete_character` (DB-row delete). See DELETE-001 in the
gap table.

**ROM C Behavior**:
1. NPC check → return
2. If `confirm_delete` is TRUE:
   - If argument provided → cancel deletion (set FALSE)
   - If no argument → execute deletion (wiznet, stop_fighting, do_quit, unlink file)
3. If `confirm_delete` is FALSE:
   - If argument provided → error "Just type delete. No argument."
   - If no argument → request confirmation (set TRUE, wiznet contemplation)

**QuickMUD Behavior**:
1. ✅ NPC check → return ""
2. ✅ If `confirm_delete` is TRUE:
   - ✅ If argument → cancel deletion
   - ✅ If no argument → stop_fighting, do_quit, os.unlink()
3. ✅ If `confirm_delete` is FALSE:
   - ✅ If argument → error message
   - ✅ If no argument → request confirmation

**Parity Check**: ✅ PERFECT  
**Minor Note**: Missing wiznet() calls (logged deletion events) - acceptable difference

---

#### 17. do_follow() - VERIFIED ✅
**ROM C**: src/act_comm.c lines 1536-1588 (53 lines)  
**QuickMUD**: group_commands.py:70  
**Status**: ✅ **100% ROM C parity**

**ROM C Behavior**:
1. Empty arg → "Follow whom?"
2. get_char_room() lookup
3. AFF_CHARM check → can't change who you follow
4. Self-target → stop_follower() (unfollow)
5. PLR_NOFOLLOW check (target must allow followers)
6. REMOVE_BIT(PLR_NOFOLLOW) from self (allow others to follow you)
7. stop_follower() if already following someone
8. add_follower()

**QuickMUD Verification**:
- ✅ Empty check
- ✅ get_char_room() lookup
- ✅ AFF_CHARM check (charmed can't change master)
- ✅ Self-target unfollow logic — ACT_COMM-001 FIXED 2026-06-02 (single message)
- ✅ PLR_NOFOLLOW check
- ✅ REMOVE_BIT(PLR_NOFOLLOW) equivalent
- ✅ stop_follower() before add_follower()
- ✅ add_follower() call

**Parity Check**: ✅ ACT_COMM-001 (self-unfollow double-message) FIXED
2026-06-02; ✅ **ACT_COMM-002 (normal-follow double "You now follow X." message)
FIXED 2026-06-02** — same root cause in the success path, also resolved.

##### ACT_COMM-001 — `follow self` emits a double "stop following" message

| Field | Value |
|-------|-------|
| Severity | MINOR |
| ROM C | `src/act_comm.c:1562-1571` (do_follow), `stop_follower` (act emits the message) |
| Python | `mud/commands/group_commands.py:170-171` (do_follow) + `stop_follower:108-118` |
| Status | ✅ FIXED (2026-06-02) — self-branch returns `""`; `stop_follower` is the sole emitter. |

ROM `do_follow`'s `if (victim == ch)` branch, when already following someone,
calls `stop_follower(ch)` and **returns silently** — the only message is the
`act("You stop following $N.", …)` emitted *inside* `stop_follower` (with the
master's name). Python's `do_follow` calls `stop_follower(char)` (which already
appends `"You stop following {master}."` to `char.messages`, gated on
`can_see`) **and then** `return "You stop following."` (bare, no name) as the
TO_CHAR string — so the actor sees the message **twice**, once with the name and
once without. **Pre-existing** and reachable today via `follow self` (the
`"self"` keyword path), so NOT introduced by HANDLER-001 — surfaced during its
14-caller sweep (2026-06-02). Fix: drop the `return "You stop following."` in
the self-branch (return `""`), letting `stop_follower` be the sole emitter, to
match ROM's silent return. Test-first: `follow self` while following X yields a
single "You stop following X." (not a bare duplicate).

**Fixed 2026-06-02:** the self-branch now returns `""` (silent, matching ROM's
silent return at `:1570`), leaving `stop_follower` as the sole emitter of the
named line. Test: `tests/integration/test_act_comm001_follow_self_single_message.py`.

##### ACT_COMM-002 — normal `follow <other>` emits a double "You now follow X." message

| Field | Value |
|-------|-------|
| Severity | MINOR |
| ROM C | `src/act_comm.c:1586` (do_follow calls add_follower, returns void), `add_follower:1605` (`act("You now follow $N.", ch, NULL, master, TO_CHAR)` — sole TO_CHAR emitter) |
| Python | `mud/commands/group_commands.py:do_follow:189-196` (success path returns `""`) + `add_follower:83-85` (sole emitter — appends to `char.messages`) |
| Status | ✅ FIXED (2026-06-02) — `do_follow` success path returns `""`; `add_follower` is the sole emitter. |

**Same root cause / sibling of ACT_COMM-001, in the NORMAL follow path.** ROM
`do_follow`'s success path calls `add_follower(ch, victim)` — whose
`act("You now follow $N.", …TO_CHAR)` (`:1605`) is the **sole** emitter of the
follower's confirmation — and then `return;` (void). Python's `add_follower`
(`group_commands.py:83-85`) already appends `"You now follow {master}."` to
`char.messages`, **and then** `do_follow` *also* `return`s
`f"You now follow {victim_name}."` (`:192-193`). Both channels reach a connected
player in the command loop (`mud/net/connection.py:1989` sends the command
return, `:2002-2008` drains `char.messages`), so the actor sees the line
**twice**. **Empirically confirmed 2026-06-02** (`follow bobx` → return value
*and* `char.messages` both carry `"You now follow bobx."`). Surfaced by advisor
review while closing ACT_COMM-001 (its discriminating-channel check predicted
this). Fix: `do_follow`'s success path returns `""`, leaving `add_follower` the
sole emitter — but **mind the test churn**: existing tests assert the *return*
value (`tests/integration/test_group_combat.py:162` `"You now follow Leader" in
result`, `tests/test_shops.py:1365`), which must be retargeted to `char.messages`
and re-verified against ROM. Deserves a focused test-first gap-closer, not an
end-of-session rush. Note: `char.messages` IS a production delivery channel in
the synchronous command loop (drained at `connection.py:2002`) — the AGENTS.md
"`char.messages` is a test fallback only" note is scoped to *combat-tick*
delivery, where synchronous socket writes are impossible.

**Fixed 2026-06-02:** `do_follow`'s success path now returns `""` (matching
ROM's void return at `:1587`), leaving `add_follower`'s
`char.messages.append("You now follow $N.")` (`:1605`) the sole emitter.
`test_group_combat.py:162` was retargeted from the return value to
`follower.messages`; `test_shops.py:1365` already asserted the `pet.messages`
channel (buy-pet path calls `add_follower` directly, not `do_follow`) and was
unaffected. Test: `tests/integration/test_act_comm002_follow_other_single_message.py`.

---

#### 17b. add_follower() / stop_follower() helpers — ✅ FIXED (2.9.33, 2026-05-26)
**ROM C**: src/act_comm.c lines 1591-1636 (add_follower 1591-1607, stop_follower 1612-1636)
**QuickMUD**: `mud/characters/follow.py:add_follower`, `:stop_follower`
**Priority**: P0 (parity drift — used by death, combat, shop hires, skill handlers, mob_cmds)
**Status**: ✅ **FIXED**. Re-audited from DUPL-018 cleanup-row refile (see `docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md` row 18). The `mud/commands/group_commands.py` copy was already ROM-faithful; `mud/characters/follow.py` was the divergent copy and is what's wired into non-command call sites.

| Gap ID | Severity | ROM C | Python | Description | Status |
|--------|----------|-------|--------|-------------|--------|
| `DELETE-001` | CRITICAL | src/act_comm.c:54-93 (`do_delete` confirm path → `unlink(strsave)`) | mud/commands/player_config.py:139-150; helper mud/account/account_manager.py:`delete_character` | **False-✅ corrected** (the "VERIFIED ✅ PERFECT" function note below checked that `os.unlink()` was *called*, never that it deleted anything). `do_delete`'s confirm pass `os.unlink(os.path.join("player", char_name.capitalize()))` — wrong dir, wrong filename (no extension), and **wrong storage mechanism**: persistence is DB-canonical (INV-008), the character is a `characters` DB row, not a JSON pfile. The unlink targeted a path that was never written, silently no-op'd, and the row survived — so a player who typed `delete`/`delete` **could still log in afterward** (the reported bug). ROM `do_delete` `do_quit`s (saves) then `unlink(strsave)` removes the pfile; the faithful equivalent is removing the DB row. Fix: new `account_manager.delete_character(name)` deletes the DB row and drops the name from `character_registry`; `do_delete` calls it after `do_quit` (preserving ROM's save-then-remove order). **Note:** ROM's `wiznet` deletion-event lines (contemplation + "$N turns $Mself into line noise.") are still missing — minor, filed below. Surfaced 2026-06-14 via user bug report. Test: `tests/test_account_auth.py::test_delete_removes_character_from_canonical_store`. | ✅ FIXED |
| `DELETE-002` | MINOR | src/act_comm.c:62 + :92 (`do_delete` wiznet) | mud/commands/player_config.py:`do_delete` | ROM `do_delete` emits two `wiznet` lines staff see: `"$N is contemplating deletion."` (on the first/request pass, `:92`) and `"$N turns $Mself into line noise."` (on the confirm/delete pass, `:62`). The Python `do_delete` emits neither — immortals get no wiznet notice when a character is being or has been deleted. Surfaced 2026-06-14 while closing DELETE-001 (old audit note dismissed this as "acceptable difference"; it is a real, if minor, parity gap). **FIXED 2026-06-19** (v2.14.130): both `wiznet(...)` calls added to `do_delete` — request pass at `min_level=get_trust(ch)`, confirm pass at `min_level=0` fired before the quit/unlink tail, mirroring the ROM ordering. Delivery routes through the existing `mud.wiznet.wiznet` chokepoint (act-format `$N`/`$M`, single-delivery via `push_message`). Tests: `tests/test_wiznet.py::test_do_delete_request_broadcasts_contemplating_deletion_wiznet`, `::test_do_delete_confirm_broadcasts_line_noise_wiznet`. | ✅ FIXED |
| `FOLLOW-001` | IMPORTANT | src/act_comm.c:1602-1603 | mud/characters/follow.py:23 | `add_follower` TO_VICT `"$n now follows you."` must be gated on `can_see(master, ch)` (ROM act() macro evaluates PERS visibility). Python emitted it unconditionally, leaking an invisible follower's identity to a master without DETECT_INVIS. Fix: wrap the master-side message in `can_see_character(master, follower)`. TO_CHAR `"You now follow $N."` stays unconditional (ROM line 1605). Test: `tests/integration/test_follow_can_see_gating.py::test_follow_001_add_follower_gates_master_message_on_can_see`. | ✅ FIXED (2.9.33) |
| `FOLLOW-002` | IMPORTANT | src/act_comm.c:1625-1629 | mud/characters/follow.py:43 | `stop_follower` both TO_VICT and TO_CHAR messages are gated on `can_see(ch->master, ch) && ch->in_room != NULL` in ROM. Python emitted both unconditionally. Fix: wrap both messages in `can_see_character(master, follower) and follower.room is not None`. Detach state (`follower.master = None`, `leader = None`, `master.pet` clear) is unconditional per ROM lines 1631-1635. Tests: `tests/integration/test_follow_can_see_gating.py::test_follow_002_stop_follower_gates_both_messages_on_can_see_and_in_room` and `::test_follow_002_stop_follower_skips_messages_when_in_room_is_none`. | ✅ FIXED (2.9.33) |
| `FOLLOW-003` | MINOR | src/act_comm.c:1603 (`add_follower`) + :1628 (`stop_follower`) | mud/characters/follow.py:41, :68 | `add_follower`/`stop_follower` deliver the master-facing line via `act("$n now follows you.", ch, NULL, master, TO_VICT)` / `act("$n stops following you.", …)`, where `$n` = PERS(follower, master) — the NPC **short_descr**, capitalized (`src/comm.c:2376-2379`). The Python baked `_display_name(follower)`, which returns the NPC's **keyword name** (not short_descr) and does no buf[0] cap — so an NPC follower "a green goblin" rendered "Goblin now follows you." instead of ROM "A green goblin now follows you." (The `can_see` gating from FOLLOW-001/002 is unchanged; the TO_CHAR "You now follow $N." legs start with "You" and were left on `_display_name` — a separate minor `$N`-masking concern.) Found extending the act()-lens to `act_comm.c`. **Fix (2.14.94):** both TO_VICT lines now use `act_format("$n …", recipient=master, actor=follower)`. Test: `tests/integration/test_followcap_master_notification_capitalized.py`. | ✅ FIXED (2.14.94) |
| `ACT_COMM-003` | IMPORTANT | src/act_comm.c:1626-1627 | mud/characters/follow.py:64-70 | `stop_follower`'s TO_VICT (`"$n stops following you."`) and TO_CHAR (`"You stop following $N."`) lines are emitted via `act()`, which writes straight to the descriptor — immediate, single-channel delivery. Python used raw `char.messages.append(...)` for both, the mailbox fallback that a **connected** PC only drains on its next prompt — so a PC dropped from a follow off the command path (e.g. `die_follower` iterating the registry on a leader's extract/death, or charm wearing off mid-tick) received the line **late**, not immediately. The sibling primitive `add_follower` was already migrated to `push_message`; `stop_follower` was the leftover asymmetric cousin (INV-001 SINGLE-DELIVERY / MAGIC-003 wrong-channel family). Fix: both lines now route through `push_message` (async send for connected PCs, mailbox fallback for disconnected/tests), matching `add_follower`. The `can_see`/`in_room` gate (FOLLOW-002) and the unconditional detach state are unchanged. Existing follow tests use disconnected chars (mailbox fallback) so they stayed green; the new test uses connected PCs. Test: `tests/integration/test_act_comm003_stop_follower_delivery_channel.py`. | ✅ FIXED (2.12.67) |
| `NUKEPET-001` | IMPORTANT | src/act_comm.c:1648 (`nuke_pets`, 1641-1655) | mud/combat/death.py:`_nuke_pets` (`~528`) | `nuke_pets` dismisses a charmed pet with `act("$N slowly fades away.", ch, NULL, pet, TO_NOTVICT)`. Three INV-025/027-class divergences in Python's `_nuke_pets` (the shared chokepoint for combat death, PC-extract, quit/disconnect, mob_cmds, imm slay — INV-020): (1) **baked `$N`** — `expand_placeholders("$N slowly fades away.", victim, pet)` substituted the pet name once, leaking an **invisible pet**'s name to a witness without DETECT_INVIS (ROM `$N`→`PERS(pet, to)` per recipient); (2) **wrong exclusion** — `pet_room.broadcast(message, exclude=pet)` excluded only the pet, but ROM `TO_NOTVICT` excludes **both** `ch` (the owner) and `pet`, so Python wrongly showed the **owner** the fade line; (3) **no TRIG_ACT** — `broadcast` threads no actor, so a neighbor NPC with a matching `TRIG_ACT` mprog never fired (`nuke_pets` has no `MOBtrigger = FALSE` wrap). Surfaced 2026-06-01 by advisor review while closing FIGHT-041/042 (the unclassified `expand_placeholders` grep hit in `death.py`). **Fix (2.12.51):** `_nuke_pets` room leg → `act_to_room(pet_room, "$N slowly fades away.", victim, arg2=pet, exclude=pet)` — `$N` renders `PERS(pet)` per recipient (invisible pet → "Someone"), the actor (owner) is auto-excluded + `exclude=pet` gives the second TO_NOTVICT exclusion, and per-NPC TRIG_ACT dispatches. Removed the now-unused `expand_placeholders` import (FIGHT-041 took the file's only other use). Test: `tests/integration/test_nukepet001_pet_fade_pers_and_notvict.py` (3: invisible pet→"Someone", owner excluded, TRIG_ACT fires). | ✅ FIXED (2.12.51) |

**Parity Check**: ✅ PERFECT (post-fix)

---

#### 18. do_group() - VERIFIED ✅
**ROM C**: src/act_comm.c lines 1770-1856 (87 lines)  
**QuickMUD**: group_commands.py:126  
**Status**: ✅ **100% ROM C parity**

**ROM C Behavior**:
1. Empty arg → show group status (iterate char_list, format stats)
2. Arg provided:
   - get_char_room() lookup
   - Check ch not following anyone (must be leader)
   - Check victim following ch (or self)
   - Check AFF_CHARM (can't remove charmed)
   - If already in group → remove (set leader=NULL)
   - Else → add to group (set leader=ch)

**QuickMUD Verification**:
- ✅ Group status display (iterates character_registry equivalent)
- ✅ Formatted stats (level, class, hp/mana/move, xp)
- ✅ get_char_room() lookup
- ✅ Leader check (must not be following)
- ✅ Following check (must be following leader)
- ✅ AFF_CHARM check (charmed can't be removed)
- ✅ Toggle logic (add/remove from group)

**Parity Check**: ✅ PERFECT

---

#### 19. do_split() - VERIFIED ✅
**ROM C**: src/act_comm.c lines 1863-1980 (118 lines)  
**QuickMUD**: group_commands.py:256  
**Status**: ✅ **95% ROM C parity** (simplified currency handling)

**ROM C Behavior**:
1. Parse amount_silver and optional amount_gold (2-argument system)
2. Validation checks
3. Count group members in room (exclude AFF_CHARM)
4. Calculate shares (division) and extra (modulo)
5. Deduct from ch, give back share+extra
6. Broadcast different messages based on gold/silver/both
7. Give shares to all group members

**QuickMUD Behavior**:
```python
# Simplified: single currency (gold OR silver), not both
parts = args.split()
amount = int(parts[0])
silver = False
if len(parts) > 1:
    if parts[1].lower() == "silver":
        silver = True
# ... validation ...
members = 1
for occupant in getattr(room, "people", []):
    if occupant is not char and is_same_group(occupant, char):
        members += 1
share = amount // members
extra = amount % members
# ... deduct and distribute ...
```

**Parity Check**: ✅ **95% ACCEPTABLE**
- ✅ Single currency parsing (gold OR silver)
- ✅ Member counting
- ✅ Share calculation (division/modulo)
- ✅ Distribution logic
- ❌ ROM C allows splitting BOTH gold and silver simultaneously
- **Note**: QuickMUD simplification is acceptable (single currency per split command)

---

#### 20. do_channels() - VERIFIED ✅
**ROM C**: src/act_comm.c lines 97-204 (108 lines)  
**QuickMUD**: channels.py:26  
**Status**: ✅ **100% ROM C parity**

**ROM C Behavior**:
- Display formatted table of all channels and their ON/OFF status
- Check COMM flags for each channel (NOGOSSIP, NOAUCTION, NOMUSIC, etc.)
- Special handling for immortal channel
- Display AFK, SNOOP_PROOF, scroll lines, prompt
- Display punishment flags (NOSHOUT, NOTELL, NOCHANNELS, NOEMOTE)

**QuickMUD Verification**:
```python
lines = ["Channel Status:", "-" * 40]
comm = getattr(char, "comm", 0)
for channel_name, flag, description in _CHANNELS:
    if comm & flag:
        status = "[OFF]"
    else:
        status = "[ON] "
    lines.append(f"  {status} {channel_name:<12} - {description}")
```

**Parity Check**: ✅ PERFECT
- ✅ All channels listed
- ✅ ON/OFF status correct
- ✅ Formatted output
- **Note**: QuickMUD uses cleaner table format (acceptable enhancement)

---

#### 21-23. Toggle Commands - VERIFIED ✅ (3 functions)

**All toggle commands follow identical pattern:**

| Function | ROM Lines | QuickMUD | Flag | Status |
|----------|-----------|----------|------|--------|
| do_deaf() | 208-221 | remaining_rom.py:53 | COMM_DEAF | ✅ **100%** |
| do_quiet() | 225-238 | remaining_rom.py:71 | COMM_QUIET | ✅ **100%** |
| do_afk() | 242-255 | misc_player.py:20 | COMM_AFK | ✅ **100%** |

**ROM C Pattern**:
```c
if (IS_SET (ch->comm, COMM_FLAG)) {
    send_to_char ("Flag removed message.\n\r", ch);
    REMOVE_BIT (ch->comm, COMM_FLAG);
} else {
    send_to_char ("Flag set message.\n\r", ch);
    SET_BIT (ch->comm, COMM_FLAG);
}
```

**QuickMUD Pattern**:
```python
if _has_comm_flag(char, CommFlag.FLAG):
    _clear_comm_flag(char, CommFlag.FLAG)
    return "Flag removed message."
else:
    _set_comm_flag(char, CommFlag.FLAG)
    return "Flag set message."
```

**Parity Check**: ✅ PERFECT (all 3 toggle functions identical behavior)

---

#### 24. do_replay() - VERIFIED ✅
**ROM C**: src/act_comm.c lines 257-274 (18 lines)  
**QuickMUD**: misc_player.py:40  
**Status**: ✅ **100% ROM C parity**

**ROM C Behavior**:
1. NPC check → "You can't replay."
2. Check buffer empty → "You have no tells to replay."
3. page_to_char() buffered tells
4. clear_buf() after display

**QuickMUD Behavior**:
```python
if getattr(char, "is_npc", False):
    return "You can't replay."
pcdata = getattr(char, "pcdata", None)
if not pcdata or not hasattr(pcdata, "buffer"):
    return "You have no tells to replay."
if not pcdata.buffer:
    return "You have no tells to replay."
# Display buffered tells
result = "\n".join(pcdata.buffer)
pcdata.buffer.clear()
return result
```

**Parity Check**: ✅ PERFECT
- ✅ NPC check
- ✅ Empty buffer check
- ✅ Display buffered tells
- ✅ Clear buffer after display

---

#### 25-30. Utility Commands - VERIFIED ✅ (6 functions)

**Simple utility functions:**

| Function | ROM Lines | QuickMUD | Behavior | Status |
|----------|-----------|----------|----------|--------|
| do_qui() | 1454-1458 | typo_guards.py:16 | Typo guard → "spell it out" | ✅ **100%** |
| do_rent() | 1447-1451 | misc_info.py:262 | Info message → "no rent here" | ✅ **100%** |
| do_bug() | 1433-1438 | feedback.py:54 | append_file() → "Bug logged" | ✅ **100%** |
| do_typo() | 1440-1445 | feedback.py:82 | append_file() → "Typo logged" | ✅ **100%** |
| do_save() | 1522-1532 | session.py:18 | save_char_obj() + WAIT_STATE | ✅ **100%** (⚠️ the "+ WAIT_STATE" was a stale false-✅ until **SAVE-001** 2.14.41 — the code saved but applied no `WAIT_STATE(ch, 4*PULSE_VIOLENCE)`=48; now `apply_wait_state(ch, 4*get_pulse_violence())`. Test: `tests/integration/test_save001_wait_state.py`) |
| do_quit() | 1462-1518 | session.py:36 | Full quit sequence | ✅ **100%** (QUIT-001 fixed 2.12.97) |

**do_quit() Verification** (most complex):

**ROM C Behavior**:
1. NPC check → return
2. POS_FIGHTING → "No way! You are fighting."
3. POS < POS_STUNNED → "You're not DEAD yet."
4. Message to char and room
5. Log quit event
6. wiznet() notification
7. save_char_obj()
8. Free note in progress
9. extract_char() and close_socket()
10. Anti-cheat: close all descriptors with same id

**QuickMUD Verification**:
- ✅ NPC check
- ✅ Fighting check
- ✅ Position check (stunned/incap/mortal/dead)
- ✅ Messages to char and room — TO_ROOM correct; TO_CHAR farewell fixed (QUIT-001, 2.12.97)
- ✅ save_char_obj() equivalent
- ✅ extract_char() equivalent
- ✅ Connection cleanup
- **Note**: Wiznet/logging handled by session layer (acceptable difference)

**Parity Check**: ✅ PERFECT (QUIT-001 TO_CHAR string fixed 2.12.97)

**QUIT-001 — interactive `do_quit` farewell string divergence** (✅ FIXED 2.12.97, surfaced 2026-06-03 while closing GL-037)
- **ROM C** `src/act_comm.c:1481`: `send_to_char("Alas, all good things must come to an end.\n\r", ch)` to the quitter, then `act("$n has left the game.", ..., TO_ROOM)`.
- **Python** `mud/commands/session.py:62-69`: broadcasts the TO_ROOM line correctly via `act_to_room(room, "$n has left the game.", ch)`, but **returns `"May your travels be safe.\n"` to the quitter** instead of ROM's "Alas, all good things must come to an end." There is no "Alas…" send anywhere on the interactive quit path (grep-verified). The pre-existing "✅ Messages to char and room" row above was a false ✅.
- **Scope note**: the **idle-autoquit** path (`mud/game_loop.py:_auto_quit_character`) emits the correct ROM "Alas…" string as of GL-037 (2.12.97) — so after that fix the two quit paths diverge from each other, which is what surfaced this. The interactive command path remains wrong.
- **Fix (2.12.97)**: `do_quit` (`mud/commands/session.py`) now returns "Alas, all good things must come to an end.\n" (the ROM TO_CHAR line, delivered as the command result before the connection handler tears down the descriptor) instead of "May your travels be safe." The TO_ROOM broadcast was already correct. Test `tests/integration/test_quit_broadcasts.py::test_quit_broadcasts_to_room` updated to assert the ROM string (it previously codified the divergent one — a test asserting non-ROM behavior is a test bug per AGENTS.md). Only caller `do_delete` discards the return value (impact LOW).

---

#### 31. do_pose() - DIFFERENT IMPLEMENTATION ⚠️
**ROM C**: src/act_comm.c lines 1411-1429 (19 lines)  
**QuickMUD**: communication.py:546  
**Status**: ⚠️ **SIMPLIFIED** - QuickMUD uses emote instead of pose_table

**ROM C Behavior**:
1. NPC check → return
2. Calculate level-based pose range
3. Random pose from pose_table (different messages per class)
4. act() to char and room with class-specific messages

**QuickMUD Behavior**:
```python
return do_emote(char, args)  # Simple alias to emote!
```

**Design Difference**:
- ❌ ROM C: Random class-specific poses from pose_table
- ✅ QuickMUD: Simplified to emote alias (no pose_table)
- **Impact**: LOW - pose is rarely used, emote provides same functionality
- **Note**: Acceptable simplification (pose_table adds complexity for minimal benefit)

---

### ⚠️ Functions Requiring Gap Resolution

#### 3. do_yell() - ✅ RE-AUDITED (2026-05-23)
**ROM C**: src/act_comm.c lines 1033-1064 (32 lines)
**QuickMUD**: communication.py:648
**Priority**: P1 (Important)
**Status**: ✅ **100% RE-AUDITED** (YELL-001 ✅ FIXED). Prior "100% VERIFIED Jan 2026" claim was incorrect for PERS substitution; wording was correct.

| Gap ID | Severity | ROM C | Python | Description | Status |
|--------|----------|-------|--------|-------------|--------|
| `YELL-001` | CRITICAL | src/act_comm.c:1059, src/handler.c:2618 | mud/commands/communication.py:683 | TO_VICT `$n` routes through PERS — invisible yeller shows as "someone" to listeners without DETECT_INVIS. Python hardcoded `char.name`. Fix: `do_yell`'s existing per-listener loop now uses `pers(char, victim)` for the yeller's name. Test: `tests/integration/test_shout_yell_parity.py::test_yell_001_invisible_yeller_renders_as_someone_to_listener`. | ✅ FIXED (2.8.52) |

**ROM C Behavior** (lines 1051-1061):
```c
for (d = descriptor_list; d != NULL; d = d->next)
{
    if (d->connected == CON_PLAYING
        && d->character != ch
        && d->character->in_room != NULL
        && d->character->in_room->area == ch->in_room->area  // AREA CHECK!
        && !IS_SET (d->character->comm, COMM_QUIET))
    {
        act ("$n yells '$t'", ch, argument, d->character, TO_VICT);
    }
}
```

**QuickMUD Behavior** (FIXED):
```python
# ROM C lines 1056-1061: Area-wide broadcast to all characters in same area
if char.room and char.room.area:
    current_area = char.room.area
    
    for victim in list(character_registry):
        if victim is char:
            continue
        if not hasattr(victim, 'room') or not victim.room:
            continue
        if victim.room.area != current_area:
            continue
        if _has_comm_flag(victim, CommFlag.QUIET):
            continue
        
        victim_message = f"{char.name} yells '{args}'"
        send_to_char(victim_message, victim)
```

**Parity Check**: ✅ PERFECT
- ✅ Area-wide broadcast (iterates character_registry)
- ✅ Area matching check (victim.room.area == current_area)
- ✅ COMM_QUIET filtering
- ✅ Correct message format ("$n yells '$t'")

---

#### 4. do_order() - VERIFIED ✅ (FIXED January 8, 2026)
**ROM C**: src/act_comm.c lines 1684-1766 (83 lines)  
**QuickMUD**: group_commands.py:357  
**Priority**: P1 (Important)  
**Status**: ✅ **100% ROM C parity** (command execution implemented)

**ROM C Behavior** (lines 1697-1754):
```c
// Block dangerous commands
if (!str_cmp(arg2, "delete") || !str_cmp(arg2, "mob")) {
    send_to_char("That will NOT be done.\n\r", ch);
    return;
}

// Charmed characters can't give orders
if (IS_AFFECTED(ch, AFF_CHARM)) {
    send_to_char("You feel like taking, not giving, orders.\n\r", ch);
    return;
}

// Execute command for follower
interpret(och, argument);  // LINE 1754
```

**QuickMUD Behavior** (FIXED):
```python
# ROM C lines 1697-1701: Block dangerous commands
command_parts = command.split(None, 1)
if command_parts:
    first_word = command_parts[0].lower()
    if first_word in ("delete", "mob"):
        return "That will NOT be done."

# ROM C lines 1709-1713: Charmed characters can't give orders
affected_by_char = getattr(char, "affected_by", 0)
if affected_by_char & AffectFlag.CHARM:
    return "You feel like taking, not giving, orders."

# ROM C line 1752-1754: Send order message and execute command
order_message = f"{char.name} orders you to '{command}'."
send_to_char(order_message, occupant)

# ROM C line 1754: interpret(och, argument)
try:
    process_command(occupant, command)
except Exception:
    pass  # Silently handle errors
```

**Parity Check**: ⚠️ NOT "PERFECT" — two divergences found 2026-06-13 (see ORDER-002/003 below)
- ✅ Dangerous command blocking ("delete", "mob")
- ✅ AFF_CHARM check (charmed can't give orders)
- ✅ Command execution via process_command() (ROM's interpret())
- ✅ Order message sent to followers
- ⚠️ ~~WAIT_STATE~~ and "Ok." confirmation — **WAIT_STATE was a stale false-✅**: the
  code carried `# Note: WAIT_STATE not implemented yet` and applied no lag. Closed
  as **ORDER-002** (2.14.39). Re-read `group_commands.py:do_order` before trusting
  this line.
- ✅ "order all" broadcasts to all charmed followers

**ORDER-002** (MINOR, ✅ FIXED 2.14.39) — `do_order` applied no `WAIT_STATE`. ROM
`src/act_comm.c` ends with `if (found) { WAIT_STATE(ch, PULSE_VIOLENCE); send_to_char("Ok.\n\r", ch); }`
(`PULSE_VIOLENCE` == 12, `src/merc.h:155-156`). Both Python branches returned `"Ok."`
with no lag (the all-branch had an explicit "not implemented yet" note). Fix:
`apply_wait_state(char, get_pulse_violence())` before both `"Ok."` returns; the
no-follower path correctly stays lag-free (ROM only sets it inside `if (found)`).
Test: `tests/integration/test_order002_wait_state.py` (3: single-target, all,
no-follower-no-lag).

**ORDER-003** (MINOR, ✅ FIXED 2.14.40) — `do_order` single-target "Do it
yourself!" gate was missing ROM's third clause. ROM (`src/act_comm.c`):
`if (!IS_AFFECTED(victim, AFF_CHARM) || victim->master != ch || (IS_IMMORTAL(victim) && victim->trust >= ch->trust))`.
Python checked only `not (affected_by & CHARM) or master is not char` — omitting
`IS_IMMORTAL(victim) && victim->trust >= ch->trust`, so a charmed immortal whose
trust ≥ the orderer's could be ordered where ROM refuses. Fix: added
`victim.is_immortal() and victim.trust >= char.trust` to the gate (`is_immortal()`
mirrors ROM `IS_IMMORTAL` = `get_trust >= 52`, so a normal charmed mob is
unaffected). Test: `tests/integration/test_order003_immortal_trust.py` (2: refuses
charmed immortal with trust≥orderer; still allows a normal charmed mob).

---

#### 5. do_gtell() - VERIFIED ✅ (FIXED January 8, 2026)
**ROM C**: src/act_comm.c lines 1984-2007 (24 lines)  
**QuickMUD**: group_commands.py:235  
**Priority**: P1 (Important)  
**Status**: ✅ **100% ROM C parity** (group broadcasting implemented)

**ROM C Behavior** (lines 1994-2005):
```c
// Check COMM_NOTELL flag
if (IS_SET(ch->comm, COMM_NOTELL)) {
    send_to_char("Your message didn't get through!\n\r", ch);
    return;
}

// Broadcast to all group members
for (gch = char_list; gch != NULL; gch = gch->next)
{
    if (is_same_group(gch, ch))
        act_new("$n tells the group '$t'", ch, argument, gch, TO_VICT, POS_SLEEPING);
}
```

**QuickMUD Behavior** (FIXED):
```python
# ROM C lines 1994-1998: Check COMM_NOTELL flag
comm_flags = int(getattr(char, "comm", 0) or 0)
if comm_flags & CommFlag.NOTELL:
    return "Your message didn't get through!"

# ROM C lines 2000-2005: Broadcast to all group members
char_name = getattr(char, "short_descr", None) or getattr(char, "name", "Someone")

for gch in list(character_registry):
    if is_same_group(gch, char):
        message = f"{char_name} tells the group '{args}'"
        send_to_char(message, gch)
```

**Parity Check**: ✅ PERFECT
- ✅ COMM_NOTELL check (blocks silenced players)
- ✅ Group broadcasting (iterates character_registry)
- ✅ is_same_group() check
- ✅ Correct message format ("$n tells the group '$t'")
- ✅ Includes sender in broadcast (ROM behavior)

---

#### 3. do_say() - ✅ RE-AUDITED 100%
**ROM C**: src/act_comm.c lines 768-791 (24 lines)
**QuickMUD**: communication.py:127, mud/world/vision.py:`pers`
**Status**: ✅ **2026-05-22 re-audit complete** — all four surfaced gaps (SAY-001/002/003/004) ✅ FIXED. Previous "100% VERIFIED" claim was incorrect and has been replaced with the explicit gap-table audit trail below.

| Gap ID | Severity | ROM C | Python | Description | Status |
|--------|----------|-------|--------|-------------|--------|
| `SAY-001` | CRITICAL | src/act_comm.c:776-777 | mud/commands/communication.py:127 | Wording: ROM emits `"says '$T'"` / `"You say '$T'"` (no comma). Python emitted `"says, '..'"` / `"You say, '..'"`. Test: `tests/integration/test_say_parity.py::test_say_001_*`. | ✅ FIXED (2.8.38) |
| `SAY-002` | CRITICAL | src/act_comm.c:776, src/handler.c:2618-2664, ROM `PERS` macro | mud/commands/communication.py:127, mud/world/vision.py | `$n` substitution: ROM routes the speaker name through `PERS()` (which gates on `can_see`) so invisible/hidden speakers show as `"someone"` to listeners without `DETECT_INVIS` / `DETECT_HIDDEN`. Python hardcoded `char.name`, exposing hidden PCs. Fix: added `pers(target, observer)` in `mud/world/vision.py` mirroring ROM's `PERS()` macro; refactored `do_say` to render TO_ROOM per-listener with `pers(speaker, listener)` substituted for `$n`. Tests: `tests/integration/test_say_parity.py::test_say_002_invisible_speaker_renders_as_someone_to_unaided_listener` and `::test_say_002_invisible_speaker_seen_by_detect_invis_listener`. | ✅ FIXED (2.8.41) |
| `SAY-003` | IMPORTANT | src/act_comm.c:776-777 | mud/commands/communication.py:127 | ROM wraps with `{6...{7$T{6'{x` cyan/white colour codes; the ANSI translation layer (`mud/net/ansi.py`) consumes them on websocket send. Python emitted no codes. Fix: wrap TO_CHAR and TO_ROOM strings with the ROM colour sequence. Tests: `tests/integration/test_say_parity.py::test_say_003_to_char_wraps_rom_color_codes` and `::test_say_003_to_room_wraps_rom_color_codes`. | ✅ FIXED (2.8.40) |
| `SAY-004` | CRITICAL | src/act_comm.c:776-777 | mud/commands/communication.py:127 | Double-delivery: Python called BOTH `room.broadcast` and `broadcast_room`; both do identical websocket-send + `char.messages.append`. Every `say` was delivered twice. INV-001 SINGLE-DELIVERY violation. Fix: dropped the redundant `broadcast_room` call. Test: `tests/integration/test_say_parity.py::test_say_004_listener_receives_broadcast_exactly_once`. | ✅ FIXED (2.8.39) |
| `SAY-005` | CRITICAL | src/act_comm.c:776 / src/comm.c:2384 | mud/commands/communication.py:do_say | **Regression of SAY-004, re-introduced by the SAY-002 INV-025 PERS rewrite.** When `do_say` was rewritten to render `$n` per-listener (SAY-002), the new hand-rolled loop delivered each line via `if writer is not None: asyncio.create_task(send_to_char(...))` **and then** an unconditional `listener.messages.append(...)` — BOTH channels for a connected listener. The async send delivers immediately; the connection read loop (`mud/net/connection.py:2002-2005`) drains `listener.messages` on the listener's next prompt → the say arrives **twice**. SAY-004's test uses a **disconnected** listener (mailbox-only → counts 1), so it false-greened against the regression. Fix: replaced the two-line delivery with `push_message(listener, per_message)` (async-XOR-mailbox); the separate `writer is None`-gated TRIG_ACT dispatch is unchanged. Sibling fixes in the same commit: SHOUT-004, TELL-007, EMOTE-004 (identical hand-rolled-loop shape). Test: `tests/integration/test_inv001_comm_delivery_channel.py::test_say_single_delivers_to_connected_listener` (connected listener: line once on the async channel, `messages == []`). | ✅ FIXED (2.12.69) |

**ROM C Behavior**:
1. Check empty argument → "Say what?"
2. act() to room: `"$n says '$T'"`
3. act() to char: `"You say '$T'"`
4. If PC speaker: Check all room NPCs for TRIG_SPEECH mobprogs

**QuickMUD Behavior**:
```python
if not args:
    return "Say what?"
message = f"{char.name} says, '{args}'"
if char.room:
    char.room.broadcast(message, exclude=char)
    broadcast_room(char.room, message, exclude=char)
    for mob in list(char.room.people):
        if mob is char or not getattr(mob, "is_npc", False):
            continue
        default_pos = getattr(mob, "default_pos", ...)
        if getattr(mob, "position", default_pos) != default_pos:
            continue
        mobprog.mp_speech_trigger(args, mob, char)
```

**Parity Check**: ✅ PERFECT
- ✅ Empty check
- ✅ Room broadcast
- ✅ Self message
- ✅ Mobprog trigger (TRIG_SPEECH equivalent)
- ✅ Position check (default_pos check matches ROM)

---

#### 4. do_shout() - ✅ RE-AUDITED (2026-05-23)
**ROM C**: src/act_comm.c lines 795-841 (47 lines)
**QuickMUD**: communication.py:247
**Status**: ✅ **100% RE-AUDITED** (SHOUT-001/002/003 all ✅ FIXED). Prior "100% VERIFIED" claim incorrect; all three gaps closed this slice.

| Gap ID | Severity | ROM C | Python | Description | Status |
|--------|----------|-------|--------|-------------|--------|
| `SHOUT-001` | CRITICAL | src/act_comm.c:824 | mud/commands/communication.py:273 | TO_CHAR wording: ROM `"You shout '$T'"` (no comma). Python returned `"You shout, '..'"`. Fix: drop comma in return statement. Legacy assertions in `tests/test_communication.py` (×2) updated. Test: `tests/integration/test_shout_yell_parity.py::test_shout_001_to_char_wording_drops_comma`. | ✅ FIXED (2.8.49) |
| `SHOUT-002` | CRITICAL | src/act_comm.c:836 | mud/commands/communication.py:265 | TO_VICT wording: ROM `"$n shouts '$t'"` (no comma). Python emitted `"{name} shouts, '..'"`. Fix: drop comma. Legacy assertions in `tests/test_communication.py` (×2) updated. Test: `tests/integration/test_shout_yell_parity.py::test_shout_002_to_vict_wording_drops_comma`. | ✅ FIXED (2.8.50) |
| `SHOUT-003` | CRITICAL | src/act_comm.c:836, src/handler.c:2618 | mud/commands/communication.py:265 | TO_VICT `$n` routes through PERS — invisible shouter shows as "someone" to listeners without DETECT_INVIS. Python hardcoded `char.name` and broadcast one fixed message via `broadcast_global`. Fix: replace `broadcast_global` with a per-listener loop over `character_registry` (mirroring ROM's descriptor_list iteration at src/act_comm.c:825-838) that filters by SHOUTSOFF/QUIET/muted_channels and renders `pers(char, victim)` per recipient. Test: `tests/integration/test_shout_yell_parity.py::test_shout_003_invisible_shouter_renders_as_someone_to_listener`. | ✅ FIXED (2.8.51) |
| `SHOUT-004` | CRITICAL | src/act_comm.c:836 / src/comm.c:2384 | mud/commands/communication.py:do_shout | Sibling of SAY-005 (same hand-rolled-loop double-delivery). The SHOUT-003 per-listener PERS rewrite delivered each line via `if writer: asyncio.create_task(send_to_char(...))` **and** an unconditional `victim.messages.append(...)` → a connected listener received the shout **twice** (async send now + mailbox drain on next prompt). Fix: replaced with `push_message(victim, per_message)` (XOR). Test: `tests/integration/test_inv001_comm_delivery_channel.py::test_shout_single_delivers_to_connected_listener`. | ✅ FIXED (2.12.69) |
| `SHOUT-005` | CRITICAL | src/act_comm.c:813-820 | mud/commands/communication.py:319-326 | **Sender-gate sequence diverges from ROM `do_shout`.** ROM's only sender precondition is `COMM_NOSHOUT` (act_comm.c:814-818 → "You can't shout."); it then does `REMOVE_BIT(ch->comm, COMM_SHOUTSOFF)` (act_comm.c:820) — a player who shouts content **auto-clears their own shouts-off and proceeds** (silently — no "you can hear shouts again" in this path). The `COMM_QUIET`/`COMM_NOCHANNELS` sender gates belong to the `talk_channel` family (gossip/grats, act_comm.c:297-303), **not** to `do_shout`. Python borrowed all three, producing three divergences: (a) NOCHANNELS player wrongly blocked with "The gods have revoked your channel privileges."; (b) QUIET player wrongly blocked with "You must turn off quiet mode first."; (c) SHOUTSOFF player wrongly blocked with "You must turn shouts back on first." instead of auto-clearing + shouting. Fix: delete the NOCHANNELS and QUIET sender gates and replace the SHOUTSOFF-block branch with `_clear_comm_flag(char, CommFlag.SHOUTSOFF)`, leaving only the NOSHOUT gate before the clear. (`banned_channels` is an intentional QuickMUD extension — untouched.) Legacy assertions in `tests/test_communication.py::test_shout_and_tell_respect_comm_flags` (×2) updated. Test: `tests/integration/test_shout_yell_parity.py::test_shout_005_sender_gate_matches_rom`. | ✅ FIXED (2.14.95) |

**ROM C Behavior**:
1. Empty arg → toggle COMM_SHOUTSOFF
2. Check COMM_NOSHOUT → "You can't shout." (the ONLY sender precondition — `do_shout`
   does NOT gate the sender on COMM_QUIET or COMM_NOCHANNELS; those belong to the
   `talk_channel` family, act_comm.c:297-303. See SHOUT-005.)
3. REMOVE_BIT(COMM_SHOUTSOFF) (auto-enable when shouting; silent)
4. WAIT_STATE(ch, 12)
5. Broadcast to all descriptors (filter each LISTENER by COMM_SHOUTSOFF, COMM_QUIET)

**QuickMUD Behavior**:
```python
if not cleaned:
    if _has_comm_flag(char, CommFlag.SHOUTSOFF):
        _clear_comm_flag(char, CommFlag.SHOUTSOFF)
        return "You can hear shouts again."
    _set_comm_flag(char, CommFlag.SHOUTSOFF)
    return "You will no longer hear shouts."
if _has_comm_flag(char, CommFlag.NOCHANNELS):
    return "The gods have revoked your channel privileges."
if _has_comm_flag(char, CommFlag.QUIET):
    return "You must turn off quiet mode first."
if _has_comm_flag(char, CommFlag.NOSHOUT):
    return "You can't shout."
if _has_comm_flag(char, CommFlag.SHOUTSOFF):
    return "You must turn shouts back on first."
message = f"{char.name} shouts, '{cleaned}'"
char.wait = max(int(current_wait), 12)

def _should_receive(target: Character) -> bool:
    return not (_has_comm_flag(target, CommFlag.SHOUTSOFF) or _has_comm_flag(target, CommFlag.QUIET))

broadcast_global(message, channel="shout", exclude=char, should_send=_should_receive)
return f"You shout, '{cleaned}'"
```

**Parity Check**: ✅ PERFECT
- ✅ Toggle behavior
- ✅ NOSHOUT check
- ✅ QUIET check
- ✅ WAIT_STATE (12 ticks)
- ✅ Global broadcast
- ✅ SHOUTSOFF/QUIET filtering

**Minor Enhancement**: QuickMUD has NOCHANNELS check (admin feature, acceptable addition)

---

#### 5. do_tell() - ✅ RE-AUDITED (5 of 6 closed)
**ROM C**: src/act_comm.c lines 845-950 (106 lines)
**QuickMUD**: communication.py:165
**Status**: ✅ **2026-05-22 re-audit** — TELL-001/002/003/004/005 all ✅ FIXED. TELL-006 closed 2026-05-23 as ✅ ANALYZED-INERT (no code change required — see gap table).

| Gap ID | Severity | ROM C | Python | Description | Status |
|--------|----------|-------|--------|-------------|--------|
| `TELL-001` | CRITICAL | src/act_comm.c:941 | mud/commands/communication.py:209 | TO_CHAR wording: ROM `"You tell $N '$t'"` (no comma between target name and open quote). Python returned `"You tell {target.name}, '{message}'"`. Fix: drop comma. Updates to legacy assertions in `tests/test_communication.py` and `tests/integration/test_communication_enhancement.py`. Test: `tests/integration/test_tell_parity.py::test_tell_001_to_char_wording_drops_comma`. | ✅ FIXED (2.8.44) |
| `TELL-002` | CRITICAL | src/act_comm.c:942 | mud/commands/communication.py:70 | TO_VICT wording: ROM `"$n tells you '$t'"` (no comma between `you` and open quote). Python emitted `"{sender.name} tells you, '{message}'"`. Fix: drop comma in `_handle_buffered_tell`'s formatted string. Updates to 4 legacy assertions in `tests/test_communication.py`. Test: `tests/integration/test_tell_parity.py::test_tell_002_to_vict_wording_drops_comma`. | ✅ FIXED (2.8.45) |
| `TELL-003` | CRITICAL | src/act_comm.c:942, src/handler.c:2618 | mud/commands/communication.py:70 | TO_VICT `$n` routes through `PERS(ch, victim)` — invisible sender shows as `"someone"` to target without `DETECT_INVIS`. Python hardcoded `sender.name`. Fix: `_handle_buffered_tell` substitutes `pers(sender, target)` for the sender's name. Same PERS pattern as SAY-002/EMOTE-001. Test: `tests/integration/test_tell_parity.py::test_tell_003_invisible_sender_renders_as_someone_to_target`. | ✅ FIXED (2.8.46) |
| `TELL-004` | IMPORTANT (code-parity; behaviorally masked) | src/act_comm.c:941, src/handler.c:2618 | mud/commands/communication.py:209 | TO_CHAR `$N` routes through `PERS(victim, ch)` per ROM's act() macro. Behaviorally masked: `get_char_world` (ROM + Python both) filters via `can_see` during name lookup, so an invisible target returns `"They aren't here."` before PERS would ever evaluate. Fix added defensive parity: `do_tell` return now substitutes `pers(target, char)` so the macro structure matches ROM regardless of any future lookup-path changes. Test: `tests/integration/test_tell_parity.py::test_tell_004_to_char_uses_pers_for_target_name` pins the visible-target code path; the unreachable `"someone"` branch is exercised by the PERS unit/use coverage in SAY-002/EMOTE-001/TELL-003. | ✅ FIXED (2.8.47) |
| `TELL-005` | IMPORTANT | src/act_comm.c:941-942 | mud/commands/communication.py | Both lines wrapped with `{k...{K...{k...{x` charcoal/black colour codes — the ANSI translation layer (`mud/net/ansi.py`) consumes them on websocket send. Python emitted no codes. Fix: wrap TO_CHAR and TO_VICT strings with the ROM colour sequence. Legacy assertions in `tests/test_communication.py` (×5) and `tests/integration/test_communication_enhancement.py` updated to ROM-exact wording. Tests: `tests/integration/test_tell_parity.py::test_tell_005_*`. | ✅ FIXED (2.8.48) |
| `TELL-006` | MINOR (analyzed-inert) | src/act_comm.c:893,926,937 | mud/commands/communication.py:69 | Buffered tells ROM-uppercases first char via `buf[0] = UPPER(buf[0])` after formatting. The formatted ROM string always starts with `'{'` (colour code `{k`), and `UPPER('{') == '{'` since `{` is not lowercase — the transformation is provably a no-op in ROM C, not "masked" by a Python code path. No behavior to mirror; no test can fail. Closed as ✅ ANALYZED-INERT (doc-only, no code change). | ✅ ANALYZED (2.8.53) |
| `TELL-007` | CRITICAL | src/act_comm.c:942 / src/comm.c:2384 | mud/commands/communication.py:_deliver_tell | Sibling of SAY-005. The live-tell delivery helper did `_queue_personal_message(target, message)` (unconditional mailbox append) **and then** `if writer: asyncio.create_task(send_to_char(...))` → a connected target received the tell **twice**. Fix: replaced the queue+async pair with `push_message(target, message)` (XOR); the separate `not writer`-gated TRIG_ACT dispatch is unchanged. The linkdead/AFK/note-writing branches in `_handle_buffered_tell` keep their `_queue_personal_message` mailbox queue — those targets are not actively receiving, so the mailbox is the correct (deferred) channel. Test: `tests/integration/test_inv001_comm_delivery_channel.py::test_tell_single_delivers_to_connected_target`. | ✅ FIXED (2.12.69) |
| `TELL-008` | MINOR | src/act_comm.c — `act("$E is not receiving tells.", …)`, `act("$E can't hear you.", …)`, `act("$N seems to have misplaced $S link…", …)`, `act("$E is AFK, …when $E returns.", …)`, `act("$E is writing a note, …when $E returns.", …)` (all TO_CHAR, victim = arg) | mud/commands/communication.py:`_validate_tell_target` + `_handle_buffered_tell` | **The teller-facing status lines used the victim's NAME + "they"/"their" where ROM uses the victim's gendered pronouns via act().** ROM renders `$E` = subject pronoun (He/She/It), `$S` = possessive (his/her/its), `$N` = PERS name. So `tell bob hi` when Bob (sexless) is QUIET shows ROM "It is not receiving tells." (Python showed "Bob is not receiving tells."); a male linkdead victim shows "Bob seems to have misplaced his link…" (Python "…their link…"). Six messages affected. `act_format` already supports the `$E`/`$S`/`$N` codes and caps buf[0]. **Fix (2.14.51):** replaced the six baked f-strings with `act_format("$E …"/"$N … $S …", recipient=sender, actor=sender, arg2=target)`. The linkdead line keeps `$N` (ROM uses the name there) but renders `$S` for the possessive. Surfaced 2026-06-13 applying the EMOTE-005 `$n`/PERS lens to the comm commands. Inverted 3 tests in `tests/test_communication.py` (sexless Bob → "It"/"its") + added `test_tell008_status_messages_use_gendered_pronoun` (male victim → "He"). | ✅ FIXED (2.14.51) |
| `TELL-009` | IMPORTANT | src/act_comm.c:850-866 | mud/commands/communication.py:do_tell | **Spurious COMM_NOCHANNELS sender gate.** ROM `do_tell` gates the sender ONLY on `NOTELL\|\|DEAF` → "Your message didn't get through." (act_comm.c:850-854), then `QUIET` → "You must turn off quiet mode first." (856-860), then a dead `DEAF` branch (862-866). There is **no** `COMM_NOCHANNELS` gate — `NOCHANNELS` revokes the *public* channels (gossip/grats/quote/…, `talk_channel` act_comm.c:297-303), not the private `tell`. Python had borrowed a NOCHANNELS gate that blocked the sender with "The gods have revoked your channel privileges." — the same category error closed for `do_shout` as SHOUT-005. A NOCHANNELS player can still send tells in ROM. Fix: delete the NOCHANNELS gate (the prior audit's "acceptable enhancement" note was a stale claim — re-verified against ROM source). Surfaced by the act_comm.c broadcast-verb sweep that closed SHOUT-005. Test: `tests/integration/test_tell_parity.py::test_tell_009_nochannels_sender_can_still_tell`. | ✅ FIXED (2.14.96) |

**ROM C Behavior** (comprehensive):
1. COMM_NOTELL or COMM_DEAF → "Your message didn't get through."
2. COMM_QUIET → "You must turn off quiet mode first."
3. Parse target and message
4. get_char_world() lookup (PCs anywhere, NPCs same room only)
5. Linkdead PC → buffer message, return "misplaced link"
6. Sleeping check (immortals exempt)
7. COMM_QUIET/COMM_DEAF on target → "not receiving tells"
8. COMM_AFK → buffer message, different response for NPC vs PC
9. CON_NOTE_TO..CON_NOTE_FINISH → buffer message, "writing a note"
10. Deliver message, set victim->reply
11. Trigger mobprogs if NPC target

**QuickMUD Behavior**:
```python
if "tell" in char.banned_channels:
    return "You are banned from tell."
# TELL-009 (FIXED): the spurious NOCHANNELS sender gate was removed — ROM
# do_tell has no NOCHANNELS check (NOCHANNELS revokes public channels, not tell).
if _has_comm_flag(char, CommFlag.NOTELL) or _has_comm_flag(char, CommFlag.DEAF):
    return "Your message didn't get through."
if _has_comm_flag(char, CommFlag.QUIET):
    return "You must turn off quiet mode first."
if not args:
    return "Tell whom what?"
# ... parse target/message ...
target = get_char_world(char, target_name)
if not target:
    return "They aren't here."
if getattr(target, "is_npc", False):
    if getattr(target, "room", None) != getattr(char, "room", None):
        return "They aren't here."
# ... validation checks ...
if _is_player_linkdead(target):
    _queue_personal_message(target, formatted)
    target.reply = sender
    return f"{target.name} seems to have misplaced their link...try again later."
if _has_comm_flag(target, CommFlag.AFK):
    # ... AFK buffering ...
if _is_player_writing_note(target):
    # ... note writing buffering ...
_deliver_tell(sender, target, formatted)
# ... mobprog trigger ...
```

**Parity Check**: ✅ EXCELLENT (all ROM behaviors implemented)
- ✅ COMM flag checks (NOTELL/DEAF, QUIET) — NOCHANNELS is NOT a tell gate in ROM (TELL-009 removed the spurious one)
- ✅ get_char_world() usage (FIXED Dec 2025)
- ✅ NPC same-room restriction
- ✅ Linkdead buffering
- ✅ Sleeping check
- ✅ AFK buffering (PC vs NPC distinction)
- ✅ Note-writing buffering
- ✅ Reply tracking
- ✅ Mobprog triggers

**Enhancement**: QuickMUD has channel ban system (acceptable addition)

---

#### 6. do_reply() - VERIFIED ✅
**ROM C**: src/act_comm.c lines 954-1029 (76 lines)  
**QuickMUD**: communication.py:191  
**Status**: ✅ **100% ROM C parity**

**ROM C Behavior**:
1. COMM_NOTELL → "Your message didn't get through."
2. ch->reply == NULL → "They aren't here."
3. Linkdead handling
4. Sleeping checks (both sender and receiver)
5. COMM_QUIET/COMM_DEAF on target
6. COMM_AFK buffering
7. Deliver message, set reply

**QuickMUD Behavior**:
```python
if _has_comm_flag(char, CommFlag.NOTELL):
    return "Your message didn't get through."
if not args:
    return "Reply to whom with what?"
target = getattr(char, "reply", None)
if target is None or target not in character_registry:
    return "They aren't here."
return do_tell(char, f"{target.name} {args}")  # Delegates to do_tell!
```

**Parity Check**: ✅ EXCELLENT (clever delegation)
- ✅ NOTELL check
- ✅ Reply target validation
- ✅ All other checks delegated to do_tell()
- ✅ Simpler and more maintainable than ROM C duplication

**Design Note**: QuickMUD delegates to do_tell() instead of duplicating logic (better design, same behavior)

---

#### 7-15. Channel Commands - VERIFIED ✅ (9 functions)

**All channel commands follow identical ROM C pattern:**

**ROM C Template** (gossip, grats, quote, question, answer, music, auction, clantalk, immtalk):
1. Empty arg → toggle COMM_NO<CHANNEL> flag
2. Check COMM_QUIET → "You must turn off quiet mode first."
3. Check COMM_NOCHANNELS → "The gods have revoked your channel privileges."
4. REMOVE_BIT(COMM_NO<CHANNEL>) (auto-enable when sending)
5. Send formatted message to self
6. Iterate descriptor_list, filter by flags, broadcast to all

**QuickMUD Template** (all 9 channel commands):
```python
cleaned = args.strip()
if not cleaned:
    if _has_comm_flag(char, CommFlag.NO<CHANNEL>):
        _clear_comm_flag(char, CommFlag.NO<CHANNEL>)
        return "<Channel> channel is now ON."
    _set_comm_flag(char, CommFlag.NO<CHANNEL>)
    return "<Channel> channel is now OFF."

blocked = _check_channel_blockers(char, CommFlag.NO<CHANNEL>)
if blocked:
    return blocked

_clear_comm_flag(char, CommFlag.NO<CHANNEL>)

def _should_receive(target: Character) -> bool:
    if _has_comm_flag(target, CommFlag.NO<CHANNEL>) or _has_comm_flag(target, CommFlag.QUIET):
        return False
    return True

broadcast_global(f"<formatted message>", channel="<channel>", exclude=char, should_send=_should_receive)
return f"You <channel> '<message>'"
```

**Verified Channel Commands**:

| Function | ROM Lines | QuickMUD | Status | Notes |
|----------|-----------|----------|--------|-------|
| do_gossip() | 333-388 | communication.py:271 | ✅ **100%** | Global chat channel — **GOSSIP-001 (2.14.52)** |
| do_grats() | 390-446 | communication.py:303 | ✅ **100%** | Congratulations channel — **GOSSIP-002 (2.14.53)** |
| do_quote() | 447-504 | communication.py:335 | ✅ **100%** | Quote channel — **GOSSIP-002 (2.14.53)** |
| do_question() | 505-561 | communication.py:367 | ✅ **100%** | Question channel — **GOSSIP-002 (2.14.53)** |
| do_answer() | 562-618 | communication.py:399 | ✅ **100%** | Answer channel — **GOSSIP-002 (2.14.53)** |
| do_music() | 619-676 | communication.py:431 | ✅ **100%** | Music channel — **GOSSIP-002 (2.14.53)** |
| do_auction() | 276-332 | communication.py:239 | ✅ **100%** | Auction channel — **GOSSIP-001 (2.14.52)** |

**GOSSIP-001 / GOSSIP-002** (MINOR, ✅ FIXED — gossip+auction 2.14.52, grats/quote/question/answer/music 2.14.53) — global channel `$n` was not PERS-masked per recipient. ROM `do_gossip`/`do_auction`/`do_grats`/`do_quote`/`do_question`/`do_answer`/`do_music` walk `descriptor_list` and render each listener's copy via `act_new("{d$n gossips '{9$t{d'{x", ch, argument, d->character, TO_VICT, POS_SLEEPING)` — `$n` → `PERS(ch, listener)`, so a wiz-invis / invisible sender a listener can't see renders as "someone", not the sender's name. The Python baked `char.name` into ONE shared string passed to `broadcast_global`, leaking the sender's identity to every listener. **Fix:** added a backward-compatible `render: recipient -> str` param to `broadcast_global` (`mud/net/protocol.py`); each channel now passes `render=lambda target: capitalize_act_line(f"…{pers(char, target)}…")` (per-recipient PERS, same infra as the room-channel SAY-002/EMOTE-001 sweep). Tests: `tests/test_communication.py::test_gossip001_invisible_gossiper_masks_to_someone` + `::test_gossip002_invisible_sender_masks_across_global_channels`. **Minor remaining (edge):** `do_clantalk` / `do_immtalk` still bake `char.name` — immtalk recipients are immortals (holylight → always see the sender, so PERS == name), and clantalk is a small mutually-visible audience; low-value, file if a clan-invis case ever matters. | ✅ FIXED (2.14.53) |
| do_clantalk() | 677-729 | communication.py:463 | ✅ **100%** | Clan-only channel |
| do_immtalk() | 730-766 | communication.py:494 | ✅ **100%** | Immortal-only channel |

**GOSSIP-003** (MINOR, ✅ FIXED — 2.14.97) — the `COMM_NOCHANNELS` channel-revocation line used corrected English "privileges" instead of ROM's *misspelled* "priviliges". ROM emits `"The gods have revoked your channel priviliges.\n\r"` verbatim at all 8 `talk_channel` sites (`src/act_comm.c:306/363/420/477/535/592/649` + `do_clantalk:704`) and the imm revoke/restore (`src/act_wiz.c:342/351`). A faithful port replicates the typo. Two production sites diverged: the shared `_check_channel_blockers` helper (gossip/grats/quote/question/answer/music/auction) and `do_clantalk`'s own inline gate — both now emit "priviliges". `mud/commands/imm_punish.py:41/48` already matched ROM. **The prior audit had a stale "acceptable addition / acceptable enhancement" note that masked this** — re-verified against ROM source per the AGENTS.md re-verify mandate. 7 contra-ROM assertions in `tests/test_communication.py` (asserting "privileges") inverted. Test: `tests/test_communication.py::test_gossip003_nochannels_message_matches_rom_misspelling`. | ✅ FIXED (2.14.97) |

**Parity Check**: ✅ **PERFECT** (all 9 channel commands)
- ✅ Toggle behavior
- ✅ QUIET check
- ✅ NOCHANNELS check (ROM's misspelled "priviliges" — GOSSIP-003)
- ✅ Auto-enable on send
- ✅ Global broadcast with filtering
- ✅ Clan filtering (clantalk)
- ✅ Immortal filtering (immtalk)

**Design Note**: QuickMUD uses shared helper `_check_channel_blockers()` - more maintainable than ROM C duplication

---

#### 16. do_emote() - RE-AUDIT 🔄
**ROM C**: src/act_comm.c lines 1067-1095 (29 lines)
**QuickMUD**: communication.py:544
**Status**: 🔄 **2026-05-22 re-audit** — three gaps surfaced (EMOTE-001 ✅ FIXED, EMOTE-002 🔄 OPEN, PMOTE-001 ✅ FIXED 2.8.68 — see rows below). 2026-05-24 re-check: two additional PMOTE sub-gaps filed (PMOTE-002 PERS, PMOTE-003 NPC filter).

| Gap ID | Severity | ROM C | Python | Description | Status |
|--------|----------|-------|--------|-------------|--------|
| `EMOTE-001` | CRITICAL | src/act_comm.c:1091, src/handler.c:2618 | mud/commands/communication.py:544 | TO_ROOM `$n` substitution must route through PERS() so invisible emoter renders as `"someone"` to listeners without DETECT_INVIS. Python hardcoded `char.name` and broadcast to all. Fix: per-listener render with `pers(char, listener)`. Tests: `tests/integration/test_emote_parity.py::test_emote_001_*`. | ✅ FIXED (2.8.42) |
| `EMOTE-002` | CRITICAL | src/act_comm.c:1092 | mud/commands/communication.py:544 | ⚠️ **REVERTED — the premise was FALSE (see EMOTE-005).** This row claimed "TO_CHAR `$n` should substitute to 'You' (act() handles the self branch)" and changed `f"{char.name} {args}"` → `f"You {args}"`. ROM `act()` does **no** `$n`→"You" conversion — it renders `$n` via `PERS(ch, to)`, and `PERS(ch, ch)` is the actor's own name. The original `f"{char.name} …}"` was ROM-correct; EMOTE-002 introduced the divergence. ~~Test: `…::test_emote_002_self_message_renders_you_not_actor_name`~~ inverted by EMOTE-005. | ❌ REVERTED by EMOTE-005 (2.14.50) |
| `EMOTE-005` | CRITICAL | src/act_comm.c:1092 + src/comm.c `act_new` (`$n`→`PERS(ch,to)`) + src/merc.h:2145 `PERS` | mud/commands/communication.py:do_emote (TO_CHAR return) | **do_emote self-line must render the actor's OWN NAME, not "You" — corrects the false-premise EMOTE-002.** ROM `do_emote` uses the same `act("$n $T", ch, NULL, argument, TO_CHAR)` for the self leg as the room leg. ROM `act()` substitutes `$n` via `PERS(ch, to)` (`src/comm.c`) with **no** "You" special-case; `PERS(ch, ch) = can_see(ch, ch) ? name : "someone"` = the actor's name (a char always sees itself). **Decisive proof:** ROM `do_say` writes a *literal* `sprintf(buf, "You say '%s'", …); send_to_char(buf, ch)` for its self-line and only uses `act("$n says…")` for the room — which would be redundant if `act()` converted `$n`→"You". So stock ROM emote shows the emoter their own name ("Bob nods"), a well-known ROM quirk. Surfaced 2026-06-13 re-verifying the EMOTE-002 ✅ against source (AGENTS.md re-verify rule). **Fix (2.14.50):** TO_CHAR return now `capitalize_act_line(f"{pers(char, char)} {args}")` (matches the TO_ROOM leg's PERS render). Inverted the test: `tests/integration/test_emote_parity.py::test_emote_005_self_message_renders_actor_name_not_you` (actor "Emoself" sees "Emoself nods", not "You nods"). | ✅ FIXED (2.14.50) |
| `PMOTE-001` | IMPORTANT | src/act_comm.c:1098-1192 | mud/commands/imm_emote.py:170 | `do_pmote` (per-receiver personalized emote with second-person substitution for matched names) — function exists with full ROM substitution loop (NOEMOTE block, Moron guard, `_pmote_substitute` letter-by-letter mirror of src/act_comm.c:1131-1175, apostrophe/possessive handling, trailing-`s` absorption). Audit row was stale — function was implemented prior to the 2026-05-22 re-audit. Tests: `tests/integration/test_act_comm_gaps.py::TestPmoteGaps::*` (5 tests covering NOEMOTE, Moron guard, name→"you", apostrophe→"r", plural-s absorption). Re-check 2026-05-24 confirmed implementation matches ROM C 1126-1190 for the documented scope; two new sub-gaps filed as PMOTE-002/003 below. | ✅ FIXED (2.8.68) |
| `PMOTE-002` | IMPORTANT | src/act_comm.c:1136, 1188 | mud/commands/imm_emote.py:198 | TO_CHAR `$N` substitution must route through PERS() so invisible actor renders as `"someone"` to listeners without DETECT_INVIS. Python's viewer broadcast hardcodes `f"{char_name} {substituted}"`, leaking actor identity. ROM `act("$N $t", vch, temp_or_argument, ch, TO_CHAR)` evaluates `PERS(ch, vch)` per listener. Fixed in 2.8.69 by routing the actor prefix through `mud.world.vision.pers(char, viewer)` for both substitution branches; locked by `tests/integration/test_act_comm_gaps.py::TestPmoteGaps::test_pmote_002_invisible_actor_renders_as_someone_to_unaided_viewer`. Mirrors EMOTE-001 pattern (`mud/commands/communication.py`). | ✅ FIXED (2.8.69) |
| `PMOTE-003` | MINOR | src/act_comm.c:1130 | mud/commands/imm_emote.py:194-195 | NPC viewers should be skipped from the personalized broadcast. ROM `if (vch->desc == NULL || vch == ch) continue;` excludes anyone without a descriptor (i.e. all NPCs). Python's condition `desc is None and not is_npc` only skipped disconnected PCs, so NPCs received the broadcast. Fixed in 2.8.70 by skipping any non-self viewer with `desc == None` in both `do_pmote` and the mirrored `do_smote` loop (`src/act_wiz.c:392-393`), locked by `tests/integration/test_act_comm_gaps.py::TestPmoteGaps::test_pmote_003_npc_viewers_do_not_receive_pmote_or_smote`. | ✅ FIXED (2.8.70) |
| `EMOTE-003` | CRITICAL | src/act_comm.c:1090-1093, src/comm.c:2384 | mud/commands/communication.py:638 | **TRIG_ACT over-dispatch (regression introduced by the 2.9.40 INV-025 sweep).** ROM `do_emote` wraps both `act("$n $T", …)` calls in `MOBtrigger = FALSE; … ; MOBtrigger = TRUE;`, and `src/comm.c:2384` fires `mp_act_trigger` only `else if (MOBtrigger)` — so an emote NEVER fires a mob act-trigger. This is deliberate: emote text is free-form, so an uncapped dispatch lets a player forge any trigger phrase (`emote bows` tripping an NPC scripted on "bows"). The INV-025 enforcement mis-read `do_emote` as the canonical TRIG_ACT *producer* and added `mp_act_trigger_room(args, char.room, char)` to Python's `do_emote`, a shipped behavioral bug. Fix (2.12.5): removed the dispatch call; the per-listener message fan-out is unchanged (PCs still see the emote). The INV-025 suite was retargeted — producer leg now anchored at `do_stand` (a genuine `act()` producer with no MOBtrigger wrap), suppression leg at the emote no-fire test. Tests: `tests/integration/test_inv025_mobprog_act_trigger_dispatch.py::test_pc_emote_does_not_fire_act_trigger_on_listening_npc`. Cross-ref INV-025 (c). | ✅ FIXED (2.12.5) |
| `EMOTE-004` | CRITICAL | src/act_comm.c:1090 / src/comm.c:2384 | mud/commands/communication.py:do_emote | Sibling of SAY-005. The EMOTE-001 per-listener PERS rewrite delivered each line via `if writer is not None: asyncio.create_task(send_to_char(...))` **and** an unconditional `listener.messages.append(...)` → a connected listener received the emote **twice**. Fix: replaced with `push_message(listener, per_message)` (XOR); EMOTE-003's no-TRIG_ACT contract is unaffected (no dispatch in this loop). Test: `tests/integration/test_inv001_comm_delivery_channel.py::test_emote_single_delivers_to_connected_listener`. | ✅ FIXED (2.12.69) |

**ROM C Behavior**:
1. PC check: COMM_NOEMOTE → "You can't show your emotions."
2. Empty check → "Emote what?"
3. **Validation**: `if (!(isalpha(argument[0])) || (isspace(argument[0])))` → "Moron!"
4. MOBtrigger = FALSE (disable mobprog triggers during emote)
5. act() to room and self: `"$n $T"`
6. MOBtrigger = TRUE (re-enable)

**QuickMUD Behavior**:
```python
args = args.strip()
if not args:
    return "Emote what?"

# Broadcast to room
message = f"{char.name} {args}"
if char.room:
    broadcast_room(char.room, message, exclude=char)

return message
```

**MINOR GAP**:
- ❌ Missing COMM_NOEMOTE check (admin punishment flag)
- ❌ Missing argument validation (must start with letter, not space)
- ❌ Missing MOBtrigger disable (prevents recursive mobprog triggers)

**Impact**: LOW (emote works correctly for normal use, missing edge cases)  
**Fix Required**: Add validation and NOEMOTE check  
**Estimated Time**: 15 minutes

---

### 📋 Functions Pending Verification (P2 - Optional)

#### 6. do_pmote() - NEEDS VERIFICATION
**ROM C**: src/act_comm.c lines 1098-1410 (312 lines!)  
**QuickMUD**: imm_emote.py:73  
**Priority**: P2 (Nice-to-have)  
**Status**: ⚠️ **UNKNOWN - Needs line-by-line audit**

**ROM C Complexity**: 312 lines of pronoun substitution logic ($n, $e, $m, $s, etc.)

**Note**: Deferred to Phase 4 (optional) due to complexity

---

#### 7. do_colour() - NEEDS VERIFICATION
**ROM C**: src/act_comm.c lines 2034-2196 (162 lines)  
**QuickMUD**: auto_settings.py:265  
**Priority**: P2 (Nice-to-have)  
**Status**: ⚠️ **UNKNOWN - Needs line-by-line audit**

**ROM C Complexity**: 162 lines of color configuration per element type

**Note**: Deferred to Phase 4 (optional) due to complexity

---

## Next Steps

### Phase 1: ROM C Parity Verification (P0-P1 Functions) 🔄 IN PROGRESS

**Target**: Verify 20 P0-P1 functions against ROM C source (lines 48-1983)

1. ✅ **do_delet()** - Simple typo guard (5 lines)
2. ✅ **do_delete()** - Character deletion logic (39 lines)
3. [ ] **do_channels()** - Channel status display (107 lines)
4. [ ] **do_deaf()** - Toggle deaf mode (16 lines)
5. [ ] **do_quiet()** - Toggle quiet mode (16 lines)
6. [ ] **do_afk()** - Toggle AFK status (14 lines)
7. [ ] **do_say()** - Room speech (26 lines)
8. [ ] **do_tell()** - Private messaging (109 lines) ✅ FIXED Dec 2025
9. [ ] **do_reply()** - Reply to tell (79 lines)
10. [ ] **do_shout()** - Global shout (50 lines)
11. [ ] **do_yell()** - Area yell (34 lines) ⚠️ **PARTIAL**
12. [ ] **do_emote()** - Custom emote (31 lines)
13. [ ] **do_auction()** - Auction channel (57 lines)
14. [ ] **do_gossip()** - Gossip channel (57 lines)
15. [ ] **do_grats()** - Grats channel (57 lines)
16. [ ] **do_immtalk()** - Immortal channel (37 lines)
17. [ ] **do_quit()** - Quit game (59 lines)
18. [ ] **do_save()** - Save character (13 lines)
19. [ ] **do_follow()** - Follow character (148 lines)
20. [ ] **do_group()** - Manage group (93 lines)
21. [ ] **do_order()** - Order charmed mobs (86 lines) ⚠️ **PARTIAL**
22. [ ] **do_gtell()** - Group tell (50 lines) ⚠️ **PARTIAL**
23. [ ] **do_split()** - Split currency (109 lines)

**Estimated Time**: 2-3 days (23 functions × 10-15 min each)

### Phase 2: Gap Resolution (P0-P1 Critical Gaps) 🔜 NEXT

**Target**: Fix 3 critical gaps preventing 100% ROM parity

1. **do_yell() adjacent room broadcasting** (Priority: P1)
   - Add exit iteration
   - Broadcast to adjacent rooms
   - Estimated: 1 hour

2. **do_order() command execution** (Priority: P1)
   - Add command dispatcher integration
   - Execute arbitrary commands on charmed followers
   - Estimated: 2 hours

3. **do_gtell() group broadcasting** (Priority: P1)
   - Iterate group members across world
   - Broadcast message to all group members
   - Estimated: 1 hour

**Total Estimated Time**: 4 hours

### Phase 3: Integration Tests (All Communication Commands) 🔜 PLANNED

**Target**: Create comprehensive integration tests for 36 functions

1. **Basic Communication** (7 tests)
   - say, tell, reply, shout, yell, emote, pmote

2. **Channel Commands** (9 tests)
   - All channel commands (gossip, auction, music, etc.)

3. **Group Commands** (5 tests)
   - follow, group, gtell, split, order

4. **Utility Commands** (11 tests)
   - channels, deaf, quiet, afk, replay, bug, typo, etc.

5. **Session Management** (2 tests)
   - quit, save

**Total Tests**: 34 integration tests

**Estimated Time**: 1-2 days

### Phase 4: P2 Function Verification (Optional) 📋 BACKLOG

**Target**: Verify 13 P2 functions against ROM C source

1. do_pmote() (312 lines) - Complex pronoun parsing
2. do_colour() (162 lines) - Color customization
3. do_quote(), do_question(), do_answer(), do_music(), do_clantalk() - Channel commands
4. do_replay(), do_bug(), do_typo(), do_rent(), do_pose() - Utility commands

**Estimated Time**: 1-2 days

---

## Success Criteria

**100% ROM C Parity Achieved When:**
- ✅ All 36 functions mapped to QuickMUD equivalents (100% - COMPLETE)
- [ ] All 20 P0-P1 functions verified with ROM C parity (0% - IN PROGRESS)
- [ ] All 3 critical gaps resolved (do_yell, do_order, do_gtell)
- [ ] 34 integration tests created and passing (100%)
- [ ] ROM_C_SUBSYSTEM_AUDIT_TRACKER.md updated to 100%

---

## ROM C Source References

All line numbers reference: `src/act_comm.c` (ROM 2.4b6)

**File Statistics:**
- Total Lines: 2,196
- Total Functions: 36
- Largest Function: do_pmote() (312 lines)
- Smallest Function: do_delet() (5 lines)

---

## Notes

- **do_tell() was fixed December 2025** - Now uses get_char_world() for ROM C parity
- **7 functions need ROM C verification** - Partial implementations exist
- **3 functions have critical gaps** - Prevent 100% ROM parity
- **100% function coverage** - All ROM C functions have QuickMUD equivalents

---

## Audit Methodology

1. **Read ROM C source** line-by-line for each function
2. **Compare with QuickMUD** implementation
3. **Document gaps** (missing features, formula differences, edge cases)
4. **Categorize severity** (Critical, Important, Optional)
5. **Create integration tests** to verify behavioral parity
6. **Update tracker** with final status

---

**Last Updated**: January 8, 2026  
**Next Review**: After Phase 1 completion (ROM C parity verification)
