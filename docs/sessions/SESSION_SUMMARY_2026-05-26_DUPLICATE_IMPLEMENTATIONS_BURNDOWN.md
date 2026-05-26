# Session Summary — 2026-05-26 — DUPLICATE_IMPLEMENTATIONS burn-down (2.9.22 → 2.9.29)

## Scope

Closed all 5 ❌ real-bug rows in
`docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md` across 8 commits
(2.9.22 → 2.9.29). DUPL-001 fragmented into 4 sub-rows (DUPL-001
conditions, DUPL-001a output_buffer, DUPL-001b combat/skills, DUPL-001c
game_loop) when fix-time re-audit surfaced bug-class divergences the
original audit row had compressed into one. All 8 commits pushed to
`origin/master`. Fix-time re-audit invalidated two prior session
classifications — see "Methodology refinements" below.

## Outcomes

### `DUPL-002` — ✅ FIXED (2.9.22)

- **Python**: `mud/magic/effects.py`, `mud/combat/engine.py` → re-export from new canonical `mud/utils/messaging.py:push_message`.
- **ROM C**: `src/comm.c:write_to_buffer` — single delivery channel.
- **Fix**: Magic-effects copy of `_push_message` appended to BOTH async socket and `char.messages`; connection read loop drains `char.messages` after every command, so every poison/plague/paralyze tick replayed once per prompt. Consolidated to new canonical `mud/utils/messaging.py:push_message` (async-then-return single-delivery contract).
- **Tests**: 2 cases in `tests/integration/test_magic_effect_message_no_duplicate.py`.

### `DUPL-004` — ✅ FIXED (2.9.23)

- **Python**: `mud/commands/misc_player.py:do_peek`. Dead stubs in `mud/commands/thief_skills.py` + `mud/commands/remaining_rom.py` deleted.
- **ROM C**: `src/act_info.c:505` — `check_improve(ch, gsn_peek, TRUE, 4)`.
- **Fix**: Local `pass`-body `_check_improve` stub silently skipped skill improvement on successful peek rolls. Worse — a function-body `from mud.core.dice import number_percent` referenced a non-existent module, so any successful peek would have raised `ModuleNotFoundError`. Wired to canonical `mud.skills.registry.check_improve(multiplier=4)` per ROM, migrated RNG to `mud.utils.rng_mm.number_percent` per Parity Rules. The other two `_check_improve` copies (thief_skills, remaining_rom) were dead — re-verification showed `do_sneak`/`do_hide` already delegate to `mud/skills/handlers.py` canonical.
- **Tests**: 2 cases in `tests/integration/test_do_peek_check_improve.py` (success path calls canonical, failure path does not).

### `DUPL-001` (conditions) — ✅ FIXED (2.9.24)

- **Python**: `mud/characters/conditions.py:_send_to_char` → canonical `send_to_char_buffered`.
- **ROM C**: `src/act_info.c:gain_condition`.
- **Fix**: Local `_send_to_char` stub appended ONLY to `char.messages`. The connection delivery path uses `asyncio.create_task(send_to_char(...))`, so connected PCs never received hunger/thirst/sober tick messages — they existed only in the test buffer. Added new canonical `mud.utils.messaging.send_to_char_buffered` (extension of `push_message` for the `send_to_char` call shape).
- **Tests**: 2 cases in `tests/integration/test_gain_condition_delivers_to_connected_pc.py`.

### `DUPL-001a` — ✅ FIXED (2.9.25, fresh bug class)

- **Python**: 9 files — `mud/commands/imm_load.py`, `imm_emote.py`, `imm_admin.py`, `imm_commands.py`, `imm_display.py`, `imm_punish.py`, `imm_server.py`, `admin_commands.py`, `remaining_rom.py`.
- **Fix**: Re-reading the 13 `_send_to_char` bodies surfaced 9 byte-identical stubs writing to `char.output_buffer` — an attribute the production connection read loop never drains. Every staff message routed through them (do_protect "You are now immune to snooping.", do_pmote, do_guild, do_violate, etc.) vanished. Migrated to canonical `send_to_char_buffered`. Trojan-horse tests in `test_act_comm_gaps.py` (11) and `test_act_wiz_command_parity.py` (2) had been asserting against `output_buffer` directly — same Trojan-horse pattern as the 2.9.21 `rom_api.py` deletion. Migrated 13 asserts to read `messages`.
- **Tests**: `tests/integration/test_imm_command_delivery_dupl_001a.py` pins `output_buffer` is never created.

### `DUPL-001b` — ✅ FIXED (2.9.26)

- **Python**: `mud/combat/assist.py`, `mud/skills/handlers.py`.
- **Fix**: Both `_send_to_char` copies wrote to BOTH async socket AND `char.messages` — same DUPL-002-class duplicate-delivery. Every combat auto-assist emote (`Hero rescues you!`) and every skill-handler outcome (`Your sanctuary fades.`) replayed once per prompt for connected PCs. Consolidated; `_broadcast_room` in `assist.py` now appends `"\n"` at the call site to preserve previous newline behavior.
- **Tests**: 3 cases in `tests/integration/test_dupl_001b_no_duplicate_delivery.py`.

### `DUPL-001c` — ✅ FIXED (2.9.27, classification corrected at fix-time)

- **Python**: `mud/game_loop.py:_send_to_char`.
- **Fix**: Prior session had labeled this "canonical-equivalent tidying, no bug." Fix-time re-audit invalidated that: the copy did `asyncio.create_task(send)` AND `messages.append()` unconditionally (no early return after async branch). Every tick-driven message — plague agony, light flicker/burnout, decay-timer void teleport, fever spread, cold suffering, decay broadcasts (`mud/game_loop.py:475,477,480,523,575,609,651,720,1057,1139`) — double-delivered for connected PCs. Consolidated to canonical.
- **Tests**: 2 cases in `tests/integration/test_dupl_001c_game_loop_no_duplicate.py`.
- **Result**: All 13 sites of DUPL-001 (`_send_to_char`) now route through canonical `send_to_char_buffered`. Audit row flipped to ✅ FIXED.

### `DUPL-003` — ✅ FIXED (2.9.28)

- **Python**: `mud/commands/obj_manipulation.py:_extract_obj` (adapter), `mud/commands/imm_load.py:_extract_obj` → canonical `mud/game_loop.py:_extract_obj`.
- **ROM C**: `src/handler.c:2051-2096 extract_obj`.
- **Fix**: Both copies read `char.carrying` — a non-existent attribute on `Character` (canonical per Parity Rules is `char.inventory`). `do_quaff` printed flavor text and cast the potion's spells, but the potion stayed in inventory: **infinite quaff bug**. The non-recursive bug also leaked container contents (extracting a chest left items dangling with `in_obj` pointing at the extracted parent). Both copies routed through canonical `game_loop._extract_obj(obj)` — recurses over `contains`, unlinks from `in_room`/`carried_by`/`in_obj`, removes from `object_registry`. `obj_manipulation.py` retains a thin `(char, obj)` adapter for call-site compatibility.
- **Tests**: 2 cases in `tests/integration/test_dupl_003_extract_obj.py` — `do_quaff` inventory removal + recursive container-contents extraction on `do_sacrifice`.

### `DUPL-005` — ✅ FIXED (2.9.29)

- **Python**: `mud/loaders/json_area_loader.py` (244 lines) deleted.
- **Fix**: Investigation surfaced the file as dead — zero importers in `mud/` or `tests/` (only `archive/specs/` mentioned it). The live `mud/loaders/json_loader.py` (re-exported via `mud/loaders/__init__.py` as "the FULL loader with resets") already handles BOTH on-disk JSON schemas — root-level `vnum_range.min/max` AND nested `{"area": {...}}` wrapper. `json_area_loader.py` was a strict-subset duplicate eligible for accidental activation by import order. Same Trojan-horse pattern as the 2.9.21 rom_api.py deletion.
- **Tests**: No new test — deletion verified by 33 existing area-loader tests staying green.

## Methodology refinements

Two prior-session classifications were invalidated by fix-time re-reads:

1. **DUPL-001 was originally a single audit row** ("`_send_to_char` — messages-only fallback for conditions"). Fix-time re-reading surfaced two fresh bug classes the original audit had compressed: `output_buffer` black-hole (9 sites, DUPL-001a) and duplicate-delivery (3 sites, DUPL-001b + DUPL-001c). The audit row was correct that the file had divergences; it under-counted by 4×.
2. **DUPL-001c was originally labeled "canonical-equivalent tidying only"** based on a structural similarity to canonical. Actual code did async AND mailbox unconditionally. Tidying claim was wrong — was a real duplicate-delivery bug for every tick-driven message.

Lesson: re-audit at fix-time, not just at audit-time. Each fix is cheap; each false-clean claim is a regression risk that survives until the next audit.

## Files Modified

- `mud/utils/messaging.py` — NEW. Canonical `push_message` + `send_to_char_buffered`.
- `mud/magic/effects.py`, `mud/combat/engine.py` — re-export DUPL-002.
- `mud/commands/misc_player.py` — DUPL-004 (canonical `check_improve` + `rng_mm.number_percent`).
- `mud/commands/thief_skills.py`, `mud/commands/remaining_rom.py` — DUPL-004 dead stubs deleted.
- `mud/characters/conditions.py` — DUPL-001 conditions (messages-only fallback).
- 9 imm_*/admin_commands/remaining_rom files — DUPL-001a (output_buffer black-hole).
- `mud/combat/assist.py`, `mud/skills/handlers.py` — DUPL-001b (duplicate-delivery).
- `mud/game_loop.py` — DUPL-001c (duplicate-delivery, ALSO drops unused top-level `import asyncio`).
- `mud/commands/obj_manipulation.py`, `mud/commands/imm_load.py` — DUPL-003 (recursive extract via canonical).
- `mud/loaders/json_area_loader.py` — DELETED, DUPL-005.
- `tests/integration/` — 5 new files (test_magic_effect_message_no_duplicate, test_do_peek_check_improve, test_gain_condition_delivers_to_connected_pc, test_imm_command_delivery_dupl_001a, test_dupl_001b_no_duplicate_delivery, test_dupl_001c_game_loop_no_duplicate, test_dupl_003_extract_obj). 2 test files migrated off the `output_buffer` Trojan-horse pattern (test_act_comm_gaps, test_act_wiz_command_parity).
- `docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md` — DUPL-001 / 002 / 003 / 004 / 005 rows flipped to ✅ FIXED.
- `CHANGELOG.md` — entries for 2.9.22 through 2.9.29.
- `pyproject.toml` — 2.9.21 → 2.9.29.

## Test Status

- Full suite: **4730 passed, 4 skipped, 0 failed** (latest run, 7m17s wall-clock).
- 17 new regression tests across the 5 DUPL rows.
- Pre-fix flake count: 0. Post-fix flake count: 0.

## Next Steps

DUPLICATE_IMPLEMENTATIONS ❌ rows fully closed. Three open paths for the next session:

1. **DUPLICATE_IMPLEMENTATIONS ⚠️ rows.** 3 DEAD-CODE rows (DUPL-006 to DUPL-008) and ~20 CLEANUP rows (DUPL-009 to DUPL-024) remain in the same audit. Low individual risk — they're consolidations and dead-code deletions, not parity bugs — but the audit's track record of surfacing real bugs at fix-time (DUPL-001a, DUPL-001c) suggests reading each row before classifying as cleanup-only.
2. **Next META_AUDIT class.** 7 of 8 classes left. Per the META_AUDIT_TAXONOMY queue:
   - BROADCAST_COVERAGE (~130 commands, expected M ❌/⚠️ gaps — but DUPL audit shifted estimates 5×; re-estimate at audit-time).
   - ARITHMETIC_BOUNDARY (defensive `max(1, ...)` floors ROM doesn't have).
   - TRIGGER_CALL_SITE_MIGRATION (HPCNT-001-shaped findings).
3. **Cross-file invariants pass** (active mode per AGENTS.md when per-file audit tracker is exhausted). Current candidates from prior sessions: mob script triggers (ENTRY/GIVE/KILL/RANDOM/HPCNT firing), group/follower chain (leader/master pointers, group XP split, follow propagation, disband-on-death).

Recommendation: **option 1 (cleanup rows)** for one short session to fully close the DUPLICATE_IMPLEMENTATIONS audit — then move to option 2 (BROADCAST_COVERAGE) which is the highest-cardinality audit in the META queue and likely to surface the next big bug cluster. Closing the audit fully is worth one session's time to avoid leaving a partly-burned-down tracker rotting.

No push to origin until explicit per-cluster user approval.
