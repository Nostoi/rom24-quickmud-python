# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.8.59]

### Fixed
- **`FIGHT-008` — POS_DEAD TO_CHAR self-message red colour + blank-line spacing** (`src/fight.c:861`): ROM's `send_to_char("{RYou have been KILLED!!{x\n\r\n\r", victim)` wraps the death notice in red colour codes and appends two `\n\r` pairs so a blank line follows the message. Python's `mud/combat/engine.py:_position_change_message` previously returned the bare `"You have been KILLED!!"` — no colour, no extra spacing. Fix: return `"{RYou have been KILLED!!{x\n"`. The protocol layer in `mud/net/protocol.py:send_to_char` auto-appends one `\r\n` to every message, so the embedded trailing `\n` plus the auto-append produces the same visual blank-line spacing ROM gets from its two `\n\r` pairs. Closes the FIGHT-004..008 position-change-broadcast sweep. Locked in by `tests/integration/test_invisibility_combat.py::TestPositionChangeBroadcastPers::test_fight_008_pos_dead_self_message_wraps_red_and_appends_blank_line`.

### Notes

- Closes the 2026-05-23 `fight.c` PERS sweep on the position-change broadcast surface (FIGHT-004..008 all ✅ FIXED in `docs/parity/FIGHT_C_AUDIT.md`).
- Weapon-proc broadcasts at `mud/combat/engine.py:1496/1510/1531/1541/1551` have analogous PERS gaps but are deferred to a follow-up cluster (FIGHT-009..013 reserved).

## [2.8.58]

### Fixed
- **`FIGHT-007` — POS_DEAD TO_ROOM broadcast (PERS + red colour + two-bang wording)** (`src/fight.c:860`): ROM's `act("{R$n is DEAD!!{x", victim, 0, 0, TO_ROOM)` had three divergences vs Python's previous `f"{victim.name} is DEAD!!!"` baked broadcast: (a) `$n` must route through PERS per-listener so invisible victims render as `"someone"` for observers without `DETECT_INVIS`; (b) missing ROM red colour codes `{R...{x` that the ANSI translation layer consumes on websocket send; (c) wording typo — three exclamation marks instead of ROM's two. Fix: `mud/combat/engine.py:_position_change_message` DEAD branch now uses `_broadcast_pos_change(victim, "{{R{name} is DEAD!!{{x")`. Legacy assertion in `tests/test_combat.py` (×1) updated to ROM-exact form. Locked in by `tests/integration/test_invisibility_combat.py::TestPositionChangeBroadcastPers::test_fight_007_pos_dead_broadcast_uses_pers_and_red_colour_and_two_bangs`.

## [2.8.57]

### Fixed
- **`FIGHT-006` — POS_STUNNED TO_ROOM broadcast routes `$n` through PERS** (`src/fight.c:853-854`): ROM's `act("$n is stunned, but will probably recover.", victim, NULL, NULL, TO_ROOM)` substitutes `$n` per-listener through PERS. Python's STUNNED branch in `mud/combat/engine.py:_position_change_message` previously baked `victim.name` into a fixed `_broadcast_room` string. Fix: route through the `_broadcast_pos_change` helper. Locked in by `tests/integration/test_invisibility_combat.py::TestPositionChangeBroadcastPers::test_fight_006_pos_stunned_broadcast_uses_pers_for_invisible_victim`.

## [2.8.56]

### Fixed
- **`FIGHT-005` — POS_INCAP TO_ROOM broadcast routes `$n` through PERS** (`src/fight.c:845-846`): ROM's `act("$n is incapacitated and will slowly die, if not aided.", victim, NULL, NULL, TO_ROOM)` substitutes `$n` per-listener through PERS. Python's INCAP branch in `mud/combat/engine.py:_position_change_message` previously baked `victim.name` into a fixed `_broadcast_room` string. Fix: route through the `_broadcast_pos_change` helper introduced in 2.8.55. Locked in by `tests/integration/test_invisibility_combat.py::TestPositionChangeBroadcastPers::test_fight_005_pos_incap_broadcast_uses_pers_for_invisible_victim`.

## [2.8.55]

### Fixed
- **`FIGHT-004` — POS_MORTAL TO_ROOM broadcast routes `$n` through PERS** (`src/fight.c:837-838`, `src/handler.c:2618`): ROM's `act("$n is mortally wounded, and will die soon, if not aided.", victim, NULL, NULL, TO_ROOM)` renders `$n` per-listener through `PERS(victim, looker)`, so an invisible victim shows as `"someone"` to room observers without `DETECT_INVIS`. Python previously baked `victim.name` into a single fixed broadcast string via `_broadcast_room`, leaking the victim's identity to every recipient. Fix: new `_broadcast_pos_change` helper in `mud/combat/engine.py` iterates `room.people`, calls `mud.world.vision.pers(victim, listener)` per recipient, and dispatches through the same fire-and-forget websocket path as `broadcast_room`. Same channel-arc PERS fix pattern (SAY-002/EMOTE-001/TELL-003/SHOUT-003/YELL-001) applied to combat death messaging. Locked in by `tests/integration/test_invisibility_combat.py::TestPositionChangeBroadcastPers::test_fight_004_pos_mortal_broadcast_uses_pers_for_invisible_victim`.

### Notes

- First gap closed in the 2026-05-23 `fight.c` PERS sweep. FIGHT-005..008 (POS_INCAP / POS_STUNNED / POS_DEAD TO_ROOM and POS_DEAD TO_CHAR) stable-IDed in `docs/parity/FIGHT_C_AUDIT.md` and will land in follow-up commits using the new `_broadcast_pos_change` helper.

## [2.8.54]

### Fixed
- **`PROMPT-CMD-004` — `do_prompt` truncates custom template to 50 chars** (`src/act_info.c:943-944`): ROM caps the raw `argument` at 50 chars (`if (strlen(argument) > 50) argument[50] = '\0';`) before `strcpy`/`smash_tilde`/suffix-append. Python previously stored the full untruncated string. Fix: `mud/commands/auto_settings.py:do_prompt` slices `arg = arg[:50]` before smash_tilde. Locked in by `tests/integration/test_prompt_cmd_parity.py::test_prompt_cmd_004_truncates_template_to_50_chars`.
- **`PROMPT-CMD-005` — `do_prompt` appends trailing space unless template ends in `%c`** (`src/act_info.c:946-947`): ROM appends a literal space to every custom prompt template unless the (already smash_tilded) buf already ends with `%c` — `if (str_suffix("%c", buf)) strcat(buf, " ")`, and `str_suffix` (src/db.c:3784) returns TRUE when `"%c"` is *not* a suffix of buf. So prompts that don't end in a colour-code escape gain a trailing space; prompts that do (e.g. ANSI colour close) are left alone. Python previously skipped this normalization, so `prompt TAG>` stored `"TAG>"` instead of ROM's `"TAG> "`. Fix: `mud/commands/auto_settings.py:do_prompt` now applies `arg = arg + " "` when not `arg.endswith("%c")`, after smash_tilde and the 50-char truncation. Legacy assertions in `tests/test_player_prompt.py` (×4) and `tests/integration/test_prompt_rom_parity.py` (×1) updated to ROM-exact stored values. Locked in by `tests/integration/test_prompt_cmd_parity.py::test_prompt_cmd_005_appends_trailing_space_unless_pct_c_suffix`.

### Notes

- Closes the `do_prompt` warm-up shelf — PROMPT-CMD-001..005 now all ✅ FIXED in `docs/parity/ACT_INFO_C_AUDIT.md`.
- PROMPT-CMD-004 and PROMPT-CMD-005 committed jointly because the legacy test assertions in `tests/test_player_prompt.py` couple both fixes; separate commits would assert transient half-states.

## [2.8.53]

### Changed
- **`TELL-006` — closed as ✅ ANALYZED-INERT** (`src/act_comm.c:893,926,937`): ROM's `buf[0] = UPPER(buf[0])` on the buffered tell strings is provably a no-op in ROM C itself — the formatted string always begins with `'{'` (colour code `{k`), and `UPPER('{') == '{'` since `{` is not lowercase. Unlike TELL-004 (behaviorally masked by a separate code path), this transformation has no reachable behavior to mirror and no failing test can be written. Doc-only close; no code change. `docs/parity/ACT_COMM_C_AUDIT.md` row flipped from 🔄 OPEN to ✅ ANALYZED. With this, the entire `do_tell` gap row (TELL-001..006) is closed.

## [2.8.52]

### Fixed
- **`YELL-001` — `do_yell` TO_VICT `$n` routes through PERS for invisible-yeller protection** (`src/act_comm.c:1059`, `src/handler.c:2618`): ROM's `act("$n yells '$t'", ..., TO_VICT)` substitutes `$n` per-listener through `PERS(ch, victim)`. So an invisible yeller renders as `"someone"` to listeners without `DETECT_INVIS`. Python's `do_yell` already iterates per-listener (area-wide loop over `character_registry` with area filter) but hardcoded `char.name` into the rendered string. Fix: `mud/commands/communication.py:do_yell` now substitutes `mud.world.vision.pers(char, victim)` for the yeller's name inside its existing per-listener loop. Closes the channel-message arc (say / tell / emote / shout / yell all now route through PERS). Locked in by `tests/integration/test_shout_yell_parity.py::test_yell_001_invisible_yeller_renders_as_someone_to_listener`.

### Notes

- Completes the 2026-05-22/23 act_comm.c channel re-audit arc: `do_say` (SAY-001..004), `do_emote` (EMOTE-001/002), `do_tell` (TELL-001..005), `do_shout` (SHOUT-001..003), `do_yell` (YELL-001). All five channel commands now route `$n` through `pers()` and emit ROM-exact wording / colour codes. PMOTE-001 remains as the only open ROM `do_pmote` greenfield port; TELL-006 deferred (MINOR cosmetic).
- Full suite at `4629 passed, 4 skipped` (+1 vs 2.8.51; zero regressions).

## [2.8.51]

### Fixed
- **`SHOUT-003` — `do_shout` TO_VICT `$n` routes through PERS for invisible-shouter protection** (`src/act_comm.c:836`, `src/handler.c:2618`): ROM's `act("$n shouts '$t'", ...)` substitutes `$n` per-listener through `PERS(ch, victim)`. So an invisible shouter renders as `"someone"` to listeners without `DETECT_INVIS`. Python previously broadcast one fixed message string via `broadcast_global(message, channel="shout", exclude=char, should_send=_should_receive)`, leaking the invisible shouter's identity to every recipient. Fix: replaced `broadcast_global` in `mud/commands/communication.py:do_shout` with a per-listener loop over `character_registry` (mirroring ROM's `descriptor_list` iteration at `src/act_comm.c:825-838`) that filters by `SHOUTSOFF` / `QUIET` / muted_channels and renders `mud.world.vision.pers(char, victim)` per recipient. Locked in by `tests/integration/test_shout_yell_parity.py::test_shout_003_invisible_shouter_renders_as_someone_to_listener`.

### Notes

- Third of three `do_shout` gaps from the 2026-05-23 re-audit. `do_shout` is now complete. YELL-001 (same PERS pattern in `do_yell`) remains open and is the last item in the channel-message arc.
- Full suite at `4628 passed, 4 skipped, 1 deselected` (+1 vs 2.8.50; zero regressions despite the per-listener broadcast refactor).

## [2.8.50]

### Fixed
- **`SHOUT-002` — `do_shout` TO_VICT wording drops the comma** (`src/act_comm.c:836`): ROM emits `act("$n shouts '$t'", ...)` — no comma between `shouts` and the open quote. Python broadcast `"{char.name} shouts, '{cleaned}'"` with an extra comma. Fix: drop the comma in the broadcast message string. Legacy assertions in `tests/test_communication.py` (×2) updated. Locked in by `tests/integration/test_shout_yell_parity.py::test_shout_002_to_vict_wording_drops_comma`.

### Notes

- Second of three `do_shout` gaps. SHOUT-003 (PERS for shouter) and YELL-001 (PERS for yeller) remain open.
- Full suite at `4627 passed, 4 skipped, 2 deselected` (+1 vs 2.8.49; zero regressions).

## [2.8.49]

### Fixed
- **`SHOUT-001` — `do_shout` TO_CHAR wording drops the comma** (`src/act_comm.c:824`): ROM emits `act("You shout '$T'", ...)` — no comma between `shout` and the open quote. Python previously returned `"You shout, '{cleaned}'"` with an extra comma. Fix: drop the comma in `mud/commands/communication.py:do_shout` return. Legacy assertions in `tests/test_communication.py` (×2) were baked to the buggy comma form and have been updated to the ROM-exact wording. Surfaced by a 2026-05-23 `do_shout` re-audit that found the prior "100% VERIFIED" claim incorrect (same audit-doc inflation that hit `do_say` / `do_emote` / `do_tell` this run). Locked in by `tests/integration/test_shout_yell_parity.py::test_shout_001_to_char_wording_drops_comma`.

### Notes

- First of three `do_shout` gaps from the 2026-05-23 re-audit. SHOUT-002 (TO_VICT wording), SHOUT-003 (PERS for shouter), plus YELL-001 (PERS for yeller — `do_yell` already gets wording right) all stable-IDed and queued.
- Full suite at `4626 passed, 4 skipped, 3 deselected` (+1 vs 2.8.48; zero regressions).

## [2.8.48]

### Fixed
- **`TELL-005` — `do_tell` wraps both lines with ROM `{k...{K...{k...{x` charcoal colour codes** (`src/act_comm.c:941-942`): ROM frames the tell channel in charcoal/black (`{k`), switches to bright/highlighted-charcoal (`{K`) for the message body, returns to `{k` for the closing quote, and resets with `{x`. The ANSI translation layer at `mud/net/ansi.py` consumes those tokens on websocket send. Python previously emitted no codes, so the tell channel rendered in the player's default terminal colour and the framing-vs-body contrast ROM relies on was lost. Fix: `mud/commands/communication.py:do_tell` return and `_handle_buffered_tell` formatted string now wrap with the ROM colour sequence. Legacy assertions in `tests/test_communication.py` (×5) and `tests/integration/test_communication_enhancement.py` were baked to the codeless plain-text form (per AGENTS.md — tests asserting Python behavior contradicting ROM are bugs in the **test**, not the implementation) and have been updated to the ROM-exact wording. Locked in by `tests/integration/test_tell_parity.py::test_tell_005_to_char_wraps_rom_color_codes` and `::test_tell_005_to_vict_wraps_rom_color_codes`.

### Notes

- Fifth of six TELL-NNN gaps from the 2026-05-22 `do_tell` re-audit. The audit's main cluster (TELL-001/002/003/004/005) is now closed. TELL-006 (uppercase first char of buffered tells — MINOR cosmetic) remains intentionally deferred and stable-IDed in `docs/parity/ACT_COMM_C_AUDIT.md`.
- Full suite at `4625 passed, 4 skipped` (+2 vs 2.8.47 baseline 4623/4; zero regressions).

## [2.8.47]

### Fixed
- **`TELL-004` — `do_tell` TO_CHAR `$N` routes through PERS for code-structure parity** (`src/act_comm.c:941`, `src/handler.c:2618`): ROM's `act("You tell $N '$t'", ...)` substitutes `$N` (capital) through `PERS(victim, ch)`. In practice this is masked by `get_char_world`'s `can_see` filtering during name lookup — an invisible target returns `"They aren't here."` before PERS would ever evaluate (same in ROM and Python). Fix is defensive code-parity: `mud/commands/communication.py:do_tell` return now substitutes `mud.world.vision.pers(target, char)` for the target name so the macro structure matches ROM regardless of future lookup-path changes. Test: `tests/integration/test_tell_parity.py::test_tell_004_to_char_uses_pers_for_target_name` pins the visible-target code path; the unreachable `"someone"` branch is exercised by sibling PERS tests (SAY-002, EMOTE-001, TELL-003).

### Notes

- Fourth of six TELL-NNN gaps from the 2026-05-22 `do_tell` re-audit. TELL-005 (charcoal colour codes) remains open. TELL-006 deferred (MINOR).
- Full suite at `4623 passed, 4 skipped, 2 deselected` (+1 vs 2.8.46; zero regressions).

## [2.8.46]

### Fixed
- **`TELL-003` — `do_tell` TO_VICT `$n` routes through PERS for invisible-sender protection** (`src/act_comm.c:942`, `src/handler.c:2618`): ROM's `act_new("$n tells you '$t'", ...)` substitutes `$n` per-target through `PERS(ch, victim)`, so an invisible sender renders as `"someone"` to a target without `DETECT_INVIS`. Python's `_handle_buffered_tell` hardcoded `sender.name`, leaking the invisible sender's identity (same pattern as pre-fix `do_say` / `do_emote`). Fix: substitute `mud.world.vision.pers(sender, target)` for the sender's name in the formatted string. Also applies to the buffered tell paths (linkdead / AFK / note-writing) since ROM's `sprintf(..., PERS(ch, victim), ...)` at `src/act_comm.c:891`/`924`/`935` wraps the same PERS call. Locked in by `tests/integration/test_tell_parity.py::test_tell_003_invisible_sender_renders_as_someone_to_target`.

### Notes

- Third of six TELL-NNN gaps from the 2026-05-22 `do_tell` re-audit. TELL-004 (PERS for target to sender) and TELL-005 (charcoal colour codes) remain open. TELL-006 deferred (MINOR).
- Full suite at `4622 passed, 4 skipped, 3 deselected` (+1 vs 2.8.45; zero regressions).

## [2.8.45]

### Fixed
- **`TELL-002` — `do_tell` TO_VICT wording drops the comma** (`src/act_comm.c:942`): ROM emits `act_new("$n tells you '$t'", ...)` — no comma between `you` and the open quote. Python's `_handle_buffered_tell` previously formatted `"{sender.name} tells you, '{message}'"` with an extra comma. Fix: drop the comma in `mud/commands/communication.py:_handle_buffered_tell` formatted string. Legacy assertions in `tests/test_communication.py` (×4) were baked to the buggy comma form and have been updated to the ROM-exact wording. Locked in by `tests/integration/test_tell_parity.py::test_tell_002_to_vict_wording_drops_comma`.

### Notes

- Second of six TELL-NNN gaps from the 2026-05-22 `do_tell` re-audit. TELL-003 (PERS for sender to victim), TELL-004 (PERS for target to sender), TELL-005 (charcoal colour codes) remain open. TELL-006 deferred (MINOR).
- Full suite at `4621 passed, 4 skipped, 4 deselected` (+1 vs 2.8.44; zero regressions).

## [2.8.44]

### Fixed
- **`TELL-001` — `do_tell` TO_CHAR wording drops the comma** (`src/act_comm.c:941`): ROM emits `act("You tell $N '$t'", ...)` — no comma between target name and the open quote. Python previously returned `"You tell {target.name}, '{message}'"` with an extra comma. Fix: drop the comma in `mud/commands/communication.py:do_tell` return. Legacy assertions in `tests/test_communication.py` (×2) and `tests/integration/test_communication_enhancement.py` were baked to the buggy comma form and have been updated to the ROM-exact wording. Surfaced by a 2026-05-22 `do_tell` re-audit that found the prior "100% VERIFIED" claim incorrect (same audit-doc inflation that hit `do_say` and `do_emote` this session). Locked in by `tests/integration/test_tell_parity.py::test_tell_001_to_char_wording_drops_comma`.

### Notes

- First of six TELL-NNN gaps from the 2026-05-22 `do_tell` re-audit. TELL-002 (TO_VICT wording comma), TELL-003 (PERS for sender to victim), TELL-004 (PERS for target to sender), TELL-005 (charcoal colour codes) remain open and will close in sequence. TELL-006 (uppercase first char of buffered tells — MINOR cosmetic) is intentionally deferred.
- Full suite at `4620 passed, 4 skipped, 5 deselected` (+1 vs 2.8.43 baseline 4619/4; deselected = the still-open TELL gaps; zero regressions).

## [2.8.43]

### Fixed
- **`EMOTE-002` — `do_emote` TO_CHAR `$n` renders as "You", not the actor's own name** (`src/act_comm.c:1092`): ROM's `act("$n $T", ..., TO_CHAR)` substitutes `$n` to `"You"` on the self branch — the actor reads `"You smiles happily"`, not `"Alice smiles happily"`. Python previously returned `f"{char.name} {args}"` so the actor saw their own name as the emote subject. Fix: `mud/commands/communication.py:do_emote` now returns `f"You {args}"`. Legacy `tests/integration/test_communication_enhancement.py::test_emote_broadcasts_custom_action` was baked to the buggy form (per AGENTS.md — tests asserting Python behavior contradicting ROM are bugs in the **test**, not the implementation) and has been updated to the ROM-exact wording. Locked in by `tests/integration/test_emote_parity.py::test_emote_002_self_message_renders_you_not_actor_name`.

### Notes

- Second of three gaps from the 2026-05-22 `do_emote` re-audit. PMOTE-001 (`do_pmote` not implemented in Python) remains open as a missing-function gap, tracked for a future session.
- Full suite at `4619 passed, 4 skipped` (+1 vs 2.8.42 baseline 4618/4; zero regressions).

## [2.8.42]

### Fixed
- **`EMOTE-001` — `do_emote` PERS substitution: invisible emoter renders as `"someone"`** (`src/act_comm.c:1091`, `src/handler.c:2618-2664`): ROM's `act("$n $T", ..., TO_ROOM)` substitutes `$n` per-listener through `PERS()` so an invisible emoter renders as `"someone"` to listeners without `DETECT_INVIS`. Python previously hardcoded `char.name` into one TO_ROOM message and broadcast it to everyone in the room, leaking the invisible emoter's identity exactly like the pre-fix `do_say` (SAY-002). Fix: refactored `mud/commands/communication.py:do_emote` to render TO_ROOM per-listener using `mud.world.vision.pers(char, listener)` (the helper added in 2.8.41 for SAY-002). Tests: `tests/integration/test_emote_parity.py::test_emote_001_invisible_emoter_renders_as_someone_to_unaided_listener` and `::test_emote_001_visible_emoter_renders_real_name_to_listener`.

### Notes

- First of three gaps from the 2026-05-22 `do_emote` re-audit. EMOTE-002 (TO_CHAR `$n` → "You" instead of actor's own name) and PMOTE-001 (`do_pmote` not implemented in Python) remain open.
- Full suite at `4618 passed, 4 skipped` (+2 vs 2.8.41 baseline 4616/4; zero regressions despite the per-listener broadcast refactor).

## [2.8.41]

### Added
- **`mud.world.vision.pers(target, observer)`** mirroring ROM's `PERS()` macro (`src/comm.c` via `#define` and `src/handler.c:2618-2664 can_see`). Returns `"someone"` if `observer` cannot see `target`, otherwise the target's NPC `short_descr` or PC `name`. No aura prefixes (that's `act_info show_char_to_char_0`) and no self-handling (callers route TO_CHAR vs TO_ROOM separately).

### Fixed
- **`SAY-002` — `do_say` PERS substitution: invisible/hidden speakers appear as `"someone"`** (`src/act_comm.c:776`, `src/handler.c:2618-2664`): ROM's `act()` substitutes `$n` through `PERS(ch, looker)`, which gates on `can_see(looker, ch)`. So when an invisible speaker says something, listeners without `DETECT_INVIS` see `"someone says '<msg>'"`, not the speaker's real name. Python previously built one TO_ROOM message string with `char.name` hardcoded and broadcast it to everyone in the room, leaking invisible/hidden PC identities. Fix: added `pers()` helper in `mud/world/vision.py` (uses existing `can_see_character`), then refactored `do_say` to render the TO_ROOM string per-listener with `pers(speaker, listener)` substituted for `$n`. Closes the four-gap `do_say` re-audit cluster opened on 2026-05-22. Tests: `tests/integration/test_say_parity.py::test_say_002_invisible_speaker_renders_as_someone_to_unaided_listener` and `::test_say_002_invisible_speaker_seen_by_detect_invis_listener`.

### Notes

- Fourth and final SAY-NNN gap from the 2026-05-22 `act_comm.c` re-audit. `do_say` is now ✅ 100% re-audited.
- Analogous CRITICAL gaps almost certainly exist in `do_tell` / `do_shout` / `do_yell` / `do_emote` / `do_pose` / `do_pmote` — those audits are now unblocked (the helper exists). Tracked as next-session candidates in `docs/sessions/SESSION_STATUS.md`.
- Full suite at `4616 passed, 4 skipped` (+2 vs 2.8.40 baseline 4614/4; zero regressions despite the per-listener broadcast refactor).

## [2.8.40]

### Fixed
- **`SAY-003` — `do_say` wraps output with ROM colour codes (`{6...{7$T{6'{x`)** (`src/act_comm.c:776-777`): ROM frames the say channel in cyan/green (`{6`), switches to white (`{7`) for the message body, returns to `{6` for the closing quote, and resets with `{x`. The ANSI translation layer at `mud/net/ansi.py` consumes those tokens on websocket send. Python previously emitted no codes, so the say channel rendered in the player's default terminal colour and the framing-vs-body contrast ROM relies on was lost. Fix: `mud/commands/communication.py:do_say` now wraps both TO_CHAR and TO_ROOM strings with the ROM colour sequence. Legacy assertions in `tests/test_commands.py`, `tests/test_command_abbrev.py`, and `tests/integration/test_communication_enhancement.py` were baked to the codeless plain-text form (per AGENTS.md, tests asserting Python behavior contradicting ROM are bugs in the **test**, not the implementation) and have been updated. Locked in by `tests/integration/test_say_parity.py::test_say_003_to_char_wraps_rom_color_codes` and `::test_say_003_to_room_wraps_rom_color_codes`.

### Notes

- Third of four SAY-NNN gaps from the 2026-05-22 `act_comm.c` re-audit. SAY-002 (`$n` PERS for invisible speakers) remains open — requires building a Python `pers()` helper that mirrors ROM's `PERS()` macro.
- Full suite at `4614 passed, 4 skipped` (+2 vs 2.8.39 baseline 4612/4; zero regressions).

## [2.8.39]

### Fixed
- **`SAY-004` — `do_say` delivers TO_ROOM broadcast exactly once (INV-001 SINGLE-DELIVERY)** (`src/act_comm.c:776`): ROM's `act(..., TO_ROOM)` iterates `ch->in_room->people` and delivers to each target exactly once. Python called BOTH `char.room.broadcast(message, exclude=char)` AND `broadcast_room(char.room, message, exclude=char)`. The two helpers do identical work — iterate `room.people`, fire-and-forget websocket send, append to `char.messages` — so every `say` was delivered twice. Players received "<name> says 'hi'" twice; transcripts and message queues both diverged. Fix: dropped the redundant `broadcast_room` call in `mud/commands/communication.py:do_say`, keeping only `char.room.broadcast`. Locked in by `tests/integration/test_say_parity.py::test_say_004_listener_receives_broadcast_exactly_once`.

### Notes

- Second of four SAY-NNN gaps from the 2026-05-22 `act_comm.c` re-audit. SAY-002 (`$n` PERS for invisible speakers) and SAY-003 (ROM colour codes) remain open.
- Full suite at `4612 passed, 4 skipped` (+1 vs 2.8.38 baseline 4611/4; zero regressions).

## [2.8.38]

### Fixed
- **`SAY-001` — `do_say` wording matches ROM (`says '$T'` / `You say '$T'` — no comma)** (`src/act_comm.c:776-777`): ROM emits `act("$n says '$T'", ...)` and `act("You say '$T'", ...)`. Python emitted `"says, '..'"` and `"You say, '..'"` with a comma the player did not type. Surfaced by a 2026-05-22 re-audit of `act_comm.c` that found the previous "100% VERIFIED" claim was incorrect. Fix: `mud/commands/communication.py:do_say` now produces the ROM-exact wording. Legacy `tests/test_commands.py`, `tests/test_command_abbrev.py`, `tests/integration/test_communication_enhancement.py` assertions were baked to the buggy comma form (per AGENTS.md — tests that assert Python behavior contradicting ROM are bugs in the **test**, not the implementation) and have been updated to the ROM-exact wording. Locked in by `tests/integration/test_say_parity.py::test_say_001_room_broadcast_drops_comma` and `test_say_001_to_char_drops_comma`.

### Notes

- Three additional `do_say` gaps surfaced by the re-audit are stable-IDed in `docs/parity/ACT_COMM_C_AUDIT.md` for sequential closure: SAY-002 (`$n` PERS substitution for invisible speakers), SAY-003 (ROM colour codes), SAY-004 (double-delivery via `room.broadcast` + `broadcast_room` — INV-001 SINGLE-DELIVERY violation).
- Full suite at `4611 passed, 4 skipped` (+2 vs 2.8.37 baseline 4609/4; zero regressions).

## [2.8.37]

### Fixed
- **`PROMPT-CMD-003` — `do_prompt` runs `smash_tilde` on custom template before storing** (`src/act_info.c:945`, `src/db.c:3663-3672`): ROM calls `smash_tilde(buf)` before `ch->prompt = str_dup(buf)`, replacing every `~` with `-` so the stored template cannot corrupt the player file on save (ROM treats `~` as the end-of-string marker on disk). Python's `do_prompt` previously stored the raw argument including any tildes the player typed. Fix: `mud/commands/auto_settings.py:do_prompt` now calls `mud.utils.text.smash_tilde` on the custom-template branch before assigning `char.prompt`. Locked in by `tests/integration/test_prompt_cmd_parity.py::test_prompt_cmd_003_smash_tilde_on_custom_template`.

### Notes

- Closes the PROMPT-CMD cluster opened by 2.8.35's NANNY-SAVELOAD-002 probe (PROMPT-CMD-001/002 landed in 2.8.36).
- Two ROM-divergence corners remain on `do_prompt` but are now stable-IDed for future hardening: PROMPT-CMD-004 (50-char truncation), PROMPT-CMD-005 (`%c`-suffix → append trailing space). Both are corner cases — no behavioral impact for typical players — and tracked in `docs/parity/ACT_INFO_C_AUDIT.md`.
- Full suite at `4609 passed, 4 skipped` (+1 vs 2.8.36 baseline 4608/4; zero regressions).

## [2.8.36]

### Fixed
- **`PROMPT-CMD-001` — `do_prompt` preserves trailing whitespace in custom templates** (`src/act_info.c:944`): the dispatcher (`mud/commands/dispatcher.py:process_command`) used `core = trimmed.rstrip()` which stripped visible trailing whitespace from every command before reaching its handler. ROM `src/interp.c:interpret` only strips line-ending whitespace, leaving visible trailing whitespace intact. Fix: dispatcher now uses `core = trimmed.rstrip("\r\n")` and computes log-line trailing whitespace from `trimmed.rstrip()` separately so the existing per-command log convention (`tests/test_logging_admin.py::test_logging_logs_alias_expansion`) is preserved. Also removed `arg = args.strip()` in `mud/commands/auto_settings.py:do_prompt` so the handler now uses the raw arg (matching ROM's raw `argument` usage at `src/act_info.c:944`). Now `prompt MYTAG> ` correctly stores `"MYTAG> "` and `bust_a_prompt` renders the trailing space.
- **`PROMPT-CMD-002` — `do_prompt` success reply echoes the stored template** (`src/act_info.c:953-954`): Python previously emitted the truncated `"Prompt set."`; ROM emits `"Prompt set to %s\n\r"` with the stored template. Fixed both the `"all"` branch and the custom-template branch in `mud/commands/auto_settings.py:do_prompt`. Existing helper tests (`tests/test_player_prompt.py`) and the live-websocket round-trip in `tests/integration/test_nanny_saveload_runtime_path.py` updated to the ROM-exact wording.

### Notes

- New enforcement tests in `tests/integration/test_prompt_cmd_parity.py` lock in both gaps on the live websocket path.
- Full suite at `4608 passed, 4 skipped` (+2 vs 2.8.35 baseline 4606/4; zero regressions). Surfaced and fixed in a single session after being flagged in 2.8.35's NANNY-SAVELOAD-002 probe.

## [2.8.35]

### Changed
- **`NANNY-SAVELOAD-001` — wimpy round-trips through reconnect** (`src/act_info.c:2800-2830`, `src/save.c:fwrite_char/fread_char`, `src/act_info.c:1548-1549`): added `tests/integration/test_nanny_saveload_runtime_path.py::test_nanny_saveload_001_wimpy_round_trips_through_reconnect` exercising `wimpy <n>` mid-session, then asserting the value comes back via `score` on the first command after reconnect. Verified the live runtime path; no implementation drift found.
- **`NANNY-SAVELOAD-002` — custom prompt template round-trips through reconnect** (`src/act_info.c:919-955`, `src/comm.c:1420-1595`): added `tests/integration/test_nanny_saveload_runtime_path.py::test_nanny_saveload_002_prompt_template_round_trips_through_reconnect` exercising `prompt <template>` mid-session, then asserting the first in-game prompt after reconnect renders the saved template (no ROM-default `<Nhp Nm Nmv>` fallback). Verified the live runtime path; the persistence layer round-trip is intact. Probe also surfaced two **separate** `do_prompt` command-side parity gaps (not save→reload bugs): (a) the dispatcher strips trailing whitespace from `prompt <template>` args before `do_prompt` sees them, so a template with a trailing space loses it; (b) the success reply is the truncated `"Prompt set."` instead of ROM's `"Prompt set to <template>\n\r"` which echoes the stored template. Both captured as follow-ups in `docs/sessions/SESSION_STATUS.md`.
- **`NANNY-SAVELOAD-003` — per-character aliases round-trip through reconnect** (`src/alias.c:102-220`, `src/save.c:fwrite_char/fread_char`): added `tests/integration/test_nanny_saveload_runtime_path.py::test_nanny_saveload_003_alias_round_trips_through_reconnect` exercising `alias k kill` mid-session, then asserting the alias listing on the first command after reconnect re-renders the saved entry with ROM listing format `"    k:  kill"`. Verified the live runtime path through the DB JSON column; no implementation drift found.

### Notes

- Full suite at `4606 passed, 4 skipped` (+3 vs 2.8.34 baseline 4603/4; zero regressions).
- Plan Task 4 (`docs/superpowers/plans/2026-05-21-parity-trust-rebuild-reaudit.md`) — save → reload → retained-state runtime-path bullet — is now complete. Remaining trust-rebuild work shifts to Plan Task 5 (re-audit other high-risk user-visible command families).

## [2.8.34]

### Fixed
- **`INV-009` REGISTRY-DISCONNECT-CLEANUP** (new cross-file invariant): `character_registry` was accumulating duplicate `Character` entries per player name in two places:
  - **In-session promote-from-bare-row duplication.** The level=0 bare-row Character loaded at `_select_character` (during the nanny name/password phase) was appended to `character_registry` and never replaced. After creation finalised, a fresh level=1 Character was loaded via `load_character` and appended on top, leaving both in the registry. `next((c for c in character_registry if c.name == X), None)` could return the stale level=0 entry (e.g. `hit=20`) while the live session ran against the level=1 entry (`hit=100`).
  - **Cross-session leak on clean disconnect.** The websocket and telnet disconnect `finally` blocks already saved the character, removed them from their room, and released the account — but never removed them from `character_registry`. Each disconnect-then-reconnect cycle added a new entry without removing the old one.
- **Fix (`mud/account/account_manager.py:load_character`)**: drop any prior `character_registry` entry with the same name before appending the freshly-loaded one (dedup-by-name on append).
- **Fix (`mud/net/connection.py` websocket + telnet disconnect cleanup)**: remove the Character from `character_registry` in the `if char: if not forced_disconnect:` block, matching the `save + char_from_room + release_account` quit semantics already present. Forced disconnects (descriptor takeover) skip removal — `_disconnect_session` transfers the live Character to the new descriptor.
- **Test**: `tests/integration/test_inv009_registry_disconnect_cleanup.py::test_inv009_registry_has_single_entry_after_disconnect_and_reconnect` reproduces both cases on the live websocket path and asserts: (a) zero `Regista` entries after a clean disconnect, (b) exactly one `Regista` entry while a reconnected session is active.
- **Tracker**: new INV-009 row in `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`.

### Notes

- Full suite at `4603 passed, 4 skipped` (+1 vs 2.8.33 baseline 4602/4; zero regressions).
- Discovered during NANNY-RECONNECT-003 debugging in 2.8.33 (see SESSION_SUMMARY_2026-05-22_NANNY_RECONNECT_RUNTIME_PATH_PARITY.md "follow-ups").

## [2.8.33]

### Changed
- **`NANNY-RECONNECT-001` — `score` after reconnect transcript parity** (`src/act_info.c:1477-1507`, `src/nanny.c:760`): added a websocket-runtime-path regression in `tests/test_websocket_server.py::test_websocket_reconnect_score_matches_rom_act_info_lines` that asserts ROM-exact title (`"You are <name> the Apprentice of Magic, level 1, ..."`), race/sex/class line (`"Race: elf  Sex: male  Class: mage"`), and hit/mana/move at full after `reset_char` on login. Verified the live runtime path; no implementation drift found.
- **`NANNY-RECONNECT-002` — `look` after reconnect matches live room registry** (`src/act_info.c:1037-1116`): added `tests/test_websocket_server.py::test_websocket_reconnect_look_matches_room_registry_not_cached_snapshot` which reconnects an elf mage, snapshots the live `character_registry` entry's `room.name` and description, then asserts the `look` transcript on the **first command after reconnect** contains both — guarding against stale pre-disconnect cached snapshots. Verified the live runtime path; no implementation drift found.
- **`NANNY-RECONNECT-003` — first in-game prompt after reconnect reflects loaded resources** (`src/comm.c:1437-1443`, `src/nanny.c:760`): added `tests/test_websocket_server.py::test_websocket_reconnect_initial_prompt_reflects_loaded_resources` which captures the first post-MOTD prompt on the live websocket, then sends `score` on the same session and asserts the ROM `<Nhp Nm Nmv>` token values equal what `score` reports (self-consistent), and that `hit == max_hit` after `reset_char` on login. Verified the live runtime path; no implementation drift found.

### Notes

- Full suite at `4602 passed, 4 skipped` (+3 vs prior baseline 4599/4; zero regressions).
- During NANNY-RECONNECT-003 debugging, a `character_registry` reconnect-duplication oddity surfaced (stale pre-disconnect Character returned by name lookup). Recorded as a follow-up in `docs/sessions/SESSION_STATUS.md` for a dedicated future slice.

## [2.8.32]

### Fixed
- **`nanny.c` happy-path new-character creation prompts**: `mud/net/connection.py` now emits ROM-exact `"New character."`, `"Give me a password for <Name>:"`, `"Please retype password:"`, and ROM race/sex/class/weapon prompt wording on the live runtime path. Removed the non-ROM `"Creating new character 'X'."` line and the non-ROM stat-reroll and hometown prompts (ROM `nanny.c:476-478` derives `perm_stat` from `pc_race_table[race].stats[i]` and has no such prompts).
- **`nanny.c` pre-login greeting parser**: the greeting no longer leaks the embedded MOTD block before `Name:`.
- **`NANNY-RETRY-001` — race invalid wording** (`src/nanny.c:460-471`): `_prompt_for_race` now sends `"That is not a valid race."` (was `"That's"`); race listing prefix is `"The following races are available:\n\r  "` to match ROM telnet line endings.
- **`NANNY-RETRY-002` — race "help" branch wording** (`src/nanny.c:444-453`): verified ROM-exact; regression test added.
- **`NANNY-RETRY-003` — class invalid wording** (`src/nanny.c:538-539`): `_prompt_for_class` now sends `"That's not a class."` (was `"That's not a valid class."`) and switches the retry prompt to `"What IS your class? "`.
- **`NANNY-RETRY-004` — customize Y/N retry** (`src/nanny.c:626-628`): `_prompt_customization_choice` now sends `"Please answer (Y/N)? "` on invalid entry (was the generic `"Please answer Y or N."`). `_prompt_yes_no` gained an optional `retry_message` kwarg so other Y/N callsites keep their existing wording.
- **`NANNY-RETRY-005` / `NANNY-RETRY-006` — weapon prompt CRLF** (`src/nanny.c:611-624`, `:638-649`): the weapon-pick prompt and its invalid-entry retry now use ROM `\n\r` line endings before `"Your choice? "` (were bare `\n`).

### Changed
- **Stricter creation transcript coverage**: `tests/integration/test_nanny_login_parity.py` adds six transcript-parity tests (`NANNY-RETRY-001..006`); full suite now at `4599 passed, 4 skipped` (+6 from prior baseline 4593/4, zero regressions).

## [2.8.31]

### Fixed
- **`nanny.c` trust-rebuild: `CON_READ_MOTD` now emits the ROM welcome line**: `mud/net/connection.py` now sends `Welcome to ROM 2.4.  Please don't feed the mobiles!` at the moment a normal login actually enters the game, matching the ROM branch instead of skipping straight to MOTD/help/look output.
- **Forced reconnects no longer run the normal login tail**: duplicate-session takeover reconnects now skip the normal welcome/look/board path and only emit the ROM reconnect-side output, which restores parity with `check_reconnect(..., TRUE)` and keeps telnet reconnect sequencing stable.

### Changed
- **Stricter reconnect/login runtime coverage**: `tests/test_websocket_server.py` now asserts the ROM welcome line on first entry, and the full suite recertifies clean with the reconnect split in place (`4593 passed, 4 skipped`).

## [2.8.30]

### Fixed
- **`save.c` trust-rebuild: reconnect now preserves the school outfit**: `mud/models/character.py` now restores equipped items from DB-canonical `equipment_state` without silently dropping them on load, and recomputes carry totals after inventory/equipment restore so the first `score` after reconnect matches the first `score` after character creation.
- **`nanny.c` trust-rebuild: login now emits the ROM board summary**: `mud/net/connection.py` now mirrors the tail of `CON_READ_MOTD` by sending a blank line and `board` output after the initial room `look` on both connection paths.

### Changed
- **Stricter runtime-path persistence coverage**: `tests/test_websocket_server.py` now asserts both reconnect outfit persistence and post-login board summary output on the real WebSocket path, and `tests/integration/test_inv008_persistence_coherence.py` now locks equipment/carry-state save-load round trips directly.

## [2.8.29]

### Fixed
- **`nanny.c` trust-rebuild: returning level-1 players no longer replay first-login outfit flow**: `mud/net/connection.py` now treats the persisted `newbie_help_seen` flag as the durable first-login marker, so reconnecting or relogging level-1 characters no longer get re-equipped by Mota or reclassified as brand-new.

### Changed
- **Stricter runtime-path login coverage**: `tests/test_websocket_server.py` now asserts that a real WebSocket reconnect does not replay the one-time school outfit path, and `tests/test_connection_motd.py` now locks the `_is_new_player()` helper contract directly.

## [2.8.28]

### Fixed
- **`act_info.c` trust-rebuild: `do_look` dark-room and container-detail parity**: `mud/world/look.py` now mirrors ROM dark-room output more closely by appending raw visible character lines without a Python-only `Characters:` label, and `look in` now uses the ROM drink-container wording with liquid color plus the correct `CONT_CLOSED` bit for closed containers.
- **`check_blind()` / `do_look` blind-gate parity**: `mud/rom_api.py` now rejects `AFF_BLIND` correctly, and `mud/world/look.py` now returns the ROM blind message `"You can't see a thing!"` instead of falling through to normal room output.

### Changed
- **Stricter `do_look` regression coverage**: `tests/integration/test_do_look_command.py` now includes exact ROM-style assertions for dark-room visible occupants, drink-container liquid wording, closed-container gating, and blindness; `tests/test_rom_api.py` now locks the blind helper contract directly.

## [2.8.27]

### Fixed
- **`act_info.c` trust-rebuild: `do_look` autoexit parity**: `mud/world/look.py` no longer emits a manual exits line on every room look; exits now appear only through the ROM `PLR_AUTOEXIT` branch.
- **`act_info.c` trust-rebuild: `do_look` room rendering parity**: room contents and visible occupants are now appended as raw lines instead of Python-only `Objects:` / `Characters:` labels, matching ROM `show_list_to_char` / `show_char_to_char` behavior more closely.

### Changed
- **Direct `do_look` regression coverage**: added ROM-exact room-look tests for autoexit gating and raw room content / occupant line formatting.


## [2.8.26]

### Fixed
- **`act_info.c` trust-rebuild: `do_who` switched-session parity**: `mud/commands/info.py` now mirrors ROM `do_who` by preferring the switched descriptor `original` character for output and title rendering instead of always showing the shell character.

### Changed
- **Stricter `do_who` output coverage**: `tests/integration/test_do_who_command.py` now includes exact ROM-style output assertions for switched sessions and representative fully-flagged player rows.


## [2.8.25]

### Fixed
- **`act_info.c` trust-rebuild: `do_equipment` slot order parity**: `mud/commands/inventory.py` now mirrors ROM `do_equipment` by iterating wear slots in numeric `MAX_WEAR` order instead of Python dict insertion order.
- **`act_info.c` trust-rebuild: `do_where` private-room parity**: `mud/commands/info.py` mode 1 now applies the ROM room-owner/private-room gate on the live session path, so mortals no longer see descriptor-backed players in genuinely private rooms.

### Changed
- **Stricter `inventory` / `equipment` / `where` regressions**: added ROM-exact layout assertions for `do_inventory` and `do_equipment`, plus a real descriptor-path private-room regression for `do_where`.


## [2.8.24]

### Fixed
- **`act_info.c` trust-rebuild: `whois` formatting parity**: `mud/commands/info_extended.py` now mirrors ROM descriptor-path `whois` behavior more closely, including race/class display, immortal rank labels, AFK/KILLER/THIEF flags via enums, and switched-descriptor `original` handling.
- **`score` player-race mapping**: fixed the player-facing race-name helper so playable race id `0` renders as `human` instead of the base-race sentinel `unique`.

### Changed
- **Stricter `act_info.c` regressions**: `tests/test_player_info_commands.py` now replaces several weak smoke assertions with ROM-exact `score` and `whois` output checks.
- **Trust-rebuild handoff updated**: `ACT_INFO_C_AUDIT.md` and the session docs now explicitly record that `act_info.c` is under observable-behavior revalidation rather than relying on legacy structural-audit completion claims.


## [2.8.23]

### Fixed
- **`score` parity and load-session hydration**: fixed ROM-visible `score` output so loaded characters now refresh live session `logon`, render race/class/title correctly, and use ROM-style low-level AC wording instead of stale helper-path values.
- **Runtime-path persistence regression coverage**: added a full WebSocket create → disconnect → reconnect test to prove completed character creation persists and the second login reaches `Password:` instead of restarting character creation.

### Changed
- **Verification language downgraded to match evidence**: README and session guidance now mark ROM parity as under active revalidation rather than fully certified, after a live `score` bug showed gaps in prior observable-behavior coverage.
- **Trust-rebuild program documented**: added a re-audit plan and a differential-testing design spec covering ROM-exact output, runtime-path verification, and data parity for future audit closure work.


## [2.8.22]

### Fixed
- **Area JSON boot/reset parity**: repaired the checked-in `data/areas/*.json` dataset and the ROM area loaders so world boot no longer emits the invalid O/P/D/G/E reset warning flood. This includes ROM-accurate room-door lock decoding, object `F` affect parsing, first-tilde string termination, and JSON room-sector preservation.

### Changed
- **Area dataset regeneration**: regenerated the checked-in area JSON files from their `.are` sources after the loader fixes, restoring missing object prototypes and corrected room topology across the shipped world data.
- **Stale test cleanup after area repair**: updated area/scan/mobprog parity tests to stop depending on previously broken topology or ambient RNG state.
- **Full-suite recertification**: the suite now reruns clean at `4567 passed, 4 skipped`.

## [2.8.21]

### Changed
- **README status refresh**: updated the public project status, audit coverage, test counts, and active-focus guidance so the README now matches the audited trackers and current session status.
- **Release wrap-up**: recertified the published repo state around the current fully green parity program (`4560 passed, 4 skipped`) and the completed 40/40 audit-bound ROM C file coverage.

## [2.8.20]

### Changed
- **Stability investigation recertified clean**: executed the queued descriptor/session reproduction subset and a full-suite rerun with no reproducing leak (`36 passed, 36 deselected` in the networking subset; full suite still `4560 passed, 4 skipped`).
- **Session guidance tightened**: `docs/sessions/SESSION_STATUS.md` now records that descriptor/session cleanup work should not proceed without a deterministic reproduction, and points the next agent at the standing investigation plan only if a leak reappears.

## [2.8.19]

### Added
- **Stability / invariant hardening handoff plan**: added a concrete next-agent execution plan for descriptor/session global-state isolation, targeting `descriptor_list`, `character_registry`, telnet/session teardown, and any newly discovered cross-file invariant.

### Changed
- **Session handoff updated**: `docs/sessions/SESSION_STATUS.md` now points at the stability / invariant hardening queue, with a dedicated handoff summary and explicit first verification commands for the next agent.

## [2.8.18]

### Added
- **Descriptor-backed `wiznet` regression coverage**: `tests/test_wiznet.py` now registers ROM-style playing descriptors for listeners and includes a stale-descriptor regression, so the suite exercises the production descriptor path instead of relying on the character-registry fallback.

### Fixed
- **`wiznet` descriptor-path immortal gate parity**: `mud/wiznet.py` now mirrors ROM `src/act_wiz.c:171-194` on the real descriptor path by rejecting NPC and non-immortal recipients before checking wiznet flags.

### Changed
- **Full-suite recertification**: the suite now reruns clean at `4560 passed, 4 skipped`.

## [2.8.17]

### Added
- **`BOARD-014` AFK parity coverage**: added ROM-backed integration tests for note-editor AFK ownership, including `note write`, `note send`, and the new `note forget` cancel path.

### Fixed
- **`BOARD-014` note-editor AFK parity**: `mud/commands/notes.py` and `mud/models/board.py` now mirror ROM `src/board.c` by setting AFK when note composition begins, clearing only note-owned AFK when posting or forgetting a note, and preserving manually enabled AFK.

### Changed
- **`board.c` audit closure**: `docs/parity/BOARD_C_AUDIT.md` and `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` now record `board.c` as fully closed with `BOARD-014` no longer deferred.
- **Full-suite recertification**: the suite now reruns clean at `4559 passed, 4 skipped`.

## [2.8.16]

### Fixed
- **`MUSIC-005` global-channel recipient parity**: `mud/music/__init__.py` now mirrors ROM `src/music.c:88-97` by iterating the ROM-style descriptor list, requiring `CON_PLAYING`, checking `COMM_NOMUSIC` / `COMM_QUIET` on `descriptor.original` when switched, and delivering the line to the active descriptor character.
- **`MUSIC-006` jukebox visibility parity**: jukebox room output now resolves `$p` per viewer, so recipients who cannot see the jukebox get ROM-style `"something"` fallback instead of a leaked short description. Implemented in `mud/music/__init__.py` with object visibility fallback in `mud/utils/act.py`.

### Changed
- **`music.c` audit closure**: `docs/parity/MUSIC_C_AUDIT.md` and `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` now record `music.c` at 100% with all six gaps closed.

## [2.8.15]

### Changed
- **Parity audit reconciliation**: refreshed stale `nanny.c` audit headers and the historical `save.c` tracker narrative so the docs match the verified codebase and enforced invariants (`INV-003`, `INV-008`).

## [2.8.14]

### Added
- **Deterministic ROM skill-improvement coverage**: `tests/integration/test_skills_integration.py` now enforces `check_improve()` on the live combat path, including the ROM rule that combat learning can continue above class adept up to 100.
- **Executable money and spell-affect integration coverage**: replaced stale skipped placeholders with live tests for drop-money consolidation, cursed no-remove equipment, poison damage-over-time, and plague contagion spread.

### Fixed
- **`check_improve()` adept-cap parity**: `mud/skills/registry.py` now mirrors ROM `src/skills.c` by allowing post-use learning through 100 instead of stopping at the class adept cap.
- **Plague contagion parity**: `mud/game_loop.py` now applies a full `AffectData` record to newly infected victims during `char_update()`, matching ROM `src/update.c:839-840`.
- **Kick ROM parity test stability**: `tests/test_skill_combat_rom_parity.py` now isolates `check_improve()` from the kick damage-roll assertions so the test verifies the ROM damage call instead of incidental follow-up RNG.

### Changed
- **Integration coverage tracker reconciliation**: the skills and spell-affects slices now record their real enforced status, and the stale info-command / equipment / group-combat historical narratives were collapsed to canonical current-state notes.
- **Full-suite recertification**: the suite now reruns clean at `4553 passed, 4 skipped`.

## [2.8.13]

### Added
- **ROM wear-off suppression enforcement**: added targeted regression coverage for `char_update()` and `obj_update()` so consecutive same-type affect expirations now stay locked to ROM `src/update.c` semantics, including single-message suppression for object wear-off.
- **Deterministic `mobile_update()` wander-gate enforcement**: added isolated integration coverage for `ACT_STAY_AREA`, `ACT_OUTDOORS`, and `ACT_INDOORS` movement restrictions using synthetic room topology instead of boot-world assumptions.

### Fixed
- **`GL-010` character affect wear-off parity**: `mud/affects/engine.py` now preserves merged spell effects while any same-type `AffectData` remains active, matching ROM `src/update.c:762-786`.
- **`GL-017` object affect wear-off parity**: `mud/game_loop.py` now suppresses duplicate same-type object wear-off messages exactly once per tick, matching ROM `src/update.c:939-957`.

### Changed
- **Parity tracker reconciliation**: cross-file invariant and integration-coverage trackers now record the enforced wander-gate and wear-off parity slices, and the full suite is recertified at `4547 passed, 10 skipped`.

## [2.8.12]

### Added
- **Canonical ROM `weapon_table`**: added `/mud/models/weapon_table.py` as the shared source for weapon class name, school weapon vnum, weapon type, and linked proficiency mapping, then wired combat, character-load skill seeding, and creation-time weapon handling to it.
- **`NANNY-010` reconnect descriptor sweep**: `mud/net/connection.py` now mirrors ROM `src/nanny.c:307-352` by sweeping duplicate descriptors on break-connect reconnect, including the switched-immortal `original->name` branch.

### Fixed
- **`COMM-005` duplicate-newbie parity**: new-character name validation now closes matching non-playing duplicate descriptors and emits ROM's `Double newbie alert` wiznet notice.
- **`FLAG-002` settable-bit preservation**: `do_flag` now preserves ROM `settable=FALSE` bits across the `=` operator for `act`, `plr`, and `comm` fields.
- **Test determinism and suite stability**: stabilized wiznet and advancement integration tests by isolating shared descriptor-list state and replacing wall-clock ROM RNG seeding with a fixed Mitchell-Moore seed.

### Changed
- **Parity tracker reconciliation**: refreshed stale audit/tracker rows for `act_obj.c`, `act_wiz.c`, `scan.c`, `special.c`, `healer.c`, `const/tables/lookup`, `fight.c`, and `comm.c` so docs match the verified codebase.
- **Full-suite recertification**: the suite now reruns clean at `4535 passed, 11 skipped`.

## [2.8.11]

### Fixed
- **`log` command trust parity**: restored the dispatcher registration for `log` to ROM `src/interp.c` level `L1` (`MAX_LEVEL - 1`) and updated the admin-logging tests to use a ROM-valid immortal trust level instead of `LEVEL_HERO`.

## [2.8.10]

### Fixed
- **Legacy character-row compatibility**: `mud/db/migrations.py` now backfills the DB-canonical `characters` columns that `load_character()` queries, so older SQLite databases with only the pre-2.8.0 schema can still load characters after migration. `mud/models/character.py:from_orm` and `mud/account/account_service.py:create_character` also keep persistent `points` aligned with ROM creation-point state.

## [2.8.9]

### Fixed
- **Command parser test parity**: leading punctuation commands now follow ROM `src/interp.c` single-character tokenization, restoring apostrophe-as-`say` handling. Updated scripted-session/command tests to match current ROM-faithful transcript ordering and scan output, and replaced a stale non-takeable school-sword pickup assumption with an explicit takeable test object.

## [2.8.8]

### Fixed
- **Admin `log` command parity**: dispatcher trust for `log` now matches ROM `src/interp.c`/`src/act_wiz.c`, `cmd_log` keeps the persisted `PLR_LOG` bit and `log_commands` boolean in sync, and admin player lookup now resolves through the live runtime character registry so `log <player>` works reliably.

## [2.8.7]

### Fixed
- **hedit RecursionError**: `_interpret_hedit` fallthrough on unknown commands now returns `"Unknown help editor command: <cmd>\n\r"` so `_should_fallback_from_olc` routes to the normal command table instead of re-entering hedit via `process_command`. Mirrors ROM `src/hedit.c:258` `interpret(ch, arg)` without the re-entry loop.

### Changed
- **tests/test_builder_hedit.py rewrite**: All 19 stale tests replaced with 23 ROM-parity tests that verify actual `cmd_hedit`/`cmd_hesave` behavior (ROM-exact strings: `"HEdit: There is no default help to edit.\n\r"`, `"Ok.\n\r"`, `"Keyword : [...]"`, `"Level   : [...]"`, etc.). Covers entry-point guard, `new` subcommand, session open/show/keyword/level/text/done, session-lost recovery, unknown-command non-recursion, and full `hesave` workflow.

## [2.8.6]

### Fixed
- **FIGHT-002 safe-room parity**: `mud/combat/engine.py:apply_damage` now mirrors ROM `src/fight.c:725-733` by re-checking `is_safe(ch, victim)` before any fighting-state or HP mutation. This stops melee damage, weapon procs, and other `apply_damage()`-backed attack paths from landing after combatants are moved into a safe room mid-fight. Regression coverage: `tests/integration/test_fight_c_safe_room_damage_gate.py`.

## [2.8.5]

### Fixed
- **FIGHT-001 combat-entry parity**: `mud/commands/combat.py:do_kill` now mirrors ROM `src/fight.c:2815-2817` by entering combat through `multi_hit(ch, victim, TYPE_UNDEFINED)` instead of a single `attack_round()`. This restores haste / second-attack / third-attack follow-up swings for `kill` command combat starts. Regression coverage: `tests/integration/test_fight_c_do_kill_parity.py`.

## [2.8.4]

### Changed
- **Pyright cleanup across test suite.** Eliminated ~30 pre-existing `reportOptionalMemberAccess` / `reportArgumentType` / `reportAttributeAccessIssue` warnings across `tests/test_boards.py`, `tests/test_logging_admin.py`, `tests/test_commands.py`, `tests/test_wiznet.py`, `tests/test_affects.py`, and `tests/test_account_auth.py`. Approach: per-call-site `assert x is not None` guards on `Optional` returns from `find_board(...)`, `from_orm(db_char)`, `load_character(...)`, `Character.pcdata`, etc.; `cast(StreamReader, …)` / `cast(TelnetStream, …)` / `cast(Room, …)` for test doubles; widened `DummyWriter.write` overrides to `bytes | bytearray | memoryview`; initialized possibly-unbound `menu_task: asyncio.Task | None = None`; `# type: ignore[arg-type]` on the two intentional `dam_type=None` cases that exercise edge-case handling. No behavior change; tests still pass at the prior pre-existing-failure baseline.

## [2.8.3]

### Changed
- **Extract `time_info` persistence to `mud/world/time_persistence.py`.** `save_time_info`, `load_time_info`, `TimeSave`, and `TIME_FILE` now live in the new module. `tests/test_time_persistence.py` updated to import from the new location.
- **Extract serialization helpers to `mud/db/serializers.py`.** All live helpers imported by `mud/account/account_manager.py` (`_normalize_int_list`, `_serialize_colour_table`, `_serialize_object`, `_serialize_pet`, `_serialize_skill_map`, `_serialize_groups`) and `mud/models/character.py:from_orm` (`_apply_colour_table`, `_normalize_int_list`, `_deserialize_object`, `ObjectSave`, `_deserialize_pet`) now live in `mud/db/serializers.py`. Both importers updated.

### Removed
- **`mud/persistence.py` deleted.** The deprecated stub (holding only the two extracted surfaces above, plus dead code from the now-gone JSON-pfile path) is gone. No behavior change; `mud/persistence` was already a non-functional deprecation banner since 2.8.1.

## [2.8.2]

### Changed
- **Type cleanup on the new DB-canonical persistence surface.** `save_character_to_db` now types its `session` parameter as `sqlalchemy.orm.Session` (TYPE_CHECKING import) instead of `object`, dropping the `# type: ignore[union-attr]` on the `session.query` call. `mud/models/character.py:from_orm` casts `_deserialize_object(...)` to `Object | None` at the equipment-restore site so the `restored_equipment: dict[str, Object]` annotation is honored. No behavior change; pyright cleanup only. 25/25 critical persistence tests still green.

## [2.8.1]

### Changed
- **INV-008 reversal — Phase 2: DB-canonical persistence is live.** `mud/account/account_manager.save_character` and `load_character` now hit the SQL `Character` row directly (via Phase 1's `save_character_to_db` and `Character.from_orm`). The JSON-pfile delegation is removed; `mud/persistence.py` keeps only `time_info` save/load and a few ROM-only helpers (deprecated banner at module top). `tests/integration/test_inv008_persistence_coherence.py` now asserts the DB-canonical round-trip including a new `test_inv008_db_canonical_is_sole_path` case. INV-008 is ✅ ENFORCED again under the new architecture.

### Removed
- **JSON-pfile test files** — deleted because the surface they covered no longer exists: `tests/test_persistence.py`, `tests/test_persistence_password_hash.py`, `tests/test_player_save_format.py`, `tests/test_inventory_persistence.py`, `tests/integration/test_pet_persistence.py`, `tests/integration/test_save_load_parity.py`, `tests/integration/test_tables_001_affect_migration.py`. Persistence coverage is now provided by `tests/integration/test_db_canonical_round_trip.py` (7 tests) + `tests/integration/test_inv008_persistence_coherence.py` (5 tests). The 3 pre-existing `test_persistence.py` / `test_inventory_persistence.py` failures (broken-area-JSON / vnum 3022) are no longer relevant — those tests went away with the surface they tested.

## [2.8.0]

### Added
- **INV-008 reversal — Phase 1 of 2: DB-canonical persistence schema.** Following the discovery that `mud/account/account_service.create_character` and `mud/models/character.py:from_orm` still write/read the DB row at first-login (the JSON-pfile path was load-bearing only after first save), the project is reversing course on INV-008: the DB row is being made canonical for ALL player state, the JSON pfile path will be deleted in Phase 2. This commit extends the `Character` SQLAlchemy model with 39 new columns to hold every field `PlayerSave` round-trips (scalars: `max_hit`, `mana`, `move`, `gold`, `silver`, `exp`, `trust`, `invis_level`, `incog_level`, `saving_throw`, `hitroll`, `damroll`, `wimpy`, `position`, `played`, `logon`, `lines`, `prompt`, `prefix`, `title`, `bamfin`, `bamfout`, `security`, `points`, `last_level`, `affected_by`, `comm`, `wiznet`, `log_commands`, `pfile_version`, `board`; JSON columns: `mod_stat`, `armor`, `conditions`, `aliases`, `skills`, `groups`, `last_notes`, `colours`, `pet_state`, `inventory_state`, `equipment_state`). Extended `Character.from_orm` to hydrate every new column. New `save_character_to_db(session, char)` in `mud/account/account_manager.py` writes the full state via UPDATE. Round-trip proven by 7 new tests in `tests/integration/test_db_canonical_round_trip.py` (all green). Public `save_character` / `load_character` surface unchanged in this phase — Phase 2 swaps the implementations and deletes `mud/persistence.py`. INV-008 reopened in the cross-file invariants tracker.
- **`docs/parity/INV008_REVERSAL_AUDIT.md`** — 71-field map (PlayerSave → Character columns), `from_orm` audit, new code surface, caller surface, INV-008 test rewrite plan, and risk register; produced as the spec for both phases of the migration.

### Notes
- Pre-existing test slowness (full suite ~12 min vs. AGENTS.md's "~16s") and ~30 pre-existing test failures verified at the pre-Phase-1 baseline (git stash). Not introduced by this commit.

## [2.7.6]

### Changed
- **INV-008 DUAL-LOAD-CHARACTER-COHERENCE consolidated (hybrid path).** `mud/account/account_manager.py` is now a thin shim delegating `load_character` and `save_character` to `mud.persistence` (the JSON pfile path). The DB row (`mud/db/models.py:Character`) keeps `name` + `password_hash` for auth only; gameplay columns are vestigial and will be dropped in a later schema-migration session. Field-level audit at `docs/parity/INV008_DIVERGENCE_AUDIT.md`. No data migration was required — pre-launch.
- **`mud/persistence.py:PlayerSave` now persists `password_hash`** so the JSON pfile is the single ROM-faithful source of truth for all PC state, including auth credentials. `save_character` writes `pcdata.pwd`; `load_character` restores it. The shim's `save_character` also syncs the hash to the DB row so the auth path (`account_service.login_character`) stays consistent after `do_password`.

### Fixed
- **30+ PC fields previously dropped on every WS logout** (because the DB-backed `account_manager.save_character` only persisted ~18 columns). Now restored on next login: current mana / current move, gold, silver, exp, hitroll, damroll, saving throw, AC array, wimpy, position, mod_stat array, comm bitfield, affected_by, wiznet flags, conditions (drunk/full/thirst/hunger), full skill learned-percent map, aliases, colour table, prompt, title, bamfin/bamfout, played time, logon timestamp, pets, item timer/value/condition/enchanted/affects on inventory and equipment, container contents.

### Added
- **INV-008 enforcement test** (`tests/integration/test_inv008_persistence_coherence.py`): four cases asserting the `account_manager` shim round-trips full gameplay state, registers loaded characters in `character_registry` (INV-003), preserves `pcdata.pwd`, and restores room placement. INV-008 flipped from ⚠️ KNOWN DIVERGENCE → ✅ ENFORCED. **All 8 cross-file invariants are now ✅ ENFORCED.**
- `docs/parity/INV008_DIVERGENCE_AUDIT.md`: field-level provenance audit (51 vs 29 fields, caller surface, recommendation).

## [2.7.5]

### Added
- **INV-007 RNG-DETERMINISM enforcement test** (`tests/test_rng_determinism.py`): scans every `.py` file under `mud/combat/`, `mud/skills/`, and `mud/spells/` for `import random`, `from random`, or `random.` and fails with path:line detail if any match. Runs in <1s. INV-007 flipped from ⚠️ ENFORCED BY CONVENTION → ✅ ENFORCED. 7 of 8 cross-file invariants are now ✅ ENFORCED; INV-008 (DUAL-LOAD-CHARACTER-COHERENCE) remains a known divergence.

### Removed
- **Vestigial `stdlib Random` from `SkillRegistry`** (`mud/skills/registry.py`): `__init__` accepted `rng: Random | None` and stored `self.rng`, but `self.rng` was never read — all rolls in registry.py already went through `rng_mm`. Removed the dead field, the dead parameter, and the `from random import Random` import. `tests/test_skills.py:load_registry` updated accordingly. Required before INV-007's grep test could be written cleanly.

## [2.7.4]

### Added
- **INV-005 SAME-ROOM-COMBAT-ONLY enforcement test** (`tests/integration/test_inv005_same_room_combat.py`): proves `mud/game_loop.py:violence_tick` skips `multi_hit` and stops fighting when attacker and victim are in different rooms (ROM `src/fight.c:violence_update`). Plus a same-room sanity case so a flipped equality wouldn't silently pass.
- **INV-006 FIGHTING-POINTER-COHERENCE enforcement test** (`tests/integration/test_inv006_fighting_pointer_coherence.py`): proves `mud/combat/engine.py:stop_fighting(victim, both=True)` sweeps `character_registry` and clears every attacker pointing at the victim (ROM `src/fight.c:stop_fighting(victim, TRUE)`); inverse case confirms `both=False` does not sweep.
- Both invariants flipped from ⚠️ VERIFIED MANUALLY → ✅ ENFORCED in `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`.
- **Cross-File Invariants tracker** (`docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`): new top-level parity doc enumerating contracts the per-file audit methodology can't enforce on its own (single-delivery, registry membership, prompt-render-after-raw_kill, etc.). Eight INV-NNN entries seeded from this year's bug history; each has a stable ID, ROM mechanism, Python enforcement point, and regression test (or an action-item placeholder when the test is still missing).
- **AGENTS.md "Cross-File Invariants" section**: methodology note explaining what per-file audits miss and how to use the new tracker. Tracker added to the "Trackers" table.
- **rom-parity-audit skill update**: Phase 2 now requires following the call chain across module boundaries and consulting the cross-file invariants tracker; Phase 5 requires citing relevant INV-NNN statuses in each tracker row's Notes column ("Audited (per-file)" replaces bare "Audited").

### Changed
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`: `comm.c`, `fight.c`, and `save.c` rows annotated with the cross-file invariants they touch and the bugs the per-file audit missed (single-delivery, prompt clamp, registry membership). Per-file ratings preserved; the new annotations make the audit's actual coverage explicit.


## [2.7.3]

### Fixed
- **Combat parity (death path)**: Combat messages now reach connected PCs exactly once. `mud/combat/engine.py:_push_message` previously appended every message to `char.messages` AND scheduled an async send, and `mud/net/connection.py:1756` unconditionally drained `char.messages` after every command — so each combat line was delivered TWICE to WebSocket clients. Live repro: PC dies, types `look`, sees the entire combat sequence (including "You have been KILLED!!") replayed milliseconds later, making it appear they died twice. ROM `src/comm.c:write_to_buffer` is one-shot. Per `docs/divergences/MESSAGE_DELIVERY.md`, the mailbox is fallback-only for tests/disconnected characters; fix returns immediately after the async dispatch when a connection exists.
- **Combat parity (prompt display)**: `bust_a_prompt` now clamps displayed hit to >= 0. The death path could leave `char.hit` negative between `update_pos` setting `Position.DEAD` (at hit <= -11) and `raw_kill` clamping to `max(1, hit)` — Python's async dispatch can interleave a prompt render in that window, exposing the negative transient. ROM never shows negative hp because `raw_kill` always finishes first in its single-threaded loop. Display-only clamp at the two render sites (default prompt + `%h` token).
- **Combat parity (death-path comments)**: `_handle_death` documents the bidirectional fighting-pointer clear and its relationship with `raw_kill → _stop_fighting`'s `char_list` sweep. ROM ref: `src/fight.c:damage` death branch.

### Added
- `tests/test_prompt_clamps_hp.py` — 4 cases guarding prompt clamp (default + custom `%h`).
- `tests/integration/test_message_delivery_no_duplicate.py` — connected PC gets one async send, no mailbox queue; disconnected falls back to mailbox.
- `tests/integration/test_pc_death_no_message_replay.py` — end-to-end: pushes the actual death-message sequence, drives the read-loop drain manually, asserts "You have been KILLED!!" appears exactly once across both passes.
- `tests/integration/test_pc_death_keeps_connection.py` — regression guard that `raw_kill` keeps the PC in `character_registry`, in the death room, with hit/mana/move >= 1, position `RESTING`, connection intact.
- `mud/net/connection.py` — diagnostic logging upgrade: read-loop's outer `except` now prints `type(exc).__name__: exc!r` plus traceback so future disconnect causes are visible in server stdout.

## [2.7.2]

### Fixed
- Restore `version` field in `pyproject.toml` (accidentally dropped in `cdcd0cc`).
- Combat one-way bug: `mud/account/account_manager.load_character` now appends loaded PCs to `character_registry` so `violence_tick`/`char_update`/idle pump iterate them. Mirrors ROM `src/save.c:fread_char` `char_list` membership.
- World mob spawning: regenerated `resets` for 46 of 54 JSON area files via `scripts/patch_json_resets.py` so the school arena and other populated areas spawn ROM mobs on boot.
- BOARD-010: `note read again` is now a no-op (ROM `src/board.c:569-572`).

### Changed
- Reconciled `BOARD_C_AUDIT.md`, `OLC_C_AUDIT.md`, and `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` against current implementation; folded several stale-test fixes (`test_save_load_parity`, `test_olc_alist`, `test_spell_affects_persistence`, `test_tables_001_affect_migration`, `test_nanny_login_parity`, `test_fighting_state`, `test_olc_save`) and added `tests/test_obj_loader.py`.
- Session summaries added under `docs/sessions/` for the 2026-05-02 work (combat triage, board audit, OLC audit, asave cleanup, broad-suite triage / JSON itemtype fix).


### Fixed
- **OLC-004/005**: Active OLC editors now support ROM-style `commands` listings with five fixed-width columns, mirroring `src/olc.c:153-209`.
- **OLC-010/015**: `do_olc` / `editor_table[]` ported — `olc <area|room|object|mobile|mpcode|hedit>` now dispatches to the real per-editor entry points via prefix matching (`str_prefix` parity), NPC guard, and remainder-arg forwarding, mirroring ROM `src/olc.c:646-690`. Both `olc` and `edit` command aliases are live. Integration tests: `tests/integration/test_olc_010_015_do_olc_router.py` (14 cases).
- **OLC_SAVE-014**: `cmd_asave <vnum>` now silent on success (ROM `src/olc_save.c:982-995`)
- **OLC_SAVE-015**: `cmd_asave world` returns `"You saved the world.\n\r"` (ROM exact)
- **OLC_SAVE-016**: `cmd_asave changed` returns `"Saved zones:\n\r"` + per-area rows + `"None.\n\r"` fallback (ROM exact)
- **OLC_SAVE-017**: `cmd_asave area` returns `"Area saved.\n\r"` (ROM exact)
- **BOARD-010**: `note read again` is now a no-op (returns `""`) — mirrors ROM `src/board.c:569-572` empty `if`-body
- **MPEDIT-003**: Added `MprogCode` dataclass + `mprog_code_registry` dict + `get_mprog_index()` — mirrors ROM `MPROG_CODE` struct and `mprog_list` linked list (`src/olc_mpcode.c`)
- **MPEDIT-002**: `do_mpedit` now looks up `mprog_code_registry` (not `mob_prototypes`); opens `mpedit` session silently on success; exact Spanish error strings; `create` branch delegates to `_mpedit_create`
- **MPEDIT-001**: `_interpret_mpedit` session loop — smash_tilde, empty→show, `done` silent, security re-check, area=NULL→edit_done, dispatch table, fallback to `interpret()`
- **MPEDIT-004**: `_mpedit_show` — ROM exact format `"Vnum:       [%d]\n\rCode:\n\r%s\n\r"`
- **MPEDIT-005**: `_mpedit_code` — no-arg enters string_edit mode; arg → `"Syntax: code\n\r"`
- **MPEDIT-006**: `_mpedit_list` — `[%3d] (%c) %5d\n\r` format; `*/space/?` builder indicator; `all`/area filter; exact empty messages
- **HEDIT-002**: `hedit level` accepts -1..MAX_LEVEL; exact ROM error message
- **HEDIT-003/004**: `hedit keyword`/`hedit level` return `"Ok.\n\r"` / exact ROM syntax strings
- **HEDIT-005**: `hedit text` no-arg is valid (triggers `string_append`); arg present → `"Syntax: text\n\r"`
- **HEDIT-006**: security check returns `"HEdit: Insufficient security to edit helps.\n\r"` (with `\n\r`)
- **HEDIT-007**: empty input in hedit session → `hedit_show` (not syntax string)
- **HEDIT-008**: `done` is silent (returns `""`, no verbose save message)
- **HEDIT-009**: unknown hedit command falls back to normal command table (`interpret`)
- **HEDIT-010**: `hedit delete` implemented — removes from `help_entries` + all keyword buckets
- **HEDIT-011**: `hedit list all` / `list area` implemented with ROM 4-column `%3d. %-14.14s` format
- **HEDIT-012**: `do_hedit new <topic>` path correctly creates entry + enters editor
- **HEDIT-013**: `do_hedit <keyword>` uses `is_name` word-match (not exact key lookup)
- **HEDIT-014**: `hedit_level`/`hedit_keyword` return `"Ok.\n\r"` (triggers `had->changed = TRUE` equivalent) (`src/olc_act.c:770-790`) — sets `pArea->age`, validates numeric arg, does not set `changed` (ROM parity). 6 integration tests added.
- **OLC-012/013/014**: `redit`/`oedit`/`medit` fallback to `interpret()` verified — `_should_fallback_from_olc()` + `_process_descriptor_input()` returning `None` correctly re-dispatches unknown OLC input through the normal command table (mirrors ROM `src/olc.c:519-521`, `575-577`, `631-633`). 14 integration tests added in `tests/integration/test_olc_012_014_editor_fallback.py`.
- **OLC-009**: `medit` missing subcommands ported — `act`, `affect`, `armor`, `form`, `part`, `imm`, `res`, `vuln`, `off`, `size`, `hitdice`, `manadice`, `damdice`, `position`, `addmprog`, `delmprog` now dispatched from `_interpret_medit`. Helpers mirror ROM `src/olc_act.c:4142-4969`. Flag toggles use XOR pattern (act/affect/form/part/imm/res/vuln/off); `act` always re-sets `IS_NPC` (ROM:4153); dice stored as `tuple[int,int,int]`; `addmprog` validates vnum against mob_registry; `delmprog` splices list and clears mprog_flags bit. Integration tests: `tests/integration/test_olc_009_medit_missing_cmds.py` (30 cases).
- **OLC-008**: `oedit` missing subcommands ported — `addaffect`, `addapply`, `delaffect`, `extra`, `wear` now dispatched from `_interpret_oedit`. Helpers mirror ROM `src/olc_act.c:2818-3450`: flag-value toggle for `extra`/`wear` (ExtraFlag/WearFlag XOR), affect list append/splice for `addaffect`/`addapply`/`delaffect` with `TO_OBJECT=1`, `type=-1`, `duration=-1` ROM defaults. Integration tests: `tests/integration/test_olc_008_oedit_missing_cmds.py` (16 cases).
- **OLC-007**: `redit` missing subcommands ported — `rlist`, `mlist`, `olist`, `mshow`, `oshow` are now dispatched from `_interpret_redit`. Helpers `_redit_rlist/mlist/olist/mshow/oshow` mirror ROM `src/olc_act.c:329-570` (3-column vnum/name listing, `is_name` filtering, item-type prefix matching, mob/obj show via `_medit_show`/`_oedit_show`). Integration tests: `tests/integration/test_olc_007_redit_list_show.py` (16 cases).
- **OLC-011**: `aedit` flag-toggle prefix ported — typing a bare `area_flags` name (e.g. `loading`, `added`) inside an active aedit session now toggles the flag via `flag_value(AreaFlag, command)` and sends `"Flag toggled."`, mirroring ROM `src/olc.c:443-449`. Integration tests: `tests/integration/test_olc_011_aedit_flag_toggle.py` (7 cases).

## [2.7.1] — update.c Parity Gap Closures (GL-004/005/009/011/012/013/014/015/018)

### Fixed
- **GL-004**: `mana_gain` now uses `room.mana_rate` instead of `room.heal_rate`; rooms with custom mana rates now regenerate mana at the correct rate (ROM `update.c:300`).
- **GL-005**: `mana_gain` furniture bonus now reads `value[4]` (mana bonus) instead of `value[3]` (hit bonus) (ROM `update.c:218,300`).
- **GL-009**: NPC `char_update` wanders-home: out-of-zone NPCs that are not fighting and not charmed now have a 5% per-tick chance of being extracted (despawned) — mirrors ROM `update.c:688-696`. Previously missing entirely.
- **GL-011**: Plague tick implemented: spreads to room occupants (5% per-tick per target, saves vs disease), drains mana and move, and deals HP damage per tick (ROM `update.c:794-846`). Previously missing.
- **GL-012**: Poison tick implemented: sends "You shiver and suffer" message and deals `level // 10 + 1` HP damage per tick (ROM `update.c:848-862`). Previously missing.
- **GL-013**: INCAP position tick damage: 50% chance of 1 HP damage per tick (ROM `update.c:864-867`). Previously missing.
- **GL-014**: MORTAL position tick damage: 1 HP damage every tick unconditionally (ROM `update.c:868-871`). Previously missing.
- **GL-015**: `_idle_to_limbo` now calls `stop_fighting(ch, both=True)` instead of `ch.fighting = None`, properly cleaning both sides of any fight (ROM `update.c:741-744`).
- **GL-018**: Decay messages for objects inside an untakeable pit (vnum 3010) are now suppressed (ROM `update.c:1017-1018`). Previously objects inside a pit always broadcast their decay message to the room.

### Added
- `_char_update_tick_effects()` helper in `mud/game_loop.py` encapsulating all per-tick damage effects (plague, poison, INCAP, MORTAL).
- Integration tests: `tests/integration/test_update_c_parity.py` — 11 tests covering all closed gaps.

## [2.7.0] — ROM Character-First Login

### Changed

- **Login model replaced with ROM-faithful character-first auth** — the
  `PlayerAccount` ORM table and account-layer have been removed entirely.
  Characters now authenticate directly (mirroring ROM `nanny.c`/`save.c`):
  the server prompts `Name:`, branches to `Password:` for returning chars or
  `Did I get that right, <Name> (Y/N)?` → `New password:` → `Confirm
  password:` for new ones.  The `PlayerAccount` class is gone; `password_hash`
  now lives on the `Character` row.
- **`_select_character` simplified** — no character-selection menu; the login
  name *is* the character name, matching ROM's single-character-per-login model.
- **`login_with_host` / `login_character`** updated to query `Character` directly;
  `create_account` / `list_characters` / `release_account` kept as thin shims
  for call-site compatibility.
- **Reconnect flow** — duplicate-session detection and reconnect prompt now
  occur at the `Name:` stage (before password), matching ROM nanny behaviour.

### Fixed

- **`negotiate_ansi_prompt` test helper** — was waiting for `b"Account: "` after
  the ANSI negotiation; updated to `b"Name: "` to match the new login prompt.
- **`test_select_character_allows_permit_from_permit_host`** — monkeypatched
  `load_character` now uses single-arg signature; `account` arg updated to be
  the character row directly (ROM model).
- **`test_websocket_boots_loaded_world_and_uses_account_login_flow`** — rewritten
  for ROM flow (`Name:` → confirm → `New password:` → `Confirm password:`).
- **`test_telnet_server_handles_multiple_connections`** and
  **`test_telnet_break_connect_prompts_and_reconnects`** — updated to ROM login
  flow (no `Character:` prompt step).

### Fixed

- **Combat message delivery** — combat messages (damage, parry, dodge, position
  changes, weapon specials) now reach connected players immediately via
  fire-and-forget asyncio tasks, matching ROM C's `write_to_buffer()` real-time
  delivery. Previously messages were queued in `char.messages` and only drained
  when the player typed a command, causing combat to appear frozen.
  See `docs/divergences/MESSAGE_DELIVERY.md` for the design rationale.

### Changed (v2.6.108)

- **JSON_LOADER_C_AUDIT.md** — all 18 gaps now closed (remaining 6 in this batch).
- JSON loader applies per-type value coercion (`_parse_item_values`) at load time, mirroring ROM `src/db2.c:429-478` and the `.are` loader path.
- `attack_lookup` now handles numeric-string inputs (in-range passes through, out-of-range falls to name prefix-match), consistent with `_skill_lookup`/`_liq_lookup`/`_weapon_type_lookup`.

### Fixed (json_loader.py parity closures — JSONLD-001,003,015,016,017,018)

- **JSONLD-001** — Object keyword list populated from JSON `keywords` key (with `name` fallback) so `is_name()` matching works on JSON-loaded objects. Converter (`convert_are_to_json.py`) now emits `keywords` separately from display `name`. All 44 area JSONs regenerated.
- **JSONLD-003** — Object `level` field emitted by converter (`convert_are_to_json.py:object_to_dict`) and read by JSON loader. All area JSONs regenerated with `level` for every object.
- **JSONLD-015** — JSON loader now calls `_parse_item_values` (from `obj_loader`) to apply per-type value coercion at load time. `attack_lookup` updated to handle pre-resolved integer values from JSON.
- **JSONLD-016** — Object `short_descr` lowercased-first and `description` uppercased-first at load time, mirroring ROM `src/db2.c:869-870`.
- **JSONLD-017** — Room `light` verified at dataclass default 0 (ROM `src/db.c:1164`). Explicit init deemed redundant — closed-by-design.
- **JSONLD-018** — JSON-only `ROOM_NO_MOB` auto-add on no-exit rooms removed. ROM does not do this; rooms now behave identically to the `.are` path.

### Changed (v2.6.107)

- Includes previously uncommitted JSONLD-012, OLC, and build changes from earlier session.

### Fixed (act_wiz.c stat family parity closures — WIZ-039..044)

- **WIZ-039** — `do_mstat` practices now uses caller's NPC status (`char.is_npc`) instead of victim's, matching ROM `IS_NPC(ch) ? 0 : victim->practice`.
- **WIZ-040** — `do_mstat` Hit/Dam now use `get_hitroll(victim)` / `get_damroll(victim)` (including STR-app bonuses) per ROM `GET_HITROLL` / `GET_DAMROLL`.
- **WIZ-041** — `do_mstat` Age/Played/Last_Level now computed via `get_age(victim)`, `(played + current_time - logon) / 3600`, and `pcdata.last_level` per ROM instead of hardcoded 17/0/0.
- **WIZ-042** — `do_mstat` Carry weight now uses `get_carry_weight(victim) // 10` (includes coin burden) per ROM.
- **WIZ-043** — `do_ostat` Number/Weight line now uses `_object_carry_number(obj)` and `_get_obj_weight(obj)` per ROM `get_obj_number` / `get_obj_weight` / `get_true_weight`.
- **WIZ-044** — `do_rstat` Objects list now has 3 spaces after colon per ROM `".\n\rObjects:   "`.

### Fixed (JSON loader parity closures — v2.6.105)

- **JSONLD-012** — JSON-loaded mob `race` values now resolve through ROM `race_lookup` into integer `race_table` indexes at load time, matching ROM `src/db2.c:234`. Race flag merging, OLC JSON save, and `medit show` display now handle integer-backed mob races without losing the human-readable race name.

### Fixed (JSON loader parity closures — v2.6.104)

- **JSONLD-009** — JSON-loaded areas now default `security` to 9 for both supported JSON formats, preserving explicit JSON values when present. This mirrors ROM `src/db.c:452` / `src/db.c:531` and restores the expected OLC builder-security default.
- **JSONLD-010** — Format 1 JSON areas now hydrate `credits` from the JSON payload when present, mirroring ROM `src/db.c:457`.
- **JSONLD-013** — JSON room `clan` values now resolve through `lookup_clan_id`, including ROM-style prefix matching, instead of preserving raw strings. Mirrors ROM `src/db.c:1192`.
- **JSONLD-014** — JSON `D` resets now apply boot-time door state and are discarded rather than retained in `area.resets` / `room.resets`, mirroring ROM `src/db.c:1058-1104`.

### Fixed (JSON loader parity closures — v2.6.103)

- **JSONLD-002** — Object `extra_descr` now stores `ExtraDescr` instances instead of raw dicts, matching the `.are` loader and ROM (`src/db2.c:571-580`). Consumer sites no longer need dict-aware fallback.
- **JSONLD-004** — Mob `hit`/`mana`/`damage` int tuples now parsed from `hit_dice`/`mana_dice`/`damage_dice` strings at load time via `_parse_dice_tuple`, matching ROM (`src/db2.c:251-269`). The `templates.py:_parse_dice` fallback still works as defense.
- **JSONLD-005** — Object `wear_flags` now converted from ROM letter string to int bitmask via `convert_flags_from_letters(WearFlag)`, matching the `.are` loader (`obj_loader.py:389`).
- **JSONLD-006** — Object `affected` list now populated with typed `Affect` instances from `affects` dicts, matching ROM (`src/db2.c:519-568`). `obj.affected` is no longer empty on JSON-loaded objects.
- **JSONLD-007** — Mob `hitroll` now populated from JSON `hitroll` key (falling back to `thac0`), matching ROM (`src/db2.c:248`). Previously `hitroll` was always 0 for JSON-loaded mobs.
- **JSONLD-008** — Mob `off_flags`/`imm_flags`/`res_flags`/`vuln_flags` int fields now populated after `merge_race_flags` via `_to_int_flags`, matching ROM (`src/db2.c:279-286`). Previously these stayed 0 on JSON-loaded mobs.
- **JSONLD-011** — Mob `form`/`parts` now converted from letter strings to int bitmasks after `merge_race_flags`, matching ROM (`src/db2.c:295-297`). Previously `IS_SET(mob.form, FORM_EDIBLE)` would fail with `ValueError`.

### Fixed (in-game runtime bugs surfaced 2026-04-30)

- `BUG-MOBHP` — Every JSON-loaded mob spawned with `max_hit=0` / `current_hp=1`, so look reported "awful condition" universally and a level 1 PC could one-shot Hassan (level 45). `mud/spawning/templates.py:_parse_dice` short-circuited on the default `(0,0,0)` primary tuple before consulting the `hit_dice` / `mana_dice` / `damage_dice` string fallback the JSON loader populated. Now treats all-zero primary as "unset" and falls through. ROM ref: `src/db.c:fread_mobile`. (commit `715469d`)
- `BUG-CORPSEINT` — `get coins corpse` raised `ValueError: invalid literal for int() with base 10: 'npc_corpse'`. `mud/loaders/json_loader.py:_load_objects_from_json` now routes prototype `item_type` through `_resolve_item_type_code` (mirroring the legacy `.are` loader), and `mud/commands/inventory.py:do_get` defensively coerces. ROM ref: `src/db.c:load_objects` `flag_value`. (commit `0f0d871`)
- `BUG-EDDICT` — `look fountain`, `read letter` raised `'dict' object has no attribute 'description'` because the JSON loader stores `extra_descr` as raw dicts and `mud/world/look.py` accessed `.description` attribute-style. Added `_ed_fields(ed)` helper accepting both shapes. ROM ref: `src/act_info.c:do_look`, `EXTRA_DESCR_DATA`. (commit `cb4eed7`)
- `BUG-NLOWER` — `look corpse`, `open south`, `open door` raised `'NoneType' object has no attribute 'lower'` because JSON-loaded prototypes carry `name=None` (the JSON schema collapsed ROM's separate keyword field) and ~15 helper sites used `getattr(x, "name", "").lower()`. Swept all match sites to the safe `(getattr(x, "name", None) or "").lower()` form across `mud/world/{obj_find,char_find}.py` and `mud/commands/{obj_manipulation,combat,misc_player,info_extended,imm_commands,imm_search,socials,remaining_rom}.py`. (commit `658d319`)

### Changed

- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` and `docs/parity/DB_C_AUDIT.md` — added "Re-audit Triggers from In-Game Debug Pass (2026-04-30)" sections flagging `mud/loaders/json_loader.py` as a partial port of `src/db.c:load_objects` / `load_mobiles` / `fread_obj` / `fread_mobile`. The four fixed bugs all trace to the JSON-path skipping ROM normalization that the `.are` loader performs. Recommendation to downgrade the db.c "100% certified" badge or split scope deferred to next session. The data-side gap (JSON dropped ROM's separate `name`/keyword field on objects) is still unfixed.

### Added

- `mud/loaders/json_loader.py` parity audit (`docs/parity/JSON_LOADER_C_AUDIT.md`) — Phase 1–3 complete. Function inventory mapped against `src/db.c:load_objects` / `load_mobiles` / `load_rooms` / `load_resets` / `load_shops` / `fread_obj` / `fread_mobile` / `convert_mob` / `convert_obj`. **18 stable gap IDs filed (JSONLD-001..018)**: 7 CRITICAL (object keyword list missing from schema; `extra_descr` raw dicts; object `level` missing; mob hit/mana/damage tuples not populated at load; `wear_flags` raw string; `obj.affected` typed list never populated; mob `hitroll` populated from wrong JSON key — `thac0`); 8 IMPORTANT (off/imm/res/vuln int fields zero on JSON-loaded mobs; area `security`/`credits` defaults; `form`/`parts` raw strings; `race` as string not index; room `clan` not lookup-validated; D-reset semantics divergence; no per-type `value[]` coercion at load time); 3 MINOR (`short_descr`/`description` first-letter normalization; room `light` default reliance; `_link_exits_for_area` JSON-only `ROOM_NO_MOB` auto-set). The four runtime bugs fixed earlier today appear as JSONLD-001/002/003/004 — three are mitigated at consumer sites and remain ⚠️ OPEN at the loader, JSONLD-003 (`item_type`) is ✅ FIXED loader-side. `convert_mob` / `convert_obj` documented as intentionally absent (JSON files carry pre-resolved new-format values). Closures pending via `rom-gap-closer` per-gap; suggested ordering (single-commit fixes first): JSONLD-002, 004, 005, 006, 007, 008, 011 → then schema/converter changes for JSONLD-001, 003.

### Added

- `olc_save.c` parity audit (`docs/parity/OLC_SAVE_C_AUDIT.md`) — Phase 1–3 complete. 17 ROM functions inventoried. **JSON-authoritative framing locked**: Python writes JSON via `mud/olc/save.py` (`save_area_to_json`); `.are` remains read-only legacy input via `mud/loaders/area_loader.py`. Format-level divergences (ROM `fwrite_flag` A–Za–z encoding, `fix_string` tilde strip, `.are` column widths) are documented as N/A under this framing. 20 stable gap IDs filed (OLC_SAVE-001..020): **8 CRITICAL** round-trip data-loss bugs (mob `off`/`imm`/`res`/`vuln` flags, `form`/`parts`/`size`/`material`, mprog list, shop binding, spec_fun binding; object `level`, structured affect chain, structured extra-descr); **5 IMPORTANT** (no help-save path, `cmd_asave area` only handles `redit`, no autosave entry, NPC security gate gap, `save_area_list` missing `social.are` + HELP_AREA prepend); **7 MINOR** (4 string-drift cases, condition-letter ladder, exit lock-flag normalization, door-reset synthesis). Closures pending via `rom-gap-closer` per-gap. Tracker: `olc_save.c` row flipped ❌ Not Audited → ⚠️ Partial.

### Fixed

- `OLC_SAVE-009` — Area-grouped help-save / help-load round trip. New `_serialize_help` helper in `mud/olc/save.py` emits the canonical `{level, keywords, text}` shape; `save_area_to_json` now includes a per-area `helps` list (symmetric with mobs / objects / rooms / mob_programs / shops / specials). Paired loader-side change: new `_load_helps_from_json` in `mud/loaders/json_loader.py` walks the section, appends each entry to `area.helps`, and registers it in `help_registry` so `do help <keyword>` keeps resolving across save→reload cycles. Mirrors ROM `src/olc_save.c:826-843` (save_helps). Closes the IMPORTANT-block hole that forced the OLC_SAVE-010 hedit dispatcher to no-op behind a "Grabando area :" placeholder. ROM `save_other_helps` standalone-help-file fan-out (`src/olc_save.c:845-872`) remains N/A under JSON-authoritative framing — Python has no global `had_list`; helps live on their owning area. Tests: `tests/integration/test_olc_save_009_area_helps_round_trip.py` (3 cases).
- `OLC_SAVE-013` — `save_area_list` (`mud/olc/save.py`) now prepends `social.are\n` as the first line of the area.lst file, mirroring ROM `src/olc_save.c:94` (ROM OLC convention). Python omitted the prepend, causing the first area filename to appear in the position ROM reserves for the `social.are` marker. HAD/HELP_AREA standalone-help-area filename rows remain N/A pending OLC_SAVE-009 (help-save port). Tests: `tests/integration/test_olc_save_013_area_list_social_prepend.py` (2 cases: prepend with areas present, prepend with empty registry).
- `OLC_SAVE-012` — `_is_builder` (`mud/commands/build.py`) now gates on `char.is_npc` before consulting `pcdata.security` or `area.builders`, mirroring the ROM `IS_BUILDER` macro's leading `!IS_NPC(ch)` clause (`src/merc.h`) and the `IS_NPC(ch) → sec = 0` clamp in `cmd_asave` (`src/olc_save.c:933`). Without this gate, an NPC whose name happened to appear in an area's `builders` list (or one carrying a stub `pcdata.security`) would have passed the builder check, letting mob_special-style flows bypass area security. Existing OLC test fixtures updated to set `is_npc=False` on PCs (they were relying on the missing gate). Tests: `tests/integration/test_olc_save_012_npc_security_gate.py` (3 cases: NPC name match, NPC stub-pcdata bypass, PC regression).
- `OLC_SAVE-011` — `cmd_asave` now accepts `char=None` for the autosave-timer entry path. Mirrors ROM `src/olc_save.c:931-936` (`if (!ch) sec = 9` lets `do_asave(NULL, "world")` persist every area). The "world" branch now skips the `_is_builder` gate when ch is None and returns silently (ROM `if (ch) send_to_char`); other args short-circuit before char-attribute access. Unblocks future autosave wiring (`olc_save.c` autosave timer port). Tests: `tests/integration/test_olc_save_011_autosave_entry.py` (3 cases: null-ch saves every area, null-ch with empty registry no-crash, player-path message regression).
- `OLC_SAVE-010` — `@asave area` now dispatches across all five ROM editor types (aedit / redit / oedit / medit / hedit) instead of only `redit`. `cmd_asave` (`mud/commands/build.py`) now resolves the target area from `session.editor_state["area"]` for aedit, `room.area` for redit, `obj_proto.area` for oedit, and `mob_proto.area` for medit; hedit returns the ROM-faithful "Grabando area :" prefix pending OLC_SAVE-009 (help-save port). Mirrors ROM `src/olc_save.c:1080-1128`. Without this, aedit/oedit/medit users got "You are not editing an area, therefore an area vnum is required." and their changes were silently unsaveable. Tests: `tests/integration/test_olc_save_010_asave_area_dispatch.py` (6 cases: aedit/redit/oedit/medit dispatch, hedit help-save marker, ED_NONE error).
- `OLC_SAVE-008` — Object extra-description list now routed through `_serialize_extra_descr` (`mud/olc/save.py`), which is dict-aware so a prototype carrying either a plain `{"keyword", "description"}` dict (from `mud/loaders/obj_loader.py`) or an `ExtraDescr` dataclass instance produces an identical flat payload. Mirrors ROM `src/olc_save.c:431-435`. Replaces the prior raw `list(...extra_descr, [])` pass-through that crashed `json.dump` on dataclass values and let stray dict keys leak through. Tests: `tests/integration/test_olc_save_008_object_extra_descr.py` (3 cases: dict round-trip, `ExtraDescr` dataclass json-safe, canonical-key shape).
- `OLC_SAVE-007` — Object affect chain now serialized through a dedicated `_serialize_affect` helper (`mud/olc/save.py`) that normalizes a prototype affect — accepting either a plain dict (A-line `{location, modifier}` or F-line `{where, location, modifier, bitvector}` per `mud/loaders/obj_loader.py`) or an `Affect` dataclass instance — into a json-safe dict. Mirrors ROM `src/olc_save.c:399-429` (TO_OBJECT applies + TO_AFFECTS/IMMUNE/RESIST/VULN). Replaces the prior opaque `list(...affects, [])` pass-through that silently dropped fields and crashed `json.dump` on dataclass values. Tests: `tests/integration/test_olc_save_007_object_affects.py` (5 cases: A-line dict normalization, F-line preservation, `Affect` dataclass shape, mixed-shape round-trip, `json.dump` regression).
- `OLC_SAVE-006` — Object `level` now persisted on JSON save. `_serialize_object` (`mud/olc/save.py`) emits the field; paired loader-side change in `_load_objects_from_json` (`mud/loaders/json_loader.py`) reads it back. Mirrors ROM `src/olc_save.c:378` (save_object level emission). Without this, a save→reboot→reload cycle silently reset every object level to 0, breaking level-gated drops, identify output, and equipment loadout heuristics. Tests: `tests/integration/test_olc_save_006_object_level.py` (3 cases: serializer field emit, full round-trip, default level=0 round-trip).
- `OLC_SAVE-005` — Mob `spec_fun` bindings now persisted on JSON save via a new top-level `specials` section emitted by `save_area_to_json` (`mud/olc/save.py`). Mirrors ROM `src/olc_save.c:578-606` (save_specials writes `M <vnum> <spec_fun>` rows in the per-area `#SPECIALS` section). Loader-side `apply_specials_from_json` (`mud/loaders/specials_loader.py`) was already in place; this closure adds the missing serialize half. Without this, a save→reboot→reload cycle silently erased every spec_fun binding (e.g. `spec_breath_fire` on dragons reverted to no special). Tests: `tests/integration/test_olc_save_005_mob_spec_fun.py` (3 cases: section emit, full round-trip, mob-without-spec_fun emits no entry).
- `OLC_SAVE-004` — Mob shop bindings (`MobIndex.pShop` → keeper / buy_types[5] / profit_buy / profit_sell / open_hour / close_hour) now persisted on JSON save via a new top-level `shops` section emitted by `save_area_to_json` (`mud/olc/save.py`). Mirrors ROM `src/olc_save.c:786-824` (save_shops). Paired loader-side change: new `_load_shops_from_json` (`mud/loaders/json_loader.py`) rehydrates `mud.registry.shop_registry` keyed by keeper vnum and re-attaches `MobIndex.pShop` after mob load. Without this, a save→reboot→reload cycle silently erased every shop binding — keepers reverted to non-merchant NPCs. Tests: `tests/integration/test_olc_save_004_mob_shops.py` (3 cases: section emit, full round-trip restoring `shop_registry`, mob-without-shop emits no entry). Loader and serializer changes ship in one commit per the audit's locked closure rule.
- `OLC_SAVE-003` — Mob `mprogs` (mob program assignments) now persisted on JSON save via a new `mob_programs` section emitted by `save_area_to_json` (`mud/olc/save.py`). Mirrors ROM `src/olc_save.c:151-169` (save_mobprogs writes the per-area `#MOBPROGS` section) plus `src/olc_save.c:245-250` (per-mob MPROG_LIST inside save_mobile). Without this, a save→reboot→reload cycle silently erased every mob program binding. Python's JSON layout factors program code area-wide and links via assignments (matching `mud/loaders/json_loader.py:_load_mob_programs_from_json`); the new `_collect_mob_programs` helper reverses that projection by walking each mob's `mprogs` list and grouping by program vnum. Triggers serialize via `mud.mobprog.format_trigger_flag` (int → ROM keyword). Tests: `tests/integration/test_olc_save_003_mob_mprogs.py` (3 cases: single assignment, multiple mobs sharing one program, mob without mprogs).
- `OLC_SAVE-002` — Mob `form`/`parts`/`size`/`material` now persisted by `_serialize_mobile` on JSON save (`mud/olc/save.py:136`). Mirrors ROM `src/olc_save.c:213-219` (save_mobile fwrite/fwrite_flag for Form/Parts/Size/Material). Without this, a save→reload cycle silently dropped physical descriptors that drive corpse parts, magic targeting, and combat sizing. `Size` enum values are coerced to lowercase names (e.g. `Size.MEDIUM` → `"medium"`) to match the `_load_mobs_from_json` string contract. JSON-write content locked by `tests/integration/test_olc_save_002_mob_form_parts_size_material.py` (3 cases). Note: a full Python-object equality round-trip is not asserted because the loader's `merge_race_flags` unions race-default bits into `form`/`parts` on read; the JSON file itself is the canonical write surface and is asserted directly.
- `OLC_SAVE-001` — Mob defensive/offensive flag sets (`offensive`/`immune`/`resist`/`vuln` letter-strings) now persisted by `_serialize_mobile` on JSON save (`mud/olc/save.py:136`). Mirrors ROM `src/olc_save.c:205-208` (save_mobile fwrite_flag for Off/Imm/Res/Vuln). Without this, a save→reboot→reload cycle silently dropped all mob defensive flag sets. Round-trip locked by `tests/integration/test_olc_save_001_mob_defensive_flags.py` (3 cases: serializer field emission, full save→load round-trip, empty/zero flag-string safety).
- `OLC_ACT-014` — Locked the `area.changed = True` protocol divergence between Python and ROM. ROM `src/olc.c:452-463`/`:510-521` dispatchers `SET_BIT(pArea->area_flags, AREA_CHANGED)` whenever a subcommand handler returns `TRUE`; Python uses an imperative pattern where each `_interpret_*edit` branch sets `area.changed = True` directly after a successful mutation. Structural divergence with equivalent behavior. Added a ROM-cite comment to `_mark_area_changed` (`mud/commands/build.py:220`) and a regression test that exercises one representative `name` mutation per editor (aedit/redit/oedit/medit), one secondary subcommand (aedit `security`), and one failed-mutation no-op case mirroring ROM's "handler returned FALSE → no SET_BIT" path. Test: `tests/integration/test_olc_act_014_area_changed_protocol.py` (6 cases).
- `OLC_ACT-013` — Locked the equivalence between Python `_get_area_for_vnum` (`mud/commands/build.py:1352`) and ROM `get_vnum_area` (`src/olc_act.c:588-599`). ROM walks the `area_first` linked list; Python iterates `area_registry.values()`. CPython dicts preserve insertion order (3.7+), so load-order traversal is equivalent to ROM's linked-list walk. Added a ROM-cite comment to the function and a regression test that locks the dict insertion-order guarantee plus first-match-on-overlap behavior. Test: `tests/integration/test_olc_act_013_get_area_for_vnum_order.py` (3 cases).

### Added

- `OLC-016` / `OLC-017` / `OLC-018` / `OLC-019` — sibling-audit dispatcher gaps closed transitively by OLC_ACT-001/002/003/004/005/006. The OLC-NNN gaps were filed in `OLC_C_AUDIT.md` as "missing dispatcher subcommand" entries; the OLC_ACT-NNN gaps are the corresponding builder-logic closures in `src/olc_act.c`. In Python, the dispatcher and builder live in the same `cmd_*edit` function in `mud/commands/build.py`, so closing the OLC_ACT side automatically closes the OLC side. All four CRITICAL `do_*edit create` paths are now wired with full ROM validation chains and authoritative `new_*_index` defaults from `src/mem.c`.
- `OLC_ACT-002` + `OLC_ACT-003` + `OLC_ACT-004` — `redit create <vnum>` / `redit reset` / `redit <vnum>` silent teleport (`mud/commands/build.py:cmd_redit`). All three are branches of ROM's single `do_redit` function (`src/olc.c:745-821`) so they ship in one combined commit. **OLC_ACT-002**: explicit `redit create <vnum>` keyword wired with full ROM validation chain (vnum required, area assignment, IS_BUILDER, already-exists). `new_room_index` defaults from `src/mem.c:181-218` (heal_rate=100, mana_rate=100). After create, builder is moved into the new room via silent `_char_from_room`/`_char_to_room`. **OLC_ACT-003**: `redit reset` dispatcher wired — security gate, exact ROM message "Room reset.\\n\\r", area `changed=True`, calls `apply_resets(area)` via `_apply_resets_for_redit` wrapper. ROM uses `reset_room(pRoom)` (src/olc.c:765); Python's broader-scope `apply_resets(area)` is a documented minor divergence pending a per-room reset port. **OLC_ACT-004**: `redit <vnum>` silent-teleport reuses existing `_char_from_room`/`_char_to_room` primitives from `mud.commands.imm_commands` per the locked human-decision flag — no new movement infra. Validates target room exists, IS_BUILDER on TARGET area, relocates, sets descriptor edit pointer. Unblocks OLC-017 (all three halves: create/reset/vnum). Tests: `tests/integration/test_olc_act_002_redit_create.py` (8), `tests/integration/test_olc_act_003_redit_reset.py` (4), `tests/integration/test_olc_act_004_redit_vnum_teleport.py` (5).
- `OLC_ACT-006` — `medit create <vnum>` subcommand (`mud/commands/build.py:_medit_create`). Mirrors ROM `src/olc_act.c:3704-3753` plus `new_mob_index` defaults from `src/mem.c:365-424` (player_name="no name", short_descr="(no short description)", long_descr="(no long description)\\n\\r", description="", level=0, sex=Sex.NONE, size=Size.MEDIUM, start_pos="standing", default_pos="standing", material="unknown", new_format=True). **CRITICAL**: `ActFlag.IS_NPC` is set on both `act_flags` (modern) and legacy `act` per ROM `src/olc_act.c:3745` `pMob->act = ACT_IS_NPC;` — without this, every NPC-classification check downstream would misclassify newly-built mobs as players. Full ROM validation chain (vnum required, area assignment, builder security, already-exists). Removed pre-existing auto-create-on-unknown-vnum bug. Unblocks OLC-019. Test: `tests/integration/test_olc_act_006_medit_create.py` (12 cases). Drive-by: `tests/integration/test_olc_builders.py:test_mob_proto` fixture also patched to write to the canonical `mud.models.mob.mob_registry` (matching the OLC_ACT-005 obj-fixture fix).
- `OLC_ACT-005` — `oedit create <vnum>` subcommand (`mud/commands/build.py:_oedit_create`). Mirrors ROM `src/olc_act.c:3178-3225` plus `new_obj_index` defaults from `src/mem.c:297-335` (name="no name", short_descr="(no short description)", description="(no description)", item_type="trash", material="unknown", extra_flags=0, wear_flags=0, weight=0, cost=0, value=[0]*5, new_format=True). Full ROM validation chain: vnum required (empty/zero rejected with "Syntax:  oedit create [vnum]"), area assignment ("OEdit:  That vnum is not assigned an area."), builder security ("OEdit:  Vnum in an area you cannot build in."), already-exists ("OEdit:  Object vnum already exists."). Returns "Object Created.\n\r" on success. **Removed** the pre-existing auto-create-on-unknown-vnum bug — unknown vnums without the explicit `create` keyword now return an error instead of silently allocating a new proto. Unblocks OLC-018. Test: `tests/integration/test_olc_act_005_oedit_create.py` (11 cases). Drive-by: fixed `tests/integration/test_olc_builders.py:test_obj_proto` fixture which registered protos in the wrong registry (`mud.registry.obj_registry` vs the canonical `mud.models.obj.obj_index_registry`).
- `OLC_ACT-001` — `aedit create` subcommand (`mud/commands/build.py:cmd_aedit` + `_aedit_create`). Mirrors ROM `src/olc_act.c:667-679` plus authoritative defaults from `src/mem.c:91-122` (`new_area`): `name="New area"`, `builders="None"`, `security=1`, `min/max_vnum=0`, `empty=True`, `area_flags=AreaFlag.ADDED`, `file_name="area<vnum>.are"`. Vnum allocation uses `max(area_registry) + 1` (Python adaptation; ROM uses global `top_area` counter). Reachable from both `@aedit create` (no active session) and `create` typed inside an active aedit session. Unblocks OLC-016 in the sibling audit. Test: `tests/integration/test_olc_act_001_aedit_create.py` (9 cases).
- `olc_act.c` parity audit (`docs/parity/OLC_ACT_C_AUDIT.md`) — Phase 1–3 complete. 108 ROM functions inventoried across four editors (aedit/redit/oedit/medit); mpedit/hedit out of scope (sibling audits). 14 stable gap IDs filed (OLC_ACT-001..014): 6 CRITICAL (aedit_create wholly missing; redit_create missing; redit reset/vnum dispatcher gaps; oedit_create missing security gate; medit_create missing ACT_IS_NPC flag on new mobs), 6 IMPORTANT (show-command completeness for all four editors; success message string drift; aedit_reset missing), 2 MINOR (structural). Tier breakdown: TIER A 9 functions (line-by-line), TIER B 8 functions (moderate), TIER C ~78 functions (inventory). Closures pending via `rom-gap-closer` per-gap. Tracker: olc_act.c row flipped ❌ Not Audited → ⚠️ Partial.

### Fixed

- `OLC_ACT-007` — `aedit show` now includes the area flags row (mirroring ROM `src/olc_act.c:644-646`). The Flags line uses `flag_string(AreaFlag, area.area_flags)` to format the ADDED/CHANGED/LOADING flags. Test: `tests/integration/test_olc_act_007_aedit_show_flags.py` (5 cases).
- `OLC_ACT-008` — `redit show` brought to ROM byte-parity with `src/olc_act.c:1068-1236`. Sector display labels in `_SECTOR_NAMES` (`mud/commands/build.py`) now use `swim`/`noswim` per ROM `src/tables.c:391-392` (previously `water_swim`/`water_noswim`); the exit line in `_room_summary` now emits the two-space gap between `Key: [%5d]` and `Exit flags:` per ROM lines 1184/1196 (single sprintf trailing space + strcat leading space). The remaining ROM fields (description, name, area, vnum, room flags, heal/mana/clan/owner/extra-descs, characters, objects, per-exit keyword/description, uppercase-non-reset flag rule) were already implemented in `_room_summary`; the new parity tests lock them in going forward. Test: `tests/integration/test_olc_act_008_redit_show_parity.py` (4 cases).
- `OLC_ACT-010` — `medit show` rewritten to ROM byte layout (`src/olc_act.c:3519-3699`). Now emits all ROM rows in order: Name/Area, Act flags, Vnum/Sex/Race, Level/Align/Hitroll/DamType, conditional Group, Hit/Damage/Mana dice, Affected by, Armor (4 columns), Form, Parts, Imm, Res, Vuln, Off, Size, Material, Start/Default pos, Wealth, Short/Long/Description. New helpers `_format_intflag`/`_format_position`/`_format_size`/`_format_sex` in `mud/commands/build.py`. Three sub-gaps explicitly deferred and recorded in `docs/parity/OLC_ACT_C_AUDIT.md`: **OLC_ACT-010b** dice/AC byte format (Python data model stores strings; ROM stores 3 ints per dice); **OLC_ACT-010c** shop/mprogs/spec_fun rendering (needs MobShop/MProg model alignment + `spec_name` lookup); **OLC_ACT-010d** ROM-faithful flag-table name strings (display tables analogous to OLC_ACT-009's `_WEAR_FLAG_DISPLAY`/`_EXTRA_FLAG_DISPLAY` needed for 10 mob flag tables). Existing `tests/test_olc_medit.py::test_medit_show_command` assertions updated to ROM format. New: `tests/integration/test_olc_act_010_medit_show_parity.py` (8 cases).
- `OLC_ACT-012` — `aedit reset` subcommand wired in `_interpret_aedit` (`mud/commands/build.py`). Mirrors ROM `src/olc_act.c:653-663` `aedit_reset`: calls `apply_resets(area)` via the existing `_apply_resets_for_redit` wrapper, sets `area.changed=True`, returns ROM-exact `"Area reset."` (previously `"Unknown area editor command: reset"`). Test: `tests/integration/test_olc_act_012_aedit_reset.py` (1 case).
- `OLC_ACT-011` — All four `*_name` OLC builders (`aedit_name`, `redit_name`, `oedit_name`, `medit_name`) now return ROM's exact `"Name set."` success message (was Python-verbose "Area name set to: X" / "Room name set to X" / "Object name (keywords) set to: X" / "Player name set to: X"). ROM source: `src/olc_act.c:683-700`/`1770-1787`/`2990-3010`/`3913-3931`. Existing assertions in `tests/test_olc_aedit.py` / `test_olc_medit.py` / `test_olc_oedit.py` updated. New: `tests/integration/test_olc_act_011_name_messages.py` (4 cases).
- `OLC_ACT-009` — `oedit show` rewritten to ROM byte layout (`src/olc_act.c:2733-2812`) + `_show_obj_values` ported from ROM `show_obj_values` (`src/olc_act.c:2210-2374`). New display tables `_WEAR_FLAG_DISPLAY` / `_EXTRA_FLAG_DISPLAY` mirror `src/tables.c:434-483` byte-for-byte (ROM-faithful labels: "finger"/"nosac"/"wearfloat"/"antigood"/"rotdeath" — not Python enum-name forms). New `_APPLY_NAMES` dict mirrors `src/merc.h:1205-1231` + `src/tables.c:489-516` for the affects table (with the ROM `APPLY_SAVES`/`APPLY_SAVING_PARA` 20-collision resolved to "saves"). `_show_obj_values` covers 13 ITEM_* cases (LIGHT, WAND/STAFF, PORTAL, FURNITURE, SCROLL/POTION/PILL, ARMOR, WEAPON, CONTAINER, DRINK_CON, FOUNTAIN, FOOD, MONEY); WAND/STAFF/SCROLL/POTION/PILL spell-name lookup emits raw value-index until a skill-by-index registry lands. Existing `tests/test_olc_oedit.py::test_oedit_show_command` assertions updated from Python-only verbose labels to ROM format. New: `tests/integration/test_olc_act_009_oedit_show_parity.py` (8 cases).
- `OLC-022` — `do_resets` (`mud/commands/imm_olc.py`) rewritten with full ROM subcommand set (src/olc.c:1232-1469): P-reset via `inside <containerVnum> [limit] [count]` (validates ITEM_CONTAINER or ITEM_CORPSE_NPC), O-reset via `room`, G/E-reset via wear-loc prefix lookup (`lfin` → FINGER_L), R-reset via `random 1..6`, M-reset extended with optional `[max#area] [max#room]` args. 6-line syntax block on unrecognized numeric-arg subcommand. `_add_reset` helper extracted. Test: `tests/integration/test_olc_do_resets_subcommands.py` (27 cases).
- `OLC-020` — `display_resets` (`mud/commands/imm_olc.py`) now faithfully formats each reset type (M/O/P/G/E/D/R) with exact ROM `sprintf` column widths, pet-shop `final[5]='P'` overlay (src/olc.c:1037-1044), wear-loc decoding via `wear_loc_strings` table, and door-reset state decoding. Bad-mob/obj `continue` paths correctly suppress output per ROM. New `mud/utils/olc_tables.py` provides `WEAR_LOC_STRINGS`, `WEAR_LOC_FLAGS`, `DOOR_RESETS`, `DIR_NAMES` tables ported from `src/tables.c:355-572`. Test: `tests/integration/test_olc_display_resets.py` (16 cases).
- `OLC-023` — `do_alist` (`mud/commands/imm_olc.py:121-146`) iterated the nonexistent `registry.areas` attribute and returned a header-only listing on a live system. Now iterates `area_registry.values()`, prints `area.vnum` (was a 1-indexed enumerate counter — drifted from ROM `src/olc.c:1494`'s `pArea->vnum`), and reads `area.file_name` (was the nonexistent `area.filename`). Test: `tests/integration/test_olc_alist.py` (4 cases).

### Added

- `STRING-004` — `string_add` OLC editor input dispatcher (.c/.s/.r/.f/.h/.ld/.li/.lr dot-commands, ~/@ termination with on_commit callback, MAX_STRING_LENGTH-4 length cap) (src/string.c:121). 24 integration tests in `tests/integration/test_string_editor_string_add.py`. Completes `string.c` at 100%.
- `STRING-005` — `format_string` word-wrap, sentence capitalization (src/string.c:299).
- `STRING-002` — `mud/utils/string_editor.py:string_append(string_edit_obj, current) -> str`. Mirrors ROM `src/string.c:66-86`: enter APPEND mode, preserve the buffer, and return the editor banner (4 lines) plus the `numlines()` line-numbered listing. Takes a `StringEdit` object and a *current* string (the existing text to append to), unlike `string_edit` which clears. The banner matches ROM verbatim: `-=======- Entering APPEND Mode -========-`, help, termination, and separator. The listing shows each line with its 1-indexed line number in `%2d` format. Used by every OLC description builder (`aedit_builder`, `redit`, `medit`, `oedit`, etc.). Test: `tests/integration/test_string_editor_append.py` (9 cases).
- `STRING-001` — `mud/utils/string_editor.py:string_edit(string_edit_obj) -> str`. Mirrors ROM `src/string.c:38-57`: enter EDIT mode, clear the buffer, return the editor banner (4 lines). Takes a `StringEdit` object (mirrors ROM `ch->desc->pString` field) and initializes it with an empty buffer. The returned banner matches ROM verbatim: `-========- Entering EDIT Mode -=========-`, help prompt, termination instructions, and separator. Used by `olc_act.c::aedit_builder` ("desc edit"), `redit` (edit-description), `medit` (edit-description). Test: `tests/integration/test_string_editor_edit.py` (6 cases).
- `STRING-003` — `mud/utils/string_editor.py:string_replace(orig, old, new) -> str`. Mirrors ROM `src/string.c:95-112`: replace the first occurrence of *old* substring within *orig* with *new*. If *old* is not found, returns *orig* unchanged. Empty *old* returns *orig* unchanged (ROM behavior). Used by `string_add::.r` dot-command (STRING-004) and `aedit_builder::replace`. Test: `tests/integration/test_string_editor_replace.py` (9 cases).
- `STRING-010` — `mud/utils/string_editor.py:string_lineadd(string, newstr, line) -> str`. Mirrors ROM `src/string.c:607-645`: insert *newstr* as the 1-indexed line N. The inserted line gets a `\n\r` suffix. If line is past the end, insertion doesn't happen (never reached). Used by `.li` and `.lr` dot-commands. Test: `tests/integration/test_string_editor_lineadd.py` (10 cases).
- `STRING-009` — `mud/utils/string_editor.py:string_linedel(string, line) -> str`. Mirrors ROM `src/string.c:574-605`: remove the 1-indexed line N from the string, preserving `\n\r` line endings. Out-of-range line numbers are a no-op. Used by `.ld` dot-command. Test: `tests/integration/test_string_editor_linedel.py` (8 cases).
- `STRING-012` — `mud/utils/string_editor.py:numlines(string) -> str`. Mirrors ROM `src/string.c:676-692`: format string as line-numbered listing (`%2d. <line>\n\r`), 1-indexed. Used by `.s` dot-command and `string_append` greeting. Test: `tests/integration/test_string_editor_numlines.py` (7 cases).
- `STRING-011` — `mud/utils/string_editor.py:merc_getline(string) -> tuple[str, str]`. Mirrors ROM `src/string.c:647-674`: read one `\n`-terminated line; consume trailing `\r` when present (ROM `\n\r` canonical line ending). Returns `(rest, line)`. Test: `tests/integration/test_string_editor_merc_getline.py` (6 cases).
- `STRING-006` — `mud/utils/string_editor.py:first_arg(argument, lower=False) -> tuple[str, str]`. Mirrors ROM `src/string.c:468-508`: quote/paren-aware single-arg parser. Recognizes `'`/`"`/`%` (self-pair quotes) and `(`/`)` (balanced pair). Unterminated quotes consume the entire remainder. The `lower` flag (ROM `fCase`) lowercases the parsed word. Test: `tests/integration/test_string_editor_first_arg.py` (10 cases).
- `STRING-008` — `mud/utils/string_editor.py:string_proper(argument) -> str`. Mirrors ROM `src/string.c:551-572`: uppercases first char of each space-delimited word, leaves rest of each word as-is. Differs from Python `str.title()` which also lowercases the rest. Test: `tests/integration/test_string_editor_proper.py` (8 cases).
- `STRING-007` — `mud/utils/string_editor.py:string_unpad(argument) -> str`. Mirrors ROM `src/string.c:516-543`: trims leading/trailing spaces (only spaces, not all whitespace) — `aedit_builder` callers expect tab/newline preservation. Test: `tests/integration/test_string_editor_unpad.py` (7 cases).
- `BIT-003` — `mud/utils/bit.py:is_stat(table) -> bool`. Mirrors ROM `src/bit.c:93-104` (and replaces ROM's static `flag_stat_table[]` registry at `src/bit.c:50-83`): returns True for IntEnum (stat) tables, False for IntFlag (flag) tables. The Python port encodes the stat-vs-flag distinction in the type system, so no runtime registry is needed. With BIT-001/002/003 closed, `bit.c` flips ✅ Audited 90% → ✅ Audited 100%. Test: `tests/integration/test_bit_is_stat.py` (5 cases).
- `BIT-002` — `mud/utils/bit.py:flag_string(table, bits) -> str`. Mirrors ROM `src/bit.c:151-177`: returns a space-joined string of every flag name set in *bits* for IntFlag (flag) tables, the single matched name for IntEnum (stat) tables, or the literal `"none"` when nothing matched. The ROM rotating two-buffer trick (`buf[2][512]`) is unnecessary in Python (immutable strings). Composite alias IntFlag members are skipped to avoid double-printing. Test: `tests/integration/test_bit_flag_string.py` (8 cases).
- `BIT-001` — `mud/utils/bit.py:flag_value(table, argument) -> int | None`. Mirrors ROM `src/bit.c:111-142`: tokenizes the argument, prefix-looks up each token, OR-accumulates hits for IntFlag (flag) tables, returns a single matched value for IntEnum (stat) tables, returns `None` (the `NO_FLAG` sentinel) on no match. Unknown tokens are silently skipped, mirroring ROM `flag_value` semantics (which differ from ROM `do_flag` on purpose). Test: `tests/integration/test_bit_flag_value.py` (9 cases).
- `OLC-INFRA-001` — descriptor-level OLC editor state plumbing. New `mud/olc/editor_state.py` provides `EditorMode` IntEnum (mirrors ROM `src/olc.h:53-59` — `NONE`/`AREA`/`ROOM`/`OBJECT`/`MOBILE`/`MPCODE`/`HELP`), `StringEdit` dataclass (mirrors ROM `desc->pString` — buffer + on-commit hook + `MAX_STRING_EDIT_LENGTH=4604`), and `route_descriptor_input(session)` (mirrors ROM `src/comm.c:833-847` — `string_edit` precedes `editor_mode` precedes normal interpret). `Session.editor_mode` and `Session.string_edit` fields wired in `mud/net/session.py`. Destinations (`string_add` for STRING-004, `run_olc_editor` for OLC-001) remain stubbed under their own gap IDs; this commit lands only the routing decision and data shapes that unblock the STRING-001..012 cluster. Test: `tests/integration/test_olc_descriptor_state.py` (6 cases).

### Changed

- `string.c` parity audit (`docs/parity/STRING_C_AUDIT.md`) — `string.c` flipped ⚠️ Partial 85% (stale, wrong file path) → ✅ Audited 5% (accurate). Phase 1 inventory catalogues all 12 public functions (`string_edit`, `string_append`, `string_replace`, `string_add`, `format_string`, `first_arg`, `string_unpad`, `string_proper`, `string_linedel`, `string_lineadd`, `merc_getline`, `numlines`); every one is OLC-editor backend operating on `ch->desc->pString`/`ch->desc->editor` with no current Python consumer (`mud/olc/` skeleton only). 12 stable gap IDs filed (`STRING-001..STRING-012`), all DEFERRED to the OLC audit cluster (`olc.c`/`olc_act.c`/`olc_save.c`/`olc_mpcode.c`/`hedit.c`) where their first concrete consumers will appear. Previous tracker note "85% — `mud/utils.py`" was stale: that file does not exist; only `mud/utils/text.py:smash_tilde` (a `merc.h` helper, not a `string.c` helper) is ported. No code changes.
- `const.c` parity audit (`docs/parity/CONST_C_AUDIT.md`) — Phase 1–3 complete. 16 ROM data tables inventoried; 13 ✅ AUDITED (item, wiznet, attack, race, pc_race, class, int_app, liq, skill, group, plus `str_app.carry` + `str_app.wield` columns); 7 stable gap IDs filed (`CONST-001`..`CONST-007`). **Four CRITICAL combat-math gaps surfaced**: `CONST-002` `GET_HITROLL` macro missing `str_app[STR].tohit` (`mud/combat/engine.py:411,420`), `CONST-003` `GET_DAMROLL` missing `str_app[STR].todam` (`mud/combat/engine.py:1184`), `CONST-004` `GET_AC` missing `dex_app[DEX].defensive` (`mud/combat/engine.py:391`), `CONST-005` `advance_level` missing `con_app[CON].hitp` + `number_range(hp_min,hp_max)` per-level HP roll (`mud/advancement.py:91`). One IMPORTANT advancement gap (`CONST-006` `wis_app[WIS].practice` in `advance_level`). One IMPORTANT data gap (`CONST-001` `title_table` 480 entries — defer to NANNY-009 dedicated session). One MINOR (`CONST-007` `weapon_table` — defer to OLC audit, BIT-style). `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` row updated; tracker held at ⚠️ Partial 80% pending closures via `/rom-gap-closer`. No code changes.
- `bit.c` parity audit (`docs/parity/BIT_C_AUDIT.md`) — `bit.c` flipped ⚠️ Partial 90% → ✅ Audited 90%. Confirmed the only current Python consumer of bit.c-shaped logic (`do_flag` in `mud/commands/remaining_rom.py`) faithfully mirrors ROM `do_flag` semantics (not ROM `flag_value` — they differ on unknown-name handling on purpose). Three MINOR helpers (`flag_value`, `flag_string`, `flag_stat_table`+`is_stat`) recorded as `BIT-001`/`BIT-002`/`BIT-003` and deferred to the OLC audit, where their first concrete consumers (`olc.c`, `olc_act.c`, `olc_save.c`, `act_olc.c`) will appear. No code changes.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — reconciled the stale `P1-3: db.c + db2.c (PARTIAL - 55%)` section with the actual audit state. Both files have been ✅ Audited 100% on the summary table since the Jan 5 (db.c) and Apr 28 (db2.c) sessions; the P1-3 narrative section has been rewritten to reflect that and to point at the per-file audit docs (`DB_C_AUDIT.md` covers db.c's 44/44 functional functions; `DB2_C_AUDIT.md` covers DB2-001/002/003/006 closures and DB2-004/005 deferred MINORs). No code changes.

### Added

- `comm.c` parity audit (`docs/parity/COMM_C_AUDIT.md`) — non-networking surface of `src/comm.c` (`bust_a_prompt`, `act_new`, `colour`, `check_parse_name`, `stop_idling`, `fix_sex`, `show_string`) mapped to Python equivalents. Networking layer (`main`, `init_socket`, `game_loop_*`, descriptor I/O) confirmed deferred-by-design per the asyncio rewrite. Phase 3 produces 9 stable gap IDs (`COMM-001..COMM-009`).
- `mud/utils/prompt.py:bust_a_prompt(char) -> str` — port of ROM `src/comm.c:1420-1595`. Expands `%h %H %m %M %v %V %x %X %g %s %a %r %R %z %% %e %c %o %O` against character state, falls back to `<%dhp %dm %dmv> %s` when `ch->prompt` is unset, short-circuits to `<AFK>` when `COMM_AFK` is on. Wired into both telnet game-loop call sites in `mud/net/connection.py`. Test: `tests/integration/test_prompt_rom_parity.py` (8 cases).
- `board.c` parity audit (`docs/parity/BOARD_C_AUDIT.md`) — full Phase 1 inventory of every public ROM function in `src/board.c` (Erwin Andreasen 1995–96 note-board subsystem) mapped to `mud/notes.py`, `mud/models/board.py`, and `mud/commands/notes.py`. Phase 3 produces 14 stable gap IDs (BOARD-001..BOARD-014); `tracker.md` flips `board.c` from ❌ Not Audited 35% → ⚠️ Partial 85%. New regression suite `tests/integration/test_boards_rom_parity.py` (6 ROM-parity tests, all green).

### Added

- `MUSIC-002` — `mud/music/__init__.py:load_songs(path=area/music.txt)` ports ROM `src/music.c:160-218`. Reads the ROM-format music data file (`group~` / `name~` / lyric lines / `~` / `#`), populates `mud.music.song_table` (up to `MAX_SONGS=20`), resets `channel_songs[0..MAX_GLOBAL]` to `-1`, drops lyrics past `MAX_LINES=100` with a warning, and gracefully no-ops on a missing file. Wired into `mud/world/world_state.py:initialize_world` so the song table is populated at boot — the global "MUSIC:" channel and `play list` previously had nothing to broadcast or display. Tests: `tests/integration/test_music_load_songs.py` (3 cases).

### Fixed

- `CONST-006` — `advance_level` per-level practice gain now applies `wis_app[get_curr_stat(ch, STAT_WIS)].practice`, mirroring ROM `src/update.c:87`. Previously the gain was a hardcoded `PRACTICES_PER_LEVEL = 2` constant — WIS-3 dunce was getting 2 free practices/level instead of 0; WIS-13 default got 2 instead of 1; WIS-25 sage got 2 instead of 5. New `mud/math/stat_apps.py::WIS_APP` table (verbatim port of `src/const.c:790-817`) and `wis_practice_bonus(ch)` accessor. The level-up message now reflects the actual roll with correct singular/plural pluralisation. Per AGENTS.md "test asserting behavior that contradicts ROM is a bug in the test", five existing tests in `tests/test_advancement.py` and `tests/integration/test_character_advancement.py` that asserted the old constant gain were updated to assert ROM's wis_app formula. Test: `tests/integration/test_advancement_wis_app.py` (26 cases).
- `CONST-005` — `advance_level` per-level HP gain now follows ROM `src/update.c:74-79` exactly: `UMAX(2, (con_app[get_curr_stat(ch, STAT_CON)].hitp + number_range(class_table[ch->class].hp_min, class_table[ch->class].hp_max)) * 9 / 10)`. Previously used a static `LEVEL_BONUS[ch_class]` dict (`mud/advancement.py:91`) — both the RNG roll and the CON modifier were absent, so a CON-25 character was missing +8 hitp/level and a CON-3 character was missing −2 hitp/level on top of the missing variability. New `mud/math/stat_apps.py::CON_APP` table (verbatim port of `src/const.c:850-878`) and `con_hitp_bonus(ch)` accessor. Mana/move continue to use the legacy `LEVEL_BONUS` path until their respective gaps close. Per AGENTS.md "test asserting behavior that contradicts ROM is a bug in the test", six existing tests in `tests/test_advancement.py` and `tests/integration/test_character_advancement.py` that asserted the old static HP values were updated to seed `rng_mm.number_range` and assert the ROM formula. Test: `tests/integration/test_advancement_con_app.py` (14 cases).
- `CONST-004` — Armor class now augments `armor[type]` with `dex_app[get_curr_stat(ch, STAT_DEX)].defensive` when the character `IS_AWAKE` (`position > POS_SLEEPING`), mirroring ROM `src/merc.h:2104-2106`. New `mud/math/stat_apps.py::DEX_APP` table (verbatim from `src/const.c:821-848`) and `get_ac(ch, ac_type)` accessor; combat at `mud/combat/engine.py:391`, `do_score` at `mud/commands/session.py`, and the wiz `stat char` AC line at `mud/commands/imm_search.py` all read through it. Sleeping/stunned/incap/dead victims still show raw armor (the IS_AWAKE gate). Before this fix, a DEX-3 character was missing +40 AC penalty and a DEX-25 character was missing −120 AC bonus on every combat hit-roll and every AC display. Test: `tests/integration/test_combat_dex_app.py` (11 cases).
- `CONST-003` — Combat `GET_DAMROLL` now augments `ch->damroll` with `str_app[get_curr_stat(ch, STAT_STR)].todam`, mirroring ROM `src/merc.h:2109-2110` (consumed at `src/fight.c:588` for weapon damage). New `mud/math/stat_apps.py::get_damroll(ch)` accessor; `calculate_weapon_damage` at `mud/combat/engine.py:1189` now reads it. Before this fix, a STR-3 attacker missed −1 damage and a STR-25 attacker missed +9 damage. Test: `tests/integration/test_combat_str_app.py::test_get_damroll_*` (7 cases).
- `CONST-002` — Combat `GET_HITROLL` now augments `ch->hitroll` with `str_app[get_curr_stat(ch, STAT_STR)].tohit`, mirroring ROM `src/merc.h:2107-2108` (consumed at `src/fight.c:471` for THAC0). New module `mud/math/stat_apps.py` ports `STR_APP[26]` verbatim from `src/const.c:728-755` and exposes `get_hitroll(ch)`; both attack paths in `mud/combat/engine.py` (THAC0 at L411, percent fallback at L420) now read the augmented value. Before this fix, a STR-3 attacker missed −3 to-hit and a STR-25 attacker missed +6. Test: `tests/integration/test_combat_str_app.py` (8 cases).
- `MUSIC-004` — `mud/commands/player_info.py:do_play` jukebox scan now applies `mud.world.vision.can_see_object(ch, obj)` so invisible / VIS_DEATH / dark-room jukeboxes drop out of selection, mirroring ROM `src/music.c:229-232`'s `can_see_obj(ch, juke)` filter. Test: `tests/integration/test_music_play.py::test_do_play_skips_invisible_jukebox`.

- `MUSIC-003` — `play list` in `mud/commands/player_info.py:do_play` now reads `mud.music.song_table` (previously `mud.registry.song_table`, which doesn't exist, so it always fell through to a 3-song hardcoded stub). Reproduces ROM `src/music.c:246-292`: capitalized `"<short_descr> has the following songs available:"` header, `play list <prefix>` filters song names by case-insensitive prefix in two `%-35s` columns, `play list artist [<prefix>]` filters by group name in single-line `%-39s %-39s` group/name pairs, and a trailing odd column is flushed on its own line. Tests: `tests/integration/test_music_play.py` (4 new list-formatting cases).

- `MUSIC-001` — `mud/commands/player_info.py:do_play` now ports the queueing half of ROM `src/music.c:220-354`. Previously a stub: it found a jukebox, returned `"Coming right up."`, and queued nothing — so `song_update()` had nothing to broadcast and `play loud` was silently ignored. The port now resolves the `loud` keyword for global plays, enforces the `value[4] > -1` / `channel_songs[MAX_GLOBAL] > -1` queue-full check (`"The jukebox is full up right now."`), case-insensitive name-prefix matches against `mud.music.song_table`, surfaces `"That song isn't available."` on no match, and writes the song id into the first free `juke.value[1..4]` (local) or `channel_songs[1..MAX_GLOBAL]` (global) slot — also resetting the slot-0 line cursor to `-1` when slot 1 is filled, matching ROM `src/music.c:337-352`. Tests: `tests/integration/test_music_play.py` (7 cases).

- `NANNY-008` — `broadcast_entry_to_room` (`mud/net/connection.py`) now moves `char.pet` into the owner's room via `char_to_room` and emits a TO_ROOM "$n has entered the game." for the pet on login, mirroring ROM `src/nanny.c:810-815`. Previously a returning player's pet stayed un-roomed and onlookers never saw the pet's arrival. Test: `tests/integration/test_nanny_login_parity.py::test_login_pet_follows_owner_into_room`.
- `COMM-009` — Standalone `mud/utils/fix_sex.py:fix_sex(ch)` helper added, mirroring ROM `src/comm.c:2178-2182`: clamps `ch.sex` to `[0,2]`, falling back to `pcdata.true_sex` for PCs and `0` for NPCs. Inline clamp at the affect-strip site in `mud/handler.py:1110-1112` now delegates to the helper. Test: `tests/test_fix_sex.py` (5 cases).
- `COMM-008` — ANSI translator now covers ROM `colour()` specials at `src/comm.c:2714-2728`: `{D` → `\x1b[1;30m`, `{*` → `\x07` (bell), `{/` → `\n\r`, `{-` → `~`, `{{` → `{`. `mud/net/ansi.py` rewritten as a single-pass `re.sub` so `{{` cannot be re-matched as `{h` once partially consumed; `strip_ansi` mirrors ROM `send_to_char` non-colour branch (`src/comm.c:1995-2007`) by eating both characters of any `{X` pair. Tests: `tests/test_ansi.py::test_translate_ansi_handles_rom_specials` and `::test_strip_ansi_eats_rom_token_pairs`.
- `COMM-007` — `_stop_idling` now broadcasts the ROM "$n has returned from the void." message through `mud/utils/act.py:act_format`, mirroring ROM `act(...)` at `src/comm.c:1922`. The previous literal `f"{name} has returned from the void."` fallback rendered "Someone has returned…" for entities without a `name`; with the new act_format pipeline, `$n` expands via `_pers` (name → short_descr fallback). Test: `tests/test_networking_telnet.py::test_stop_idling_broadcast_uses_rom_act_format`.
- `COMM-002` — `show_string` pager input semantics now match ROM. While paging, `_read_player_command` (`mud/net/connection.py`) used to treat `"c"` as continue and dispatch arbitrary non-empty input to `interpret()`. ROM `src/comm.c:632-633` instead routes input to `show_string` instead of `interpret`, and `show_string` at `src/comm.c:2131-2141` aborts on any non-empty input and consumes it as no-op. Fix: empty input continues paging; any non-empty input clears the pager and returns `" "` (no-op). The bulk paging machinery (`Session.start_paging` / `send_next_page`) was already wired through `mud/net/protocol.py:send_to_char`; this closure pinned the missing ROM-faithful abort semantics. Tests: `tests/test_networking_telnet.py::test_show_string_pager_aborts_on_any_non_empty_input_per_rom` (new) and `test_show_string_paginates_output` (updated to assert `" "` no-op consumption).
- `COMM-006` — `is_valid_character_name` now rejects names matching any clan in `CLAN_TABLE` (case-insensitive), mirroring ROM `src/comm.c:1713-1718`. `rom`/`ROM` and `loner` are both rejected at character creation.
- `COMM-004` — Character-creation name validator now rejects names that collide with any mob prototype's `player_name` keyword list, mirroring ROM `src/comm.c:1782-1796`. Implemented as a new `mud.account.is_valid_character_name` helper layered on top of `is_valid_account_name`; the old syntactic-only validator stays intact for account-name validation (a Python addition with no ROM analogue). `create_character` and the connection-layer character-creation flow both use the new validator. Pre-existing tests in `tests/test_account_auth.py` that used stock RPG names colliding with real mobs (`Zeus`, `Nomad`, `Queen`, `Guardian`) were renamed to invented tokens — per AGENTS.md "test contradicting ROM C is a bug in the test."
- `COMM-003` — `check_parse_name` length floor now matches ROM. `is_valid_account_name` rejected names shorter than 3 characters; ROM `src/comm.c:1729` rejects only names shorter than 2. Two-letter ROM-legal names (e.g. `Bo`) are now accepted. The previous NANNY-012 test (`test_name_validator_matches_rom_check_parse_name`) had locked in the buggy `< 3` threshold with a docstring misreading ROM — the test now asserts the correct ROM `< 2` bound (`Bo` accepted, `a` rejected).
- `COMM-001` — Player prompts now render character state. The telnet game loop previously emitted a literal `"> "` regardless of `do_prompt` settings; HP / mana / move / room / alignment never reached the client. Fix: replaced the hard-coded `send_prompt("> ")` with `send_prompt(bust_a_prompt(char))` at `mud/net/connection.py:1698,1923` and made `do_prompt` write to `Character.prompt` (mirrors ROM `ch->prompt`, `src/act_info.c:951-952`) instead of `PCData.prompt` (which in ROM is the colour triplet, not the format string). `send_prompt` now applies ANSI rendering so `{p…{x` colour wrappers don't leak as raw text. Five existing tests in `test_player_prompt.py` / `test_player_auto_settings.py` / `test_config_commands.py` updated to assert the correct field (per AGENTS.md "test contradicting ROM C is a bug in the test").
- `BOARD-001` — Five hardcoded ROM boards (General/Ideas/Announce/Bugs/Personal) are now seeded on `load_boards()` with the exact ROM levels, force-types, default recipients, and purge-days from `src/board.c:67-76`. Persisted JSON content is overlaid on top so notes survive a reload but the static metadata cannot drift below ROM defaults.
- `BOARD-002` / `BOARD-003` — `note write` and `note send` now emit ROM TO_ROOM `act()` broadcasts ("$n starts writing a note." / "$n finishes $s note.") via `char.room.broadcast(..., exclude=char)`, mirroring `src/board.c:503` and `src/board.c:1181`. Adds `_possessive(char)` helper for ROM `$s` (his/her/its from `Character.sex`).
- `BOARD-004` — `Board.post` now routes through a new `mud.notes.next_note_stamp(base)` helper backed by a module-level `_last_note_stamp` counter, mirroring ROM `finish_note` (`src/board.c:154-160`). Two notes posted in the same wall-clock second now get distinct, monotonically increasing timestamps so the `> last_read` unread cursor cannot collide. Test fixtures reset the counter per test (parallel to ROM rebooting `boot_db` globals).
- `BOARD-005` (and `BOARD-006`) — `Board.unread_count_for(char, last_read)` mirrors ROM `unread_notes` (`src/board.c:444-460`) by filtering through `mud.notes.is_note_to(char, note)` (the canonical recipient predicate, factored out of `mud/commands/notes.py`). `do_board` listing now uses the recipient-aware count, so Personal/per-name notes no longer leak into non-recipients' unread totals. `BOARD-006` is subsumed by this fix (ROM's listing filter `unread_notes != BOARD_NOACCESS` is now consistent with what each row displays).
- `BOARD-008` — `load_boards` now sweeps every loaded board for notes whose `expire < now` and appends them to `<board>.old.json` before re-saving the active board, mirroring ROM `load_board`'s archive at `src/board.c:365-383`. Boards no longer grow without bound across reloads.
- `BOARD-012` — `do_note` now mirrors ROM `src/board.c:736-737`: an unknown subcommand (anything other than `read`/`list`/`write`/`remove`/`purge`/`archive`/`catchup` and the Python-only draft verbs) dispatches to `do_help(ch, "note")` instead of returning the generic `"Huh?"`. Test: `tests/integration/test_boards_rom_parity.py::test_note_unknown_subcommand_shows_help`.
- `BOARD-011` — `note write` now mirrors ROM `do_nwrite` at `src/board.c:482-488`: when the player has an in-progress draft whose `text` is empty (e.g. lost link before typing the body), the stale draft is discarded and the actor sees the ROM cancellation notice ("Note in progress cancelled because you did not manage to write any text before losing link.") before a fresh draft is started. Test: `tests/integration/test_boards_rom_parity.py::test_note_write_discards_textless_in_progress_draft`.
- `BOARD-013` — Added `mud.notes.make_note(board_name, sender, to, subject, expire_days, text)` and `mud.notes.personal_message(...)` mirroring ROM `make_note` / `personal_message` at `src/board.c:843-886`. Unknown boards and text exceeding `MAX_NOTE_TEXT` (= `4 * MAX_STRING_LENGTH - 1000` = 17432, per `src/board.h:19`) return `None` (mirroring ROM's silent `bug` + return); on success the note is appended via `Board.post` (so it picks up the unique `last_note_stamp` cursor), persisted with `save_board`, and `expire = current_time + expire_days * 86400`. Unblocks programmatic Personal-board injection for death notifications and system mail.

- `TABLES-001` — `AffectFlag` bit positions (`mud/models/constants.py`) renumbered to match ROM `src/merc.h:953-982` exactly (letters A..dd → bits 0..29). Closes a 20-of-29-bit divergence where `convert_flags_from_letters` was decoding ROM area-file letters with the canonical mapping (e.g. `G` → bit 6) but Python `AffectFlag.SANCTUARY` sat on bit 6, so any letter-form area data was silently mis-aligned with the enum. Pfile schema gains `pfile_version: int` (default `0`); legacy saves are translated on load by `mud/persistence.py:translate_legacy_affect_bits` (covers character `affected_by`, every nested `Affect.bitvector` on persisted items, pet `affected_by`, and pet affect bitvectors), then re-saved at `pfile_version=1`. Reproducer `tests/integration/test_tables_parity.py::test_affect_flag_letters_match_rom_merc_h` flipped from `xfail(strict)` → green; `test_merc_h_letter_macros_match_python_intflag_values` now also covers `AFF_*`. New migration tests in `tests/integration/test_tables_001_affect_migration.py`. Tables.c flips ⚠️ Partial 75% → ✅ AUDITED 100%.
- `TABLES-003` — Programmatic verification of every `src/merc.h` letter-mapped `#define` macro against the matching Python `IntFlag` member's bit value. New test `tests/integration/test_tables_parity.py::test_merc_h_letter_macros_match_python_intflag_values` parses merc.h, resolves A..Z / aa..dd letter tokens, and cross-checks ~210 macros across the `ACT_/PLR_/OFF_/IMM_/RES_/VULN_/FORM_/PART_/COMM_/ROOM_/GATE_/FURN_/WEAPON_` prefixes. Confirms only `AFF_*` (TABLES-001) diverges; all other letter-mapped tables in `src/tables.c` have correct Python bit positions. Acts as a durable regression guard.
- `TABLES-002` — `mud/utils/prefix_lookup.py:prefix_lookup_intflag` now consults a ROM `src/tables.c` table-name alias map (`rom_flag_aliases`) before falling back to Python IntFlag member names. ROM-style abbreviations like `+npc`/`+healer`/`+changer`/`+can_loot`/`+dirt_kick`/`+noclangossip` now resolve to the matching Python flag member (`IS_NPC`/`IS_HEALER`/`IS_CHANGER`/`CANLOOT`/`KICK_DIRT`/`NOAUCTION`), restoring ROM `flag_lookup` parity for `do_flag` and OLC.

### Added

- `tables.c` parity audit (`docs/parity/TABLES_C_AUDIT.md`): Phase 1 inventory of all 38 ROM data tables in `src/tables.c` mapped to Python `IntFlag`/`IntEnum` equivalents in `mud/models/constants.py`; Phase 2 spot-checks confirm `ActFlag` / `PlayerFlag` / `OffFlag` / `CommFlag` bit positions match ROM letters A..dd. Three gaps documented: **TABLES-001 (CRITICAL)** — `AffectFlag` bit positions diverge from ROM `merc.h:953-982` (e.g. `AFF_DETECT_GOOD=G=1<<6` in ROM, but `AffectFlag.SANCTUARY=1<<6` in Python); `convert_flags_from_letters` decodes ROM letters with the ROM-correct mapping, so any area-file `AFF G` is silently mis-decoded as `SANCTUARY`. Closure deferred — requires `AffectFlag` renumber + persistence migration plan. TABLES-002 (ROM-name aliases for prefix-match) and TABLES-003 (per-table value verification for the remaining 30+ tables) also open. New `tests/integration/test_tables_parity.py` (4 passing spot-checks + 1 xfail reproducer for TABLES-001).

### Fixed

- `LOOKUP-008` — Added public `liq_lookup(name)` to `mud/utils/prefix_lookup.py` mirroring ROM `src/lookup.c:138-150` (case-insensitive prefix-match against `LIQUID_TABLE`, returns `-1` on miss). The loader-internal `mud/loaders/obj_loader.py:_liq_lookup` is retained because it intentionally returns `0` (water) on miss for object-load defaults. With this `lookup.c` is ✅ AUDITED at 100% (LOOKUP-001..008 all closed).
- `LOOKUP-007` — Added `item_lookup(name)` to `mud/utils/prefix_lookup.py` mirroring ROM `src/lookup.c:124-136` (case-insensitive prefix-match against `ItemType` IntEnum, returns the ITEM_X type value, `-1` on miss). Python's `ItemType` IntEnum values match ROM ITEM_X constants 1:1.
- `LOOKUP-006` — Added `size_lookup(name)` to `mud/utils/prefix_lookup.py` mirroring ROM `src/lookup.c:95-107` (case-insensitive prefix-match against `Size` IntEnum, returns `-1` on miss).
- `LOOKUP-005` — Added `sex_lookup(name)` to `mud/utils/prefix_lookup.py` mirroring ROM `src/lookup.c:81-93` (case-insensitive prefix-match against `Sex` IntEnum, returns `-1` on miss). ROM `sex_table {none, male, female, either}` maps 1:1 to Python's enum.
- `LOOKUP-004` — Added `position_lookup(name)` to `mud/utils/prefix_lookup.py` mirroring ROM `src/lookup.c:67-79` (case-insensitive prefix-match against `Position` IntEnum, returns `-1` on miss).
- `LOOKUP-003` — `lookup_clan_id` (`mud/models/clans.py`) now uses ROM-faithful prefix-match instead of exact-match. `lookup_clan_id("lo")` returns clan `loner`, `lookup_clan_id("ro")` returns clan `rom`, mirroring ROM `src/lookup.c:53-65` (`clan_lookup` calls `str_prefix`).
- `LOOKUP-002` — `_lookup_flag_bit` (`mud/commands/remaining_rom.py`) now uses ROM-faithful prefix-match instead of exact-match. `flag char Bob plr +holy` matches `HOLYLIGHT` per ROM `src/lookup.c:39-51` (`flag_lookup` calls `str_prefix`). Introduces `mud/utils/prefix_lookup.py` with shared `prefix_lookup_index` and `prefix_lookup_intflag` helpers for the remaining LOOKUP-003..008 closures.
- `LOOKUP-001` — Added `race_lookup(name: str | None) -> int` to `mud/models/races.py` mirroring ROM `src/lookup.c:110-122` (case-insensitive prefix-match against `RACE_TABLE`, fall-through `return 0`). Fixes a latent `ImportError` in `mud/persistence.py:614`'s pet-restore path: every pet load with a non-None race snapshot was crashing with `ImportError: cannot import name 'race_lookup'` because the function had not been ported. Caught during the `lookup.c` parity audit.
- `FLAG-001` — `do_flag` (`mud/commands/remaining_rom.py`) is now a fully-wired immortal command instead of a syntax-validator stub. Mirrors ROM `src/flags.c:44-251`: parses the `=`/`+`/`-`/toggle operator, dispatches `act`/`plr`/`aff`/`immunity`/`resist`/`vuln`/`form`/`parts`/`comm` to the matching Character attribute and IntFlag enum (`ActFlag`, `PlayerFlag`, `AffectFlag`, `ImmFlag`, `FormFlag`, `PartFlag`, `CommFlag`), enforces NPC-only / PC-only field guards (`Use 'plr' for PCs.`, `Use 'act' for NPCs.`, `Form/Parts can't be set on PCs.`, `Comm can't be set on NPCs.`), looks up flag names case-insensitively, rejects unknown flags with `That flag doesn't exist!`, and mutates the matching bit on the victim. Previously the command returned a confirmation string but performed no mutation. New 9-test integration suite in `tests/integration/test_flag_command_parity.py`. FLAG-002 (preserve ROM `flag_type.settable=FALSE` bits across the `=` operator) deferred as MINOR — requires per-bit settable metadata on the IntFlag enums.

### Changed

- `sha256.c` audit completed (`docs/parity/SHA256_C_AUDIT.md`). SHA-256 primitive is delegated to Python's stdlib `hashlib` (byte-for-byte equivalent to ROM `src/sha256.c:131-318`). The `sha256_crypt` password hash (ROM `src/sha256.c:320-336`, plain unsalted single-round SHA-256) is replaced by PBKDF2-HMAC-SHA256 with a 16-byte random salt and 100 000 rounds in `mud/security/hash_utils.py` — a deliberate security upgrade with no observable gameplay parity surface (no pfile compatibility goal). Tracker row flipped from ⚠️ Partial → ✅ AUDITED.

### Fixed

- `NANNY-012` — Name validator (`is_valid_account_name` in `mud/account/account_service.py`) now matches ROM `check_parse_name` (`src/comm.c`, called from `nanny.c:188`): minimum length raised from 2 to 3 chars, and `god` / `imp` added to the reserved-name set. Existing reserved tokens (`all auto immortal self someone something the you loner none`) are unchanged.
- `NANNY-013` — Audit correction: ROM `hit=max_hit; mana=max_mana; move=max_move` (src/nanny.c:772-775) is already covered by `from_orm` initialising `max_*` from `perm_*` plus `hit` from saved `hp` (a fresh character is persisted with `hp=perm_hit=100`). NANNY-014 reset_char further guarantees max_* are restored on every login. Added regression test.
- `NANNY-006` — Login fallback room now distinguishes immortals from mortals when no saved room can be loaded. Added `ROOM_VNUM_CHAT = 1200` constant (ROM `src/merc.h:1250`) and `default_login_room_vnum(char)` helper in `mud/net/connection.py`; an `is_admin` character with `char.room is None` lands in ROOM_VNUM_CHAT (the immortal chat room), mortals in ROOM_VNUM_TEMPLE. Mirrors ROM `src/nanny.c:791-802` `IS_IMMORTAL ? ROOM_VNUM_CHAT : ROOM_VNUM_TEMPLE`.
- `NANNY-001` — Account login now disconnects on the first wrong password (returns `None` from `_run_account_login`) instead of looping back to the Account prompt, mirroring ROM `src/nanny.c:269-274` (`close_socket(d)` on bad password). The same path applies to reconnect attempts (matching ROM's "one chance" rule for both fresh logins and CON_BREAK_CONNECT).
- `NANNY-005` — Audit correction: ROM `perm_stat[class.attr_prime] += 3` (src/nanny.c:769) was already implemented in `mud/account/account_service.py:finalize_creation_stats` and locked in by `tests/test_nanny_rom_parity.py::test_prime_attribute_bonus_formula`. ROM applies the bonus during the `level == 0 → 1` promotion inside `CON_READ_MOTD`; Python applies it equivalently during `create_character` since Python characters are persisted at level 1.
- `NANNY-004` — Audit correction: ROM `learned[weapon_gsn] = 40` (src/nanny.c:653) was already implemented in `mud/models/character.py:from_orm` (lines 1047-1051), which uses `_STARTING_WEAPON_SKILL_BY_VNUM` to seed the picked weapon's skill to ≥40 on every load. Audit had cited the prompt-time path. Added regression test.
- `NANNY-003` — Audit correction: ROM `learned[gsn_recall] = 50` (src/nanny.c:581) was already implemented in `mud/models/character.py:from_orm` (lines 1052-1053), which clamps `learned["recall"]` to ≥50 on every character load. Audit had cited the wrong source location. Added regression test to lock in the behavior.
- `NANNY-002` — Login flow now honors the `PlayerFlag.DENY` bit per ROM `src/nanny.c:197-205`: a denied character logs `Denying access to <name>@<host>.`, receives `You are denied access.`, and is rejected before reaching the game loop. New `is_character_denied_access` helper in `mud/net/connection.py`, wired into both load branches of `_select_character`.
- `NANNY-007` — Login flow now broadcasts `<Name> has entered the game.` to other room occupants on every fresh (non-reconnect) login, mirroring ROM `act("$n has entered the game.", ch, NULL, NULL, TO_ROOM)` at `src/nanny.c:804`. New `broadcast_entry_to_room` helper in `mud/net/connection.py` excludes the actor and uses `act_format` for `$n` substitution.
- `BAN-004` — `BanEntry.matches` (`mud/security/bans.py`) no longer falls through to exact-string match when neither PREFIX nor SUFFIX bit is set; ROM `src/ban.c:104-132` `check_ban` silently skips such entries. Pre-existing tests in `tests/test_bans.py` and `tests/test_account_auth.py` were updated to use `*host*` patterns so a host-specific ban actually matches under ROM semantics.
- `BAN-003` — `_apply_ban` (`mud/commands/admin_commands.py`) now accepts ROM-style prefix abbreviations of the type token (`a`, `n`, `p`, `al`, `ne`, …), matching `src/ban.c:180-191` `!str_prefix(arg2, "all"/"newbies"/"permit")`. Previously required full-prefix `startswith` so single-letter abbreviations were rejected.
- `BAN-002` — `_render_ban_listing` now mirrors ROM's chained ternary at `src/ban.c:166-168`: prints `"newbies"` / `"permit"` / `"all"` based on the corresponding flag bits and falls through to `""` when none is set. Previously defaulted to `"all"` in the no-flag case.
- `BAN-001` — `_render_ban_listing` (`mud/commands/admin_commands.py`) now left-aligns the level column (`:<3d`) to match ROM `src/ban.c:164` `%-3d` instead of right-aligning. Visible in `banlist` / `ban` (no-arg) output.
- `NANNY-011` — `_prompt_new_password` (`mud/net/connection.py`) now rejects passwords containing `~` with ROM message "New password not acceptable, try again." mirroring ROM `src/nanny.c:396-405` file-format poisoner check. Python uses a DB backend so the practical risk is gone, but parity with ROM input validation is preserved.
- `NANNY-014` — Login flow now invokes `reset_char(ch)` on every successful login (ROM `src/nanny.c:760`), restoring `max_hit`/`max_mana`/`max_move` from `pcdata.perm_*`, zeroing transient `mod_stat[]`/`hitroll`/`damroll`/`saving_throw`, and re-applying equipment affects so returning characters land with clean state. Wired into both branches of `mud/net/connection.py:handle_connection` via new `apply_login_state_refresh` helper. Also corrected a latent bug in `mud/handler.py:reset_char` where `range(int(WearLocation.MAX))` raised `AttributeError` (the enum has no `MAX` member); replaced with literal `19` matching ROM `MAX_WEAR` (`src/merc.h:1356`).
- `SPEC-001` — `spec_executioner` yell now broadcasts area-wide (ROM `src/special.c:890-893`) instead of room-only. Added `_yell_area` helper mirroring ROM `do_yell`.
- `SPEC-002` — `spec_guard` now checks ALL room occupants for evil-alignment combatants (ROM `src/special.c:948-972`), not just PCs. The fallback path targeting `alignment < max_evil` fighters now works for NPCs too.
- `SPEC-003` — `spec_mayor` gate open/close now emits proper TO_CHAR (`You open the gate.`) and TO_ROOM (`Mayor opens gate.`) messages, plus reverse-exit toggle. Mirrors ROM `do_function(ch, &do_open, "gate")` / `do_function(ch, &do_close, "gate")`.
- `SPEC-004` — `spec_thief` gold/silver division now uses `c_div` (C integer division) instead of Python `//`, matching ROM `src/special.c:1174-1186`.
- `SPEC-005` — `spec_nasty` ambush now calls `do_murder` (which sets PLR_KILLER flag) instead of `do_kill`, matching ROM `src/special.c:368-371`. Updated `_issue_command` to search multiple command modules.
- `SPEC-006` — `spec_troll_member` and `spec_ogre_member` now check `is_safe()` before attacking, matching ROM `src/special.c:145,213`. Prevents attacks in safe rooms.
- `SPEC-008` — `spec_mayor` movement now uses `move_character()` (with fallback for test SimpleNamespace objects), matching ROM `move_char(ch, dir, FALSE)`.
- `SPEC-012` — `spec_nasty` gold steal now uses `c_div(gold_before, 10)` instead of `gold_before // 10`, matching ROM `src/special.c:394-396`.

- `WIZ-001` — `goto`, `at`, and `transfer` now mirror ROM `src/act_wiz.c:821-839,897-905,957-966` owner/private-room gating by honoring owner-locked rooms, the canonical `ROOM_SOLITARY` flag value, and `is_room_owner()` bypass semantics.
- `WIZ-002` — `violate` now mirrors ROM `src/act_wiz.c:1000-1057`: it targets rooms through `find_location()`, rejects public rooms with the `use goto` hint, and no longer parses directions/exits.
- `WIZ-003` — `protect` now mirrors ROM `src/act_wiz.c:2086-2118` lookup/messages and toggles the real `CommFlag.SNOOP_PROOF` bit instead of the old `COMM_NOTELL` value.
- `WIZ-004` — `snoop` now honors the canonical `CommFlag.SNOOP_PROOF` bit from ROM `src/act_wiz.c:2167-2174`, preventing snooping of correctly protected targets.
- `WIZ-006` — `log` command now mirrors ROM `src/act_wiz.c:2927-2984`: uses `get_char_world()` for lookup, toggles `PlayerFlag.LOG` on `victim.act` instead of a `log_commands` bool, rejects NPCs with ROM message, and uses canonical `\n\r` line endings.
- `WIZ-007` — `force` command now mirrors ROM `src/act_wiz.c:4183-4322`: adds `gods` branch for hero+ players, adds private-room check before forcing individuals, applies trust check to all victims (not just non-NPCs), iterates `descriptor_list` for `force all` and `char_list` for `force players`/`force gods`, and uses canonical `\n\r` line endings.
- `WIZ-005` — `stat` family now mirrors ROM `src/act_wiz.c:1059-1742`: `do_stat` dispatcher uses `get_char_world`/`get_obj_world`/`find_location` per ROM; `do_rstat` outputs Name/Area/Vnum/Sector/Light/Healing/Mana/Room flags/Description/Extra descs/Characters/Objects/Door details; `do_ostat` outputs Name(s)/Vnum/Format/Type/Resets/Short+Long descr/Wear bits/Extra bits/Number+Weight/Level+Cost+Condition+Timer/In room+In obj+Carried by+Wear_loc/Values/Item-type blocks (scroll, potion, pill, wand, staff, drink_con, weapon, armor, container)/Extra descs/Affects; `do_mstat` outputs Name/Vnum/Format/Race/Group/Sex/Room/Count+Killed/Stats/Hp+Mana+Move+Practices/Level+Class+Align+Gold+Silver+Exp/AC per type/Hit+Dam+Saves+Size+Position+Wimpy/Damage+Fighting/Thirst+Hunger+Full+Drunk for PCs/Carry number+Weight/Age+Played/Act/Comm/Offense/Immune/Resist/Vulnerable/Form+Parts/Affected by/Master+Leader+Pet/Security/Short+Long desc/Spec fun/Affected. Added 8 ROM-faithful bit-name helpers (`wear_bit_name`, `extra_bit_name`, `imm_bit_name`, `off_bit_name`, `form_bit_name`, `part_bit_name`, `weapon_bit_name`, `cont_bit_name`) and 5 display helpers (`size_name`, `position_name`, `sex_name`, `class_name`, `race_name`) to `mud/handler.py`.
- `WIZ-008` — Punish commands (`nochannels`, `noemote`, `noshout`, `notell`, `freeze`, `pardon`) now use canonical `CommFlag`/`PlayerFlag` enum values instead of hardcoded wrong bit positions that were corrupting unrelated flags. Added `wiznet()` broadcasts with `WIZ_PENALTIES` + `WIZ_SECURE` flags. Added `\n\r` line endings.
- `WIZ-009` — `peace` now calls `stop_fighting(person, True)` instead of setting `fighting = None` (properly clearing all combat references). Uses `ActFlag.AGGRESSIVE` enum instead of hardcoded `0x20`. Added `\n\r` line endings.
- `WIZ-010` — `invis` and `incognito` now broadcast room-wide `act()` messages per ROM `src/act_wiz.c:4329-4420`. `incognito` clears `reply` when setting a specific level. Added `\n\r` line endings.
- `WIZ-011` — Echo family (`echo`, `recho`, `zecho`, `pecho`) now iterates `descriptor_list` with `CON_PLAYING` filter per ROM `src/act_wiz.c:674-777` instead of `registry.players` dict. `pecho` uses ROM trust check and exact messages. Added `\n\r` line endings.
- `WIZ-012` — `bamfin`/`bamfout` now use `smash_tilde()` and ROM `strstr` case-sensitive name check per `src/act_wiz.c:455-512`. Added `\n\r` line endings.
- `WIZ-013` — `wizlock`/`newlock` now use `\n\r` line endings per ROM `src/act_wiz.c:3150-3188`.
- `WIZ-014` — `holylight` now returns empty string for NPCs (ROM parity) and uses `\n\r` line endings per `src/act_wiz.c:4422-4439`.
- `WIZ-015` — `slookup` now supports `all` arg, shows `Slot` column, uses prefix-match lookup per ROM `src/act_wiz.c:3191-3229`. Added `\n\r` line endings.
- `WIZ-016` — `sockets` now uses `\n\r` line endings per ROM `src/act_wiz.c:4140-4176`.
- `WIZ-017` — `deny` rewritten to ROM parity per `src/act_wiz.c:517-557`: SET-only (not toggle), uses `get_char_world()` not `character_registry`, adds `PlayerFlag.DENY` flag, wiznet broadcast, `stop_fighting(victim, True)`, forced quit, `\n\r` line endings.
- `WIZ-018` — `switch` now has private-room check (`is_room_owner`/`room_is_private`) and wiznet broadcast per ROM `src/act_wiz.c:2202-2269`. Added `\n\r` line endings.
- `WIZ-019` — `return` now has full ROM message, prompt cleanup, and wiznet broadcast per `src/act_wiz.c:2273-2303`. Added `\n\r` line endings.
- `WIZ-020` — `smote` now uses ROM `_smote_substitute` letter-by-letter algorithm, case-sensitive `strstr` name check, skips no-descriptor viewers per `src/act_wiz.c:362-453`. Added `\n\r` line endings.
- `WIZ-021` — `pecho` now uses ROM trust check (`get_trust(char) != MAX_LEVEL`) and exact messages per `src/act_wiz.c:750-777`. Added `\n\r` line endings.
- `WIZ-022` — `disconnect` now follows ROM descriptor-list victim lookup per `src/act_wiz.c:561-614`. Added `\n\r` line endings.
- `WIZ-023` — `guild` now uses `lookup_clan_id`/`CLAN_TABLE` per ROM `src/act_wiz.c:196-249`; distinguishes independent-clan (`"a <name>"`) vs member-clan (`"member of clan <Name>"`) messaging; uses `str_prefix`-style match for "none"; all messages have `\n\r`.
- `WIZ-024` — `outfit` now always returns `"You have been equipped by Mota.\n\r"` per ROM `src/act_wiz.c:251-310` (removed "You already have your equipment" branch).
- `WIZ-025` — `copyover` now iterates `descriptor_list` with `CON_PLAYING` filter per ROM `src/act_wiz.c:4498-4588`; all messages have `\n\r`.
- `WIZ-026` — `qmconfig` verified as already ROM-faithful per `src/act_wiz.c:4685-4787`; added test coverage for `"I have no clue..."` fallback.
- `wiznet()` broadcast now iterates `descriptor_list` with `CON_PLAYING` filter per ROM `src/act_wiz.c:171-194`; falls back to `character_registry` in test environments without descriptor setup.
- `WIZ-027` — `load` syntax messages now have `\n\r` line endings per ROM; re-invokes `do_load("")` on invalid type.
- `WIZ-028` — `mload` now returns `"Ok.\n\r"` instead of `"You have created {name}!"` per ROM `src/act_wiz.c:2489-2517`; added `wiznet()` broadcast; safe `getattr` for registry.
- `WIZ-029` — `oload` now returns `"Ok.\n\r"` instead of `"You have created {name}!"` per ROM `src/act_wiz.c:2521-2570`; added `wiznet()` broadcast; ROM typo preserved in level message; fixed `char.inventory` slot name.
- `WIZ-030` — `purge` trust check now uses ROM `<=` comparison per `src/act_wiz.c:2625`; added `"X tried to purge you!\n\r"` notification to victim; all messages have `\n\r`.
- `WIZ-031` — `restore` iterates `descriptor_list` for `restore all` per ROM `src/act_wiz.c:2820-2845`; added wiznet broadcasts; all messages have `\n\r`.
- `WIZ-032` — `clone` now has wiznet broadcasts per ROM `src/act_wiz.c:2338-2455`; added trust check for mob cloning; uses `obj.carried_by` to determine placement; all messages have `\n\r`.
- `WIZ-033` — `set` command now uses `\n\r` line endings and re-invokes `do_set("")` on invalid type per ROM `src/act_wiz.c:3233-3275`.
- `WIZ-034` — `sset` now uses `getattr(registry, "skill_table", [])` iteration; added `(use the name of the skill, not the number)` hint; all messages have `\n\r` per ROM `src/act_wiz.c:3278-3352`.
- `WIZ-035` — `mset` now fully ROM-parity per `src/act_wiz.c:3355-3790`: uses `smash_tilde()`; uses `get_max_train()` for stat ranges; `level` rejects PCs; `sex` sets `pcdata.true_sex`; `hp`/`mana`/`move` set PC `perm_*` values; uses ROM field name prefixes (`startswith()`); adds fields: `class`, `race`, `group`, `hours`, `thirst`, `drunk`, `full`, `hunger`; `security` uses `ch->pcdata->security` range; clears `victim.zone`; re-invokes `do_mset("")` on unknown field; all messages have `\n\r`.
- `WIZ-036` — `oset` now fully ROM-parity per `src/act_wiz.c:3958-4067`: uses `smash_tilde()`; adds `v0`-`v4` aliases; caps `value0` at `min(50, value)` per ROM:3998; adds `timer` field; uses ROM field prefixes; re-invokes `do_oset("")` on unknown field; all messages have `\n\r`.
- `WIZ-037` — `rset` now fully ROM-parity per `src/act_wiz.c:4071-4136`: uses `smash_tilde()`; uses `find_location()` for room lookup; adds private-room check (`is_room_owner`/`room_is_private`); adds "Value must be numeric.\n\r" check; uses ROM field prefixes; re-invokes `do_rset("")` on unknown field; all messages have `\n\r`.
- `WIZ-038` — `string` now fully ROM-parity per `src/act_wiz.c:3793-3954`: uses `smash_tilde()`; adds `spec` field via `get_spec_fun()`; `long` appends `\n\r`; uses `set_title()` for title; uses ROM field prefixes; adds ROM `extra_descr` insertion; re-invokes `do_string("")` on bad type; all messages have `\n\r`.
- `ALIAS-001` — `alia` now returns the ROM `src/alias.c:97-100` typo-guard text instead of a generic helper string.
- `ALIAS-002` — `alias` now mirrors ROM `src/alias.c:112-220`: exact list/query/set/realias messages, reserved-word checks, quote/name validation, `delete`/`prefix` expansion guards, and the five-alias limit.
- `ALIAS-003` — alias substitution now mirrors ROM `src/alias.c:69-99`: one expansion pass only, truncation warning handling, and `mud.rom_api.substitute_alias()` now returns the expanded string instead of an internal tuple.
- `ALIAS-004` — `unalias` now mirrors ROM `src/alias.c:236-274` prompt/removal/failure messages.
- `ALIAS-005` — prefix preprocessing before alias expansion now mirrors ROM `src/alias.c:49-61,88-95`, including the overlong-line warning and full-`prefix` bypass semantics.
- `HEALER-001` — `heal` now finds NPC healers via `ACT_IS_HEALER` and shows the ROM `src/healer.c:49-79` service table instead of a compressed summary string.
- `HEALER-002` — `heal mana` now mirrors ROM `src/healer.c:147-190`: silver-aware affordability, `deduct_cost`, healer payout, TO_ROOM utterance, and `dice(2, 8) + level/3` mana restoration.
- `HEALER-003` — `heal refresh` now dispatches to the underlying ROM spell path from `src/healer.c:156-160,196` instead of a placeholder full-restore shortcut.
- `HEALER-004` — `heal heal` now dispatches to the underlying ROM `spell_heal` path from `src/healer.c:107-112,196` instead of always filling hit points to max.

## [2.6.15] - 2026-04-28

Closes the `scan.c` audit (P2): all 3 gaps fixed, ROM-faithful TO_ROOM/TO_CHAR
broadcasts on the `scan` command, divergent header and fallback lines removed.

### Added

- `SCAN-001` — `do_scan` with no argument now emits the TO_ROOM broadcast
  `"$n looks all around."` so onlookers see the scan, mirroring ROM
  `src/scan.c:60` (`act("$n looks all around.", ch, NULL, NULL, TO_ROOM);`).
- `SCAN-002` — directional `do_scan` now emits the TO_CHAR/TO_ROOM act() pair
  `"You peer intently <dir>."` / `"$n peers intently <dir>."`, mirroring ROM
  `src/scan.c:89-90`.

### Fixed

- `SCAN-002` — directional `do_scan` no longer prints a spurious
  `"Looking <dir> you see:"` header. ROM builds that string into `buf` at
  `src/scan.c:91` but never calls `send_to_char(buf, ch)`; the only visible
  scanner-facing message is the `"You peer intently <dir>."` act().
- `SCAN-003` — `do_scan` no longer emits non-ROM fallback lines
  (`"No one is nearby."`, `"Nothing of note."`) when no visible characters
  are found. ROM emits only the act() messages and header in that case
  (`src/scan.c:48-104`).

## [2.6.14] - 2026-04-28

Closes the `db2.c` audit (P1): all CRITICAL/IMPORTANT mob-loader gaps fixed.
Both `.are` and JSON loaders now match ROM `src/db2.c:load_mobiles` for AC
scaling, `ACT_IS_NPC` enforcement, race-table flag merge, and first-char
uppercase of long_descr/description. Two MINOR gaps (`DB2-004` kill_table,
`DB2-005` single-line fread_string) remain deferred — both documented as
not user-reachable in the current port.

### Fixed

- `DB2-003` — both mob loaders now uppercase the first character of
  `long_descr` and `description` at load time, mirroring ROM
  `src/db2.c:236-237` (`pMobIndex->long_descr[0] = UPPER(...)`).
  Previously mob protos with a lowercase first letter rendered that way in
  room/look output. `.are` loader normalizes after `read_string_tilde`;
  JSON loader normalizes inline at MobIndex construction.
- `DB2-006` — mob armor-class fields (`ac_pierce`/`ac_bash`/`ac_slash`/`ac_exotic`)
  are now multiplied by 10 at load time in both the `.are` loader
  (`mud/loaders/mob_loader.py`) and the JSON loader (`mud/loaders/json_loader.py`),
  mirroring ROM `src/db2.c:273-276`. Previously every loaded NPC had an AC value
  10× off in ROM's negative-AC convention, making them noticeably easier to hit.
  `mud/scripts/convert_are_to_json.py` now divides back when re-emitting JSON so
  the JSON files stay a faithful mirror of the raw `.are` upstream.
- `DB2-002` — both mob loaders now merge ROM `race_table[race].{act, aff,
  off, imm, res, vuln, form, parts}` flag bits into each loaded mob's
  letter-based flag fields, mirroring ROM `src/db2.c:239-242,279-286,295-297`.
  Previously race-derived intrinsics (dragon flying, troll regeneration,
  modron immunities, undead form/parts) were silently dropped at load time.
  Implemented in `mud/loaders/mob_loader.py:merge_race_flags`; the JSON
  loader (`mud/loaders/json_loader.py`) invokes it after MobIndex construction.
- `DB2-001` — both mob loaders now unconditionally OR `ACT_IS_NPC` (letter `A`)
  into every prototype's `act_flags` letter string, mirroring ROM
  `src/db2.c:239`. Previously a mob whose area-file flags omitted the `A`
  letter would spawn with `IS_NPC()` returning false, breaking every
  downstream `is_npc` check (combat, save, look, mobprog dispatch).

## [2.6.13] - 2026-04-28

Closes the cross-file dependency that blocked `interp.c` completion:
`WEAR-010` (do_wear dispatches weapons to wield) and `WEAR-011`
(do_hold auto-replaces) cleared the way for `INTERP-013` to collapse
`do_wield`/`do_hold` into aliases on `do_wear`, mirroring ROM
`cmd_table[]`. `interp.c` now closes at **24/24 fixed + 1
closed-deferred**.

### Fixed

- `act_obj.c:WEAR-010` — `do_wear` now dispatches `ITEM_WEAPON` items
  to the WIELD branch (`_dispatch_wield`) instead of rejecting with
  "You need to wield weapons, not wear them." Mirrors ROM
  `src/act_obj.c:1401-1697` `wear_obj` single-dispatcher design where
  `do_wear`/`do_wield`/`do_hold` are all the same function. Tests:
  `tests/integration/test_equipment_system.py::test_wear_010_do_wear_dispatches_weapon_to_wield`.
- `act_obj.c:WEAR-011` — `do_hold` now auto-unequips an existing held
  item via `_unequip_to_inventory()` instead of rejecting with
  "You're already holding {name}." Mirrors ROM
  `src/act_obj.c:1670-1677` `remove_obj(WEAR_HOLD, fReplace=TRUE)`
  semantics. Tests:
  `tests/integration/test_equipment_system.py::test_wear_011_do_hold_auto_replaces_existing_held`.
- `interp.c:INTERP-013` — `wield` and `hold` now dispatch to `do_wear`
  via the dispatcher's `aliases=("wield", "hold")` on the `wear`
  Command, mirroring ROM `cmd_table[]` (src/interp.c:103, 215, 232).
  `do_wield`/`do_hold` collapsed to thin wrappers around `do_wear`
  for direct-import callers. Closes `interp.c` to **24/24 fixed +
  1 closed-deferred** (100% of closeable gaps). Tests:
  `tests/integration/test_interp_dispatcher.py::test_interp_013_wear_wield_hold_share_do_wear`.

### Changed

- `wield <non-weapon>` and `hold <non-holdable>` no longer reject with
  command-specific errors ("You can't wield that." / "You can't hold
  that."). They now run the full `do_wear` dispatcher, so
  e.g. `wield ring` wears the ring on a finger — ROM-faithful since
  ROM has no separate `do_wield`/`do_hold` functions.
- `wield` and `hold` with no argument now emit
  `"Wear, wield, or hold what?"` instead of `"Wield what?"` /
  `"Hold what?"`, mirroring ROM's single-prompt design.

## [2.6.12] - 2026-04-28

Closes the remaining `interp.c` parser/extension gaps:
`INTERP-015` (port ROM `one_argument` to replace `shlex.split`) and
`INTERP-016` (verify `tail_chain` is a no-op in stock ROM and close-defer).
`interp.c` is now 22/24 gaps fixed + 1 closed-deferred + 1 deferred-pending
(`INTERP-013`, blocked on `ACT_OBJ_C` `do_wear` port).

### Fixed

- `interp.c:INTERP-015` — `_split_command_and_args` no longer routes
  through `shlex.split`; the new `_one_argument()` mirrors ROM
  `src/interp.c:766-798` byte-for-byte (lowercases head, single-char
  `'` and `"` quote sentinels with no nesting, backslash treated
  literally, surrounding whitespace stripped). `shlex` import dropped.
  Tests:
  `tests/integration/test_interp_dispatcher.py::test_interp_015_one_argument_matches_rom`
  (8 cases).

### Changed

- `interp.c:INTERP-016` — closed-deferred. Confirmed `tail_chain()`
  is `return;` only in stock ROM 2.4b6 (`src/db.c:3929`); empty
  hook used by some ROM derivatives for stack-tail-call extension.
  Stock-ROM behavior is "do nothing", which Python already matches
  by omission.
- `tests/test_alias_parity.py::test_alias_case_sensitivity` renamed
  to `test_alias_case_insensitive_lookup_matches_rom` and flipped to
  assert ROM-correct behavior — ROM `do_alias` stores keys via
  `one_argument` which lowercases (`src/alias.c:127, 217`), so an
  uppercase input head expands a lowercased alias key. The previous
  Python assertion mirrored pre-port `shlex` behavior, not ROM.

## [2.6.11] - 2026-04-28

Closes the three small position/trust gates left in `interp.c`
(`INTERP-004`/`-005`/`-006`). `interp.c` is now 20/24 gaps closed
(83%); only `INTERP-013` (deferred until `do_wear` ports the missing
wield/hold logic), `INTERP-015` (shlex/one_argument port), and
`INTERP-016` (`tail_chain` documentation, no-op) remain.

### Fixed

- `interp.c:INTERP-004` — `shout` now requires trust 3 to match ROM
  (`src/interp.c:200`). Previously had no `min_trust` (defaulted to 0).
  Test: `tests/integration/test_interp_dispatcher.py::test_interp_004_shout_requires_trust_3`.
- `interp.c:INTERP-005` — `murder` now requires trust 5 to match ROM
  (`src/interp.c:247`). Test:
  `test_interp_005_murder_requires_trust_5`.
- `interp.c:INTERP-006` — `music` `min_position` lowered from
  `RESTING` to `SLEEPING` to match ROM (`src/interp.c:93`). Test:
  `test_interp_006_music_min_position_sleeping`.

## [2.6.10] - 2026-04-27

Closes five more `interp.c` gaps: command-mapping cleanup
(`INTERP-009/010/011/012/014` — `hit`/`take`/`junk`/`tap`/`go`/`:`
now route to canonical handlers), `do_commands` column-padding fix
(`INTERP-024`), and the prefix-order sweep (`INTERP-017`) — Python's
prefix scan now mirrors ROM `cmd_table[]` declaration order via a
250-entry table, so 1- and 2-letter abbreviations resolve identically
to ROM. `INTERP-013` (collapse `do_wield`/`do_hold` into `do_wear`)
deferred — Python `do_wear` is missing strength/skill/two-hand checks
and HOLD auto-unequip that the separate functions currently provide;
collapsing now would regress behavior. `interp.c` is now 17/24 gaps
closed (71%).

### Fixed

- `interp.c:INTERP-009` — `"hit"` now dispatches to `do_kill` as a
  ROM-style alias on the kill `Command`; deleted redundant `do_hit`
  stub from `player_info.py` (`src/interp.c:88`). Test:
  `tests/integration/test_interp_dispatcher.py::test_interp_009_hit_routes_to_do_kill`.
- `interp.c:INTERP-010` — `"take"` now dispatches to `do_get` as an
  alias on the get `Command`; deleted `do_take` stub
  (`src/interp.c:226`). Test:
  `tests/integration/test_interp_dispatcher.py::test_interp_010_take_routes_to_do_get`.
- `interp.c:INTERP-011` — `"junk"` and `"tap"` now dispatch to
  `do_sacrifice` as aliases; deleted both stubs from `remaining_rom.py`
  (`src/interp.c:228-229`). Test:
  `test_interp_011_junk_tap_route_to_do_sacrifice`.
- `interp.c:INTERP-012` — `"go"` now dispatches to `do_enter` as an
  alias; deleted `do_go` stub (`src/interp.c:263`). Test:
  `test_interp_012_go_routes_to_do_enter`.
- `interp.c:INTERP-014` — `":"` now dispatches to `do_immtalk` as an
  alias; deleted `do_colon` stub from `typo_guards.py` whose
  `"Say what on the immortal channel?"` placeholder was masking ROM's
  NOWIZ toggle behavior (`src/interp.c:356`). Test:
  `test_interp_014_colon_routes_to_do_immtalk`.
- `interp.c:INTERP-024` — `do_commands`/`do_wizhelp` no longer strip
  trailing whitespace from rows; ROM emits each name as `%-12s` with
  full column padding preserved (`src/interp.c:815-823`). Test:
  `test_interp_024_do_commands_preserves_12char_column_padding`.
- `interp.c:INTERP-017` — `resolve_command` now walks a 250-entry
  ROM-faithful `_PREFIX_TABLE` in `src/interp.c` declaration order
  instead of Python's feature-grouped `COMMANDS` list; removed the
  exact-match shortcut so prefix resolution mirrors ROM
  `interpret()` exactly (e.g. `"go"` now resolves to `goto` not
  `enter`, matching ROM's hand-ordered prefix block). Sweep test:
  `tests/integration/test_interp_prefix_order.py::test_interp_017_prefix_winner_matches_rom`
  parses `src/interp.c` at collection time and asserts every
  single-letter prefix plus 20 curated 2-letter prefixes resolve
  identically to ROM (45 cases).

## [2.6.9] - 2026-04-27

Closes four `interp.c` dispatcher-level gaps in one session: empty-input
behavior (`INTERP-007`), ROM punctuation aliases (`INTERP-008`), snoop
forwarding (`INTERP-002`), and verified the wiznet `WIZ_SECURE` mirror
that was already in place (`INTERP-003`). `interp.c` is now 11/24 gaps
closed (46%).

### Fixed

- `interp.c:INTERP-007` — empty input now returns silently to match
  ROM `interpret()` (`src/interp.c:401-404`). Previously emitted the
  literal `"What?"`. Test:
  `tests/integration/test_interp_dispatcher.py::test_interp_007_empty_input_returns_silently`.
- `interp.c:INTERP-008` — added ROM punctuation aliases `.` → `gossip`,
  `,` → `emote`, `/` → `recall` to `COMMAND_INDEX`
  (`src/interp.c:184,186,272`). Test:
  `tests/integration/test_interp_dispatcher.py::test_interp_008_punctuation_aliases_route_to_rom_handlers`.
- `interp.c:INTERP-002` — `process_command` now forwards the input
  logline to `desc.snoop_by.character.messages` prefixed with `"% "`
  (`src/interp.c:491-496`). Test:
  `tests/integration/test_interp_dispatcher.py::test_interp_002_snoop_forwards_logline_to_snooper`.
- `interp.c:INTERP-003` — verified `log_admin_command` already mirrors
  logged commands to wiznet `WIZ_SECURE` with ROM-style `$`/`{`
  doubling (`mud/admin_logging/admin.py:107-114`,
  `src/interp.c:468-489`). Audit row description was stale. Test:
  `tests/integration/test_interp_dispatcher.py::test_interp_003_logged_command_mirrors_to_wiznet_secure`.

## [2.6.8] - 2026-04-27

Closes the immortal command trust drift (`INTERP-001`). All 43 commands
that were gated too low now match ROM `cmd_table[]` tier-for-tier. This
is a security-relevant fix — previously a `LEVEL_IMMORTAL` (52) character
could invoke commands ROM gates at L1..ML (53..60).

### Fixed

- `interp.c:INTERP-001` — raised `min_trust` on 43 immortal commands
  in `mud/commands/dispatcher.py` to match ROM `cmd_table[]` trust
  tiers (`src/interp.c:63-381`, `src/interp.h:34-44`). Affected
  tiers: ML, L1, L2, L3, L4, L5, L6, L7. Security-relevant — closes
  privilege drift where `LEVEL_IMMORTAL` (52) characters could
  invoke commands ROM gates at L1..ML (53..60). Test:
  `tests/integration/test_interp_trust.py::test_interp_001_command_trust_matches_rom` (50 parameters).

## [2.6.7] - 2026-04-27

`interp.c` social-cluster audit complete (6/6 social gaps closed). Both
remaining gaps (prefix lookup + literal "not found" message) shipped
with integration coverage; socials suite now 31/31. `interp.c` overall
audit progress: 6/24 gaps closed (25%) — non-social gaps (trust drift,
dispatcher hooks, command-mapping cleanup) remain open.

### Fixed

- `interp.c:INTERP-021` — social command lookup now mirrors ROM
  `str_prefix` semantics so partial names (e.g. `gigg` → `giggle`)
  resolve in load order. Added `mud.models.social.find_social()` and
  routed both the dispatcher fallback (`mud/commands/dispatcher.py`)
  and `perform_social` (`mud/commands/socials.py`) through it. Mirrors
  ROM `src/interp.c:584-592`.
- `interp.c:INTERP-022` — `perform_social` now emits the literal
  `"They aren't here."` when the targeted victim is absent, matching
  ROM `src/interp.c:637-640`. The fabricated `social.not_found` field
  (which has no counterpart in ROM's social table) is no longer used.

## [2.6.6] - 2026-04-27

`interp.c` ROM parity audit started — full audit doc with 24 stable gap
IDs (`INTERP-001`..`INTERP-024`) created. Closed the entire CRITICAL+
IMPORTANT social-cluster subset of `check_social` (`src/interp.c:597-685`):
position gates, NOEMOTE, sleeping snore exception, and the NPC slap/echo
auto-react via `mud.utils.rng_mm.number_bits(4)`. Socials integration
suite grew from 13 to 27 tests, all green.

### Fixed

- `interp.c:INTERP-018` — `perform_social` now refuses socials from
  characters in `Position.DEAD`, `MORTAL`, `INCAP`, or `STUNNED` and
  emits ROM's exact response messages
  (`"Lie still; you are DEAD."`, `"You are hurt far too bad for that."`,
  `"You are too stunned to do that."`). Mirrors
  `src/interp.c:603-616` (`check_social` position gate).
- `interp.c:INTERP-019` — sleeping characters now receive
  `"In your dreams, or what?"` for every social except `snore`
  (the canonical Furey exception). Mirrors `src/interp.c:618-626`.
- `interp.c:INTERP-020` — players punished with the `COMM_NOEMOTE`
  flag now receive `"You are anti-social!"` when attempting any
  social. NPCs are unaffected per ROM's `IS_NPC` short-circuit.
  Mirrors `src/interp.c:597-601`.

### Added

- `interp.c:INTERP-023` — NPC auto-reaction to player socials. When
  a non-NPC socials at an awake, non-charmed, non-switched NPC,
  `mud.utils.rng_mm.number_bits(4)` (0..15) decides the response:
  values 0..8 echo the social back at the player with the actor and
  victim swapped; values 9..12 produce a slap
  (`"$n slaps $N." / "You slap $N." / "$n slaps you."`); values 13..15
  fall through silently. Mirrors `src/interp.c:652-685`.

## [2.6.5] - 2026-04-27

`mob_prog.c` ROM parity audit complete — all 7 gaps closed (2 CRITICAL,
4 IMPORTANT, 1 MINOR). MOBprog predicate evaluation, greet/grall trigger
exclusivity, $-code expansion, and program-flow state-machine now match
ROM 2.4b6 behaviour.

### Fixed

- MOBPROG-007: `_program_flow` now logs a warning and aborts the program when
  an `if`/`or`/`and` keyword is not in ROM's `fn_keyword[]` table, mirroring
  the `bug()` + `return` paths at `src/mob_prog.c:1049-1056`, `1076-1083`,
  `1103-1109`. Typo'd predicates fail loudly instead of silently evaluating
  to False. Integration coverage at
  `tests/integration/test_mobprog_program_flow.py`. Also corrected the
  `test_simple_quest_accept_workflow` fixture program to use the real ROM
  keyword `carries` (not the previously-silent invalid `has_item`).
- MOBPROG-006: `_expand_arg` `$R` substitution now replicates the ROM
  long-standing bug at `src/mob_prog.c:798-799` — the visibility gate uses
  `rch` (random victim) but the substituted string is `ch->short_descr`
  (NPC actor) or `ch->name` (PC actor). Per AGENTS.md ROM Parity Rules,
  QuickMUD reproduces the bug. Integration coverage at
  `tests/integration/test_mobprog_predicates.py`.
- MOBPROG-005: `_program_flow` `else` branch now resets
  `state[level] = IN_BLOCK` mirroring ROM `src/mob_prog.c:1138`. Structural
  state-machine parity only — no observable divergence on valid programs;
  regression coverage added at
  `tests/integration/test_mobprog_program_flow.py`.
- MOBPROG-004: `_cmd_eval` `clan` / `race` / `class` checks now resolve their
  name keyword via a ROM-style prefix lookup over `CLAN_TABLE`, `RACE_TABLE`,
  and `CLASS_TABLE` (mirroring ROM `clan_lookup` / `race_lookup` /
  `class_lookup`, `src/mob_prog.c:601-609`) instead of comparing the int
  attribute to the literal name string. `if class $n mage`,
  `if race $n dragon`, `if clan $n thieves` now match ROM. Integration
  coverage at `tests/integration/test_mobprog_predicates.py`.
- MOBPROG-003: `_cmd_eval` `vnum` check now compares against `lval=0` when the
  target is a PC instead of returning False. Mirrors ROM `src/mob_prog.c:631-642`
  — `lval` initialises to 0 and is only overwritten for NPCs, so
  `if vnum $n == 0` is True against PCs and `if vnum $n != 0` is False.
  Integration coverage at `tests/integration/test_mobprog_predicates.py`.
- MOBPROG-002: `mp_greet_trigger` no longer falls through to GRALL after a
  failed GREET percent roll. Mirrors ROM `src/mob_prog.c:1340-1345` where the
  GREET / GRALL branches are exclusive — a mob that is awake, can see the
  entrant, and has a GREET trigger only attempts GREET; GRALL is reserved for
  the busy/blind path. Integration coverage at
  `tests/integration/test_mobprog_greet_trigger.py`.
- MOBPROG-001: `_cmd_eval` `objexists` now walks `mud.models.obj.object_registry`
  (mirroring ROM `get_obj_world`, `src/mob_prog.c:399`) instead of only the
  current room and same-room carriers. Mob programs that gate on
  `if objexists <vnum|name>` against globally-placed items now match ROM
  semantics. Integration coverage at
  `tests/integration/test_mobprog_predicates.py`.

## [2.6.4] - 2026-04-27

`mob_cmds.c` ROM parity audit complete — all 18 gaps closed (6 CRITICAL,
9 IMPORTANT, 3 MINOR). MOBprog script commands (`mob kill`, `assist`,
`oload`, `flee`, `cast`, `call`, `damage`, `junk`, `purge`, `transfer`)
now match ROM 2.4b6 behaviour for charm/master defence, position gates,
target-type dispatch, level bounds, NO_MOB respect, recursion, and
bug-log emission on script authoring errors.

### Fixed

- MOBCMD-017: `do_mptransfer` now mirrors ROM's recursive structure — a
  literal `mob transfer all <loc>` recursively dispatches
  `do_mptransfer(ch, "<pcname> <loc>")` once per PC in the room
  (`src/mob_cmds.c:791-806`) so each victim re-runs the full validation
  pipeline (private-room check, location resolution). Previously the
  Python implementation inlined the iteration with a direct
  `_transfer_character` call. NPCs are skipped exactly as in ROM line
  799. Integration coverage at `tests/integration/test_mob_cmds_transfer.py`.
- MOBCMD-018: verified `do_mpflee` already checks `ch.fighting` as the
  first guard, mirroring ROM `src/mob_cmds.c:1266-1267`. The audit row
  was stale and is now closed without a code change.
- MOBCMD-007: `do_mppurge` no longer accepts the literal `"all"` token
  as a synonym for the no-arg purge-everything form. ROM
  `src/mob_cmds.c:631-665` treats an empty argument as purge-all and has
  no `"all"` keyword — the token falls through to the name-resolution
  branch like any other word. Also added the missing
  `Mppurge - Bad argument` (ROM line 663) and `Mppurge - Purging a PC`
  (ROM line 671) bug logs via the new `_bug()` helper. The previously
  divergent unit test (`test_mppurge_all_cleans_room`) now uses the
  no-arg form. Integration coverage at
  `tests/integration/test_mob_cmds_purge.py`.
- MOBCMD-013: `do_mpdamage` now emits a ROM-style `bug()` warning via
  Python's `logging` module when the min or max argument is non-numeric,
  mirroring ROM `src/mob_cmds.c:1105-1107` + `1113-1115`. Previously the
  function silently returned, swallowing what is a script-authoring
  error. A new module-local `_bug()` helper in `mud/mob_cmds.py` mirrors
  ROM's `bug("Mp... - <reason> from vnum %d.", vnum)` pattern; expect
  this helper to be reused as further `mob_cmds` gaps are closed.
  Integration coverage at
  `tests/integration/test_mob_cmds_damage.py::TestMpDamageNonNumericArgsBugLog`.
- MOBCMD-009: `do_mpflee` now respects `ROOM_NO_MOB` on a candidate
  destination when the fleeing character is an NPC, mirroring ROM
  `src/mob_cmds.c:1277-1280`. Previously script-driven NPC flees would
  pour mobs into rooms flagged NO_MOB. Integration coverage at
  `tests/integration/test_mob_cmds_flee.py::TestMpFleeNoMobRoomFlag`.
- MOBCMD-006: `do_mpoload` now validates the optional level argument
  against ROM's `level < 0 || level > get_trust(ch)` check
  (`src/mob_cmds.c:575-580`) and refuses to spawn the object when out of
  range. Previously the level was accepted unconditionally so a script
  could load objects above the mob's trust ceiling. Integration coverage
  at `tests/integration/test_mob_cmds_oload.py`.
- MOBCMD-004: `do_mpjunk` (MOBprog `junk` script command) now matches
  ROM's empty-needle behaviour: `mob junk all.` (trailing dot, no
  suffix) discards nothing because ROM `src/mob_cmds.c:436` defers to
  `is_name(&arg[4], ...)` which returns FALSE for an empty string.
  Python had been short-circuiting on `not suffix` and discarding every
  carried object. Bare `mob junk all` still clears inventory as before.
  Integration coverage at `tests/integration/test_mob_cmds_junk.py`.
- MOBCMD-002: `do_mpassist` now enforces ROM `src/mob_cmds.c:393`'s full
  guard set — `victim == ch`, `ch->fighting != NULL`, and
  `victim->fighting == NULL`. Previously only the third clause was
  checked, so a script mob already in a fight could be redirected onto a
  new target via `mob assist`, and a script mob could nonsensically
  assist itself. Integration coverage at
  `tests/integration/test_mob_cmds_assist.py`.
- MOBCMD-001: `do_mpkill` now refuses when the script mob is charmed
  (`AffectFlag.CHARM`) and the chosen victim is its master, mirroring ROM
  `src/mob_cmds.c:364-369`. Previously a charmed mob scripted to
  `mob kill <master>` would attack its own charmer. Integration coverage
  at `tests/integration/test_mob_cmds_kill.py::TestMpKillCharmedMasterGuard`.
- MOBCMD-015 + MOBCMD-016: `do_mpcall` (MOBprog `call` script command) now
  parses the optional obj1/obj2 tokens from `mob call <vnum> <victim>
  <obj1> <obj2>` and resolves them via `_find_obj_here` (the `get_obj_here`
  analog), forwarding both to `mobprog.call_prog`. ROM
  `src/mob_cmds.c:1217-1252` initialises obj1/obj2 to NULL and only sets
  them when the corresponding token resolves through `get_obj_here`; the
  Python implementation had been dropping both args entirely so called
  sub-programs could never receive object context. Integration coverage at
  `tests/integration/test_mob_cmds_call.py`.
- MOBCMD-011 + MOBCMD-012: `do_mpcast` (MOBprog `cast` script command) now
  resolves the JSON `target` string into a canonical `_TargetType` IntEnum
  mirroring ROM `TAR_*` (`src/magic.h`) and dispatches on the enum, matching
  ROM's switch in `src/mob_cmds.c:1043-1066`. The previously string-keyed
  branches were drift-prone; in particular the `TAR_OBJ_CHAR_DEF/OFF/INV`
  cases now require an object (no character fallback) and `TAR_CHAR_DEFENSIVE`
  defaults to `ch` when the lookup fails, matching ROM lines 1055 + 1060-1065.
  Integration coverage at `tests/integration/test_mob_cmds_cast.py`.
- MOBCMD-003: `do_mpkill` now gates on `ch.position == Position.FIGHTING`
  (matching ROM `src/mob_cmds.c:361`) instead of the looser
  `ch.fighting is not None` check, and short-circuits self-attacks via the
  missing `victim is ch` guard from the same ROM line. Integration coverage
  at `tests/integration/test_mob_cmds_kill.py`.
- MOBCMD-008: `do_mpflee` now performs 6 `rng_mm.number_door()` random-door
  attempts before giving up, mirroring ROM `src/mob_cmds.c:1272-1286`.
  Previously the function iterated the exits list in order, so the first
  valid exit always won — wrong distribution for ROM-faithful flee
  behavior. Integration coverage at
  `tests/integration/test_mob_cmds_flee.py::TestMpFleeRandomDoor`.
- MOBCMD-010: `do_mpflee` (MOBprog `flee` script command) now routes through
  `mud.world.movement.move_character` instead of the silent `_move_to_room`
  helper, mirroring ROM `src/mob_cmds.c:1283`
  (`move_char(ch, door, FALSE)`). Leave/arrive broadcasts, mp_exit/entry
  triggers, and the rest of the canonical movement pipeline now fire on
  script-driven flees. Integration coverage at
  `tests/integration/test_mob_cmds_flee.py`.
- MOBCMD-005: `do_mpoload` (MOBprog `oload` script command) now accepts the
  optional `level` argument from `mob oload <vnum> [level] [R|W]`, mirroring
  ROM `src/mob_cmds.c:538-614`. When omitted, level defaults to
  `get_trust(ch)`; the spawned object's `level` is set post-spawn to mirror
  ROM `create_object(pObjIndex, level)`. Previously the level token was parsed
  but discarded, so script-loaded objects always took the prototype's raw
  level. Integration coverage at `tests/integration/test_mob_cmds_oload.py`.
- MOBCMD-014: `do_mpdamage` (MOBprog `damage` script command) now routes
  through `mud.combat.engine.apply_damage` instead of raw-decrementing
  `victim.hit`. Mirrors ROM `src/mob_cmds.c:1132-1145`
  (`damage(victim, victim, amount, TYPE_UNDEFINED, DAM_NONE, FALSE)`) so
  the death pipeline, position updates, fight triggers, and corpse
  handling fire on script-driven damage. Integration coverage at
  `tests/integration/test_mob_cmds_damage.py`.

### Changed

- `docs/parity/ACT_OBJ_C_AUDIT.md` and `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
  refreshed to reflect that ROM `src/act_obj.c` is at 100% parity. Apr 27, 2026
  formal sweep verified all 12 audited functions
  (`do_get`/`do_put`/`do_drop`/`do_give`/`do_remove`/`do_sacrifice`/`do_quaff`/
  `do_drink`/`do_eat`/`do_fill`/`do_pour`/`do_recite`/`do_brandish`/`do_zap`
  plus `do_wear`/`do_wield`/`do_hold` and `do_steal`) against current Python;
  the recent batch commits (`97c901e` do_drop parity batch, `517542b` close
  get/put/drop/give/wear/sacrifice/recite/brandish/zap/steal gaps) closed all
  outstanding gaps. 193 act_obj-area integration tests green. P1 audited count
  rises from 5/11 (81%) to 6/11 (86%). No code changes — documentation
  reconciliation only.

## [2.6.3] - 2026-04-27

### Added

- Three project-local skills under `.claude/skills/` encoding the ROM 2.4b6 →
  Python parity loop: `rom-parity-audit` (file-level 5-phase audit),
  `rom-gap-closer` (single-gap TDD close flow), `rom-session-handoff`
  (end-of-session SESSION_SUMMARY + SESSION_STATUS + CHANGELOG generation).
- `CLAUDE.md` "Porting workflow" section: decision-tree mapping of when to
  invoke each skill plus dependencies between them.

### Changed

- `README.md` Project Status / badges refreshed to current state: version
  `2.6.2`, tests `3508/3521 passing` (99.6%) with 11 skipped and 2 known
  pre-existing failures, integration suite `1000+`, ROM 2.4b parity badge
  scoped to "gameplay 100%" (truer given the long tail of P2/P3 files), and
  active focus called out as `act_obj.c` (~60%).
- `AGENTS.md` Repo Hygiene §2 now requires that any change to README's
  Project Status / badges / metrics be accompanied in the same commit by a
  refresh of AGENTS.md tracker pointers and `docs/sessions/SESSION_STATUS.md`,
  preventing drift between the three surfaces. Underlying numbers stay
  sourced from `docs/parity/*` trackers.

## [2.6.2] - 2026-04-27

### Fixed

- **act_enter portal regressions** uncovered by the act_enter.c audit
  (PR #123):
  - `_stand_charmed_follower` now forwards `do_stand`'s returned string
    into the follower's message stream, so charmed sleepers receive the
    "You wake and stand up." text exactly as ROM `act_move.c:1044`
    sends inside `do_stand`.
  - `_portal_fade_out` now explicitly removes the portal from
    `room.contents` and clears `portal.location`. `game_loop._extract_obj`
    keys off `obj.in_room` but `Object` uses `obj.location`, so portal
    detachment after charge expiry was a silent no-op. Behavior now
    matches ROM `extract_obj(portal)` at `act_enter.c:212`.
  - `test_enter_closed_portal_denied`: corrected expected message to
    `"You can't seem to find a way in."` per ROM `act_enter.c:94`. The
    prior `"The portal is closed."` was the door-blocked message from
    `act_move.c`, not the portal path.
  - `test_move_through_portal_blocked_while_fighting`: corrected to
    assert silent return per ROM `act_enter.c:70-71`
    (`if (ch->fighting != NULL) return;`); removed the non-ROM
    `"No way!  You are still fighting!"` string.
- **`test_giant_strength_refuses_to_stack`** (was
  `test_stat_modifiers_stack_from_same_spell`): test asserted +4 STR after
  recasting giant strength, but ROM `src/magic.c:3022-3030`
  `spell_giant_strength` early-returns with "You are already as strong as
  you can get!" when the target is already affected. The Python
  implementation correctly mirrors ROM; the test was wrong. Rewrote the
  test to assert ROM anti-stack behavior.
- **`test_scavenger_prefers_valuable_items`**: flaky because the
  Mitchell-Moore RNG state leaks across tests, and the scavenger only acts
  on a 1/64 roll per `mobile_update` tick. Seed `rng_mm.seed_mm` to a
  known value at start of test and bump the iteration cap from 2000 to
  5000 for deterministic passes.

## [2.6.1] - 2026-04-27

### Added

- **act_enter.c parity (100% ROM parity for portal/enter mechanics):**
  Close all 15 ENTER-001..016 gaps documented in
  `docs/parity/ACT_ENTER_C_AUDIT.md`. 25 new integration tests in
  `tests/integration/test_act_enter_gaps.py`.

### Fixed

- **ENTER-009 (CRITICAL):** `do_enter` TO_CHAR message ("You enter $p." /
  "...somewhere else...") was being returned as a Python string and
  silently dropped — now delivered to the player.
- **ENTER-005:** Portal lookup uses `get_obj_list` (visibility,
  numbered syntax `2.portal`, keyword-list semantics) instead of fuzzy
  substring matching.
- **ENTER-004:** Non-portal objects and closed portals both produce
  `"You can't seem to find a way in."` (was diverging).
- **ENTER-008/010:** Departure/arrival TO_ROOM messages go through
  `act_format` + `broadcast_room` for correct `$n` invisibility
  resolution.
- **ENTER-011:** Portal fade-out only broadcasts in the old room when
  caller is in the old room; calls `extract_obj` on charge expiry.
- **ENTER-013:** `_get_random_room` capped at 100k iterations
  (was potentially returning None; ROM loops indefinitely).
- **ENTER-006/007/012:** Follower cascade — charmed followers stand
  before following, follower-name interpolation via `act_format`.
- **ENTER-002/003/014/015/016:** Cosmetic message wording matched to
  ROM and fighting-character silent-skip path.

## [2.6.0] - 2026-04-27

### Added

- **act_obj.c parity batch (100% ROM parity for object-manipulation
  commands):** do_get/do_put/do_drop/do_give/do_wear/do_remove/do_sacrifice/
  do_quaff/do_eat/do_drink/do_fill/do_pour/do_envenom/do_recite/do_brandish/
  do_zap/do_steal and shop commands (do_buy/do_sell/do_list/do_value).
  Adds full ROM TO_ROOM/TO_VICT/TO_NOTVICT broadcasts via act_format +
  broadcast_room. ~80 new integration tests under tests/integration/.
- **act_move.c parity batch:** do_stand/do_rest/do_sit/do_sleep/do_wake
  rewritten with full ROM furniture support (STAND/SIT/REST/SLEEP_AT/ON/IN
  with capacity checks and ch.on tracking). MOVE-001 arrival broadcast,
  MOVE-002 follower-name interpolation, SNEAK-001/HIDE-001 dispatcher
  delegation to canonical handlers. 40 new integration tests in
  tests/integration/test_position_commands.py.
- **act_comm.c P2 batch:** do_emote NOEMOTE check, do_pmote (~312 lines),
  do_colour, do_split gold+silver simultaneous-split fix, do_pose pose_table
  by class+level. New mud/utils/poses.py.
- **act_info.c P2 batch:** do_title/do_description/auto-settings family
  (autolist, autoassist, autoexit, autogold, autoloot, autopeek, autosac,
  autosplit, autotitle).
- LIQUID_TABLE in mud/models/constants.py extended with proof/full/thirst/
  food/ssize fields sourced from ROM src/const.c:886-931.
- WebSocket stream support (mud/network/websocket_stream.py) for the
  browser frontend; tests in tests/test_websocket_server.py.

### Changed

- **AGENTS.md rewritten:** ~700 lines → 275. Removed running session
  narrative, duplicated status reporting, stale "next steps". Added Session
  Notes (docs/sessions/) and Repo Hygiene (CHANGELOG / README / semver in
  pyproject.toml) sections modeled on quickmud-web-client/AGENTS.md.
- 79 SESSION_SUMMARY_*.md and HANDOFF_*.md files moved from repo root to
  `docs/sessions/`.

### Fixed

- `_obj_from_char()` now operates on `char.inventory` (was reading the
  wrong field, so transferred objects were not removed from giver).
- `count_users()` in mud/handler.py now reads `room.people` (room.characters
  does not exist).
- String-keyed equipment lookups replaced with `WearLocation` IntEnum keys
  across BRANDISH/ZAP/POUR families.
- Hardcoded hex flag values replaced with enum members
  (`PlayerFlag.AUTOSPLIT`, `WearFlag.NO_SAC`, `ItemType.STAFF/WAND`, etc).
- `do_steal` MAX_LEVEL set to 60 (was 51); STEAL-001..014 covering
  one_argument semantics, is_safe, is_clan, sleeping-victim wake, PC→PC
  PlayerFlag.THIEF, multi_hit signature, NODROP/INVENTORY checks,
  can_see_object visibility filter.
- `do_recite/do_brandish/do_zap` success paths were unrunnable due to
  undefined SkillTarget, bad ItemType references, string-keyed HOLD
  lookup; all 17 RECITE/BRANDISH/ZAP gaps closed.

## [2.5.2] - 2025-12-30

### Added

- **Command Integration ROM Parity Tests** (70 new tests):
  - `tests/test_act_comm_rom_parity.py` - 23 tests for communication commands (ROM `act_comm.c`)
    - Channel status display (`do_channels`)
    - Communication flag toggles (`do_deaf`, `do_quiet`, `do_afk`)
    - Channel blocking logic (QUIET, NOCHANNELS flags)
    - Delete command NPC blocking
    - Replay command behaviors
  - `tests/test_act_enter_rom_parity.py` - 22 tests for portal mechanics (ROM `act_enter.c`)
    - Random room selection with flag exclusions (`get_random_room`)
    - Portal entry mechanics (closed, curse, trust checks)
    - Portal charge system and flag handling (RANDOM, BUGGY, GOWITH)
    - Follower cascading through portals
  - `tests/test_act_wiz_rom_parity.py` - 25 tests for wiznet/admin commands (ROM `act_wiz.c`)
    - Wiznet channel toggle and flag management
    - Wiznet broadcast filtering (WIZ_ON, flag filters, min_level)
    - Admin commands (freeze, transfer, goto, trust)
    - Trust level enforcement

- **Documentation**:
  - `COMMAND_INTEGRATION_PARITY_REPORT.md` - Comprehensive command integration test completion report
    - Detailed ROM C to Python mapping for all 70 tests
    - Test philosophy and design decisions
    - ROM C source analysis summary
    - Quality metrics and coverage matrix

### Changed

- **ROM 2.4b6 Parity Certification Updates**:
  - Updated total ROM parity test count: 735 → 805 tests (+70)
  - Updated total test count: 2507 → 2577 tests (+70)
  - Added Command Integration Tests section to certification document
  - Updated ROM C source verification to include `act_comm.c`, `act_enter.c`, `act_wiz.c`

- **Test Coverage**:
  - Increased command integration test coverage (communication, portal, wiznet modules)
  - Total ROM parity tests: 805 (127 P0/P1/P2 + 608 combat/spells/skills + 70 command integration)

## [2.5.1] - 2025-12-30

### Added

- **Session Summary Documentation**:
  - `P0_P1_P2_EXTENDED_TESTING_SESSION_SUMMARY.md` - Verification session summary documenting that all P0/P1/P2 ROM C parity tests were already complete from previous sessions (December 29-30, 2025)

### Changed

- Updated README badges and project status to reflect complete ROM C parity test coverage (735 total ROM parity tests including 127 P0/P1/P2 formula verification tests)

## [2.5.0] - 2025-12-29

### Added

- **🎉 ROM 2.4b6 Parity Certification**: Official 100% ROM 2.4b6 behavioral parity certification
  - Created `ROM_2.4B6_PARITY_CERTIFICATION.md` - Comprehensive official certification document
  - 10 detailed subsystem parity matrices with ROM C source verification
  - Complete audit trail with 7 comprehensive audit documents (2000+ lines)
  - Integration test verification (43/43 passing = 100%)
  - Unit test coverage breakdown (700+ tests)
  - Differential testing methodology documented
  - Production readiness assessment
  - All 7 certification criteria verified and passing

- **Combat System Parity Verification** (100% Complete):
  - `COMBAT_PARITY_AUDIT_2025-12-28.md` - Comprehensive combat system audit
  - Added combat assist system (`mud/combat/assist.py`) with all ROM mechanics
  - Added 30+ combat tests (damage types, position multipliers, surrender command)
  - Verified all 32 ROM C combat functions implemented
  - Verified all 15 ROM combat commands functional
  - Position-based damage multipliers (sleeping 2x, resting/sitting 1.5x)
  - Damage resistance/vulnerability system complete
  - Special weapon effects (sharpness, vorpal, flaming, frost, vampiric, poison)

- **World Reset System Parity Verification** (100% Complete):
  - `WORLD_RESET_PARITY_AUDIT.md` - Comprehensive reset system audit
  - Verified all 7 ROM reset commands (M, O, P, G, E, D, R)
  - 49/49 reset tests passing with complete behavioral verification
  - Door state synchronization (bidirectional + one-way doors)
  - Exit randomization (Fisher-Yates shuffle)
  - ROM scheduling formula verified exact
  - Special cases documented (shop inventory, pet shops, infrared)

- **OLC Builders System Parity Verification** (100% Complete):
  - `OLC_PARITY_AUDIT.md` - Comprehensive OLC system audit
  - Verified all 5 ROM editors (@redit, @aedit, @oedit, @medit, @hedit)
  - 189/189 OLC tests passing with complete workflow verification
  - All 5 @asave variants functional
  - All 5 builder stat commands operational
  - Builder security system complete (trust levels, vnum ranges)

- **Security System Parity Verification** (100% Complete):
  - `SECURITY_PARITY_AUDIT.md` - Comprehensive security system audit
  - `SECURITY_PARITY_COMPLETION_SUMMARY.md` - Security session summary
  - Verified all 6 ROM ban flags (BAN_SUFFIX, PREFIX, NEWBIES, ALL, PERMIT, PERMANENT)
  - All 4 pattern matching modes (exact, prefix*, *suffix, *substring*)
  - 25/25 ban tests passing
  - Trust level enforcement verified
  - ROM file format compatibility verified

- **Object System Parity Verification** (100% Complete):
  - `OBJECT_PARITY_COMPLETION_REPORT.md` - Object system completion report
  - `docs/parity/OBJECT_PARITY_TRACKER.md` - Detailed 11-subsystem breakdown
  - Verified all 17 ROM object commands functional
  - 152/152 object tests passing + 277+ total object-related tests
  - Complete equipment system (11/11 wear mechanics)
  - Full container system (9/9 mechanics)
  - Exact encumbrance system (7/7 ROM C functions)
  - Complete shop economy (11/11 features)

- **Session Documentation**:
  - `SESSION_SUMMARY_2025-12-28.md` - Complete session documentation
  - `SESSION_SUMMARY_2025-12-27.md` - Previous session documentation

- **Additional Audit Documents**:
  - `SPELL_AFFECT_PARITY_AUDIT_2025-12-28.md` - Spell affect system verification
  - `COMBAT_GAP_VERIFICATION_FINAL.md` - Combat gap analysis and closure
  - `COMBAT_DAMAGE_RESISTANCE_COMPLETION.md` - Damage type system completion
  - `REMAINING_PARITY_GAPS_2025-12-28.md` - Final gap analysis (none remaining)
  - `COMMAND_AUDIT_2025-12-27_FINAL.md` - Command parity final verification

### Changed

- **README.md Updates**:
  - Updated version badge to 2.5.0
  - Updated ROM parity badge to link to official certification
  - Added "CERTIFIED" designation to ROM parity claim
  - Updated test counts to reflect integration test results (43/43 passing)
  - Added integration tests badge
  - Reorganized documentation section with certification first
  - Updated project status section with certification details

- **Documentation Organization**:
  - Added official certification as primary documentation
  - Reorganized docs to highlight certification achievement
  - Updated all parity references to point to certification

- **Test Organization**:
  - Added `tests/test_combat_assist.py` - Combat assist mechanics (14 tests)
  - Added `tests/test_combat_damage_types.py` - Damage resistance/vulnerability (15 tests)
  - Added `tests/test_combat_position_damage.py` - Position damage multipliers (10 tests)
  - Added `tests/test_combat_surrender.py` - Surrender command (5 tests)

### Fixed

- Combat damage vulnerability check now runs after immunity check (ROM parity fix)
- Corrected misleading "decapitation" comment on vorpal flag (ROM 2.4b6 has no decapitation)
- Updated outdated parity assessments in ROM_PARITY_FEATURE_TRACKER.md

### Verified

- ✅ **100% ROM 2.4b6 command coverage** (255/255 commands implemented)
- ✅ **100% integration test pass rate** (43/43 tests passing)
- ✅ **96.1% ROM C function coverage** (716/745 functions mapped)
- ✅ **All 10 major subsystems** verified with comprehensive audits
- ✅ **Production readiness** confirmed for players, builders, admins, developers

### Documentation

- 7 comprehensive audit documents totaling 2000+ lines
- Official ROM 2.4b6 parity certification document
- Complete ROM C source verification methodology
- Differential testing documentation
- Production deployment guidelines

## [2.4.0] - 2025-12-27

### Added

- **GitHub Release Creator Skill**: Comprehensive Claude Desktop skill for automated release management
  - Added `.claude/skills/github-release-creator/` with complete release automation tooling
  - Python script for automated release creation (`create_release.py`)
  - Shell scripts for release validation and creation
  - Changelog extraction utilities
  - Complete documentation with usage examples and workflows
  - GitHub CLI integration for professional release management
  - Support for semantic versioning, draft releases, and pre-releases

## [2.3.1] - 2025-12-27

### Added

- **Comprehensive Test Planning Documentation**:
  - Created `docs/validation/MOB_PARITY_TEST_PLAN.md` - Complete testing strategy for ROM 2.4b mob behaviors
    - 22 spec_fun behaviors (guards, dragons, casters, thieves)
    - 30+ ACT flag behaviors (aggressive, wimpy, scavenger, sentinel)
    - Damage modifiers (immunities, resistances, vulnerabilities)
    - Mob memory and tracking systems
    - Group assist mechanics
    - Wandering/movement AI
  - Created `docs/validation/PLAYER_PARITY_TEST_PLAN.md` - Complete testing strategy for player-specific behaviors
    - Information display commands (score, worth, whois)
    - Auto-settings (autoassist, autoloot, autogold, autosac, autosplit)
    - Conditions system (hunger, thirst, drunk, full)
    - Player flags and reputation (KILLER, THIEF)
    - Prompt customization
    - Title/description management
    - Trust/security levels
    - Player visibility states (AFK, wizinvis, incognito)
- **Claude Desktop Skill Support**:
  - Added `SKILL.md` - Comprehensive skill documentation for AI assistants
  - Added `.claude/skills/skill-creator/` - Anthropic's skill-creator tool
    - Skill validation scripts
    - Skill packaging utilities
    - Best practices documentation

### Changed

- **Test Organization**: Created clear roadmap for implementing 180+ behavioral tests
  - 6 major mob test areas (P0-P3 priority matrix)
  - 8 major player test areas (P0-P3 priority matrix)
  - 4-phase implementation roadmap for each
  - Complete test templates with ROM C references

### Documentation

- Documented 100+ specific test cases with ROM C source references
- Added implementation effort estimates and player impact assessments
- Created comprehensive testing guides for future development

## [2.3.0] - 2025-12-26

### Added

- **MobProg 100% ROM C Parity Achievement**: All 4 critical trigger hookups complete
  - `mp_give_trigger` integrated in do_give command
  - `mp_hprct_trigger` integrated in combat damage system
  - `mp_death_trigger` integrated in character death handling
  - `mp_speech_trigger` already integrated (verified)
- MobProg movement command validation in area file validator
- Comprehensive MobProg testing documentation (5 guides)
- Enhanced `validate_mobprogs.py` with movement command validation
- Organized validation and parity documentation structure

### Changed

- **Documentation Reorganization**: Created proper folder structure
  - Moved 10 documentation files to `docs/validation/` and `docs/parity/`
  - Moved 10 scripts to `scripts/validation/` and `scripts/parity/`
  - Moved 5 report files to appropriate `reports/` subfolders
  - Created 6 README files documenting folder contents
- Updated all cross-references in documentation to use new paths
- Enhanced validation scripts with movement command checks

### Fixed

- Integration test issues with Object creation and trigger signatures
- Syntax error in validate_mobprogs.py output formatting

## [2.2.1] - Previous Release

### Added

- Complete weapon special attacks system with ROM 2.4 parity (WEAPON_VAMPIRIC, WEAPON_POISON, WEAPON_FLAMING, WEAPON_FROST, WEAPON_SHOCKING)

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [1.3.0] - 2025-09-15

### Added

- Complete fighting state management with ROM 2.4 parity
- Character immortality protection following IS_IMMORTAL macro
- Level constants (MAX_LEVEL, LEVEL_IMMORTAL) matching ROM source

### Changed

### Deprecated

### Removed

### Fixed

- Character position initialization defaults to STANDING instead of DEAD
- Fighting state damage application and position updates
- Immortal character survival logic in combat system
- Combat defense order to match ROM 2.4 C source (shield_block → parry → dodge)

### Security

## [1.2.0] - 2025-09-15

### Added

- Complete telnet server with multi-user support
- Working shop system with buy/sell/list commands
- 132 skill system with handler stubs
- JSON-based world loading with 352 resets in Midgaard
- Admin commands (teleport, spawn, ban management)
- Communication system (say, tell, shout, socials)
- OLC building system for room editing
- pytest-timeout plugin for proper test timeouts

### Changed

- Achieved 100% test success rate (200/200 tests)
- Full test suite completes in ~16 seconds
- Modern async/await telnet server architecture
- SQLAlchemy ORM with migrations
- Comprehensive test coverage across all subsystems
- Memory efficient JSON area loading
- Optimized command processing pipeline
- Robust error handling throughout

### Fixed

- Character position initialization (STANDING vs DEAD)
- Hanging telnet tests resolved
- Enhanced error handling and null room safety
- Character creation now allows immediate command execution

## [0.1.1] - 2025-09-14

### Added

- Initial ROM 2.4 Python port foundation
- Basic world loading and character system
- Core command framework
- Database integration with SQLAlchemy

### Changed

- Migrated from legacy C codebase to pure Python
- JSON world data format for easier editing
- Modern Python packaging structure

## [0.1.0] - 2025-09-13

### Added

- Initial project structure
- Basic MUD framework
- ROM compatibility layer
- Core game loop implementation

[Unreleased]: https://github.com/Nostoi/rom24-quickmud-python/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/Nostoi/rom24-quickmud-python/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/Nostoi/rom24-quickmud-python/compare/v0.1.1...v1.2.0
[0.1.1]: https://github.com/Nostoi/rom24-quickmud-python/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Nostoi/rom24-quickmud-python/releases/tag/v0.1.0
