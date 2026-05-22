# Session Summary — 2026-05-22 — `do_say` re-audit (SAY-001/003/004) + PROMPT-CMD-003

## Scope

Two slices in one session:

1. **PROMPT-CMD-003** — closed the PROMPT-CMD cluster opened by
   2.8.35's NANNY-SAVELOAD-002 probe by running `smash_tilde` on the
   `do_prompt` custom-template branch.
2. **`do_say` re-audit** — re-verified `src/act_comm.c:768-791`
   against the live Python implementation. The prior
   `ACT_COMM_C_AUDIT.md` "100% VERIFIED" claim was incorrect; four
   gaps surfaced. Closed three of them (SAY-001 wording, SAY-003
   colour codes, SAY-004 INV-001 double-delivery). SAY-002 (`$n`
   PERS substitution for invisible/hidden speakers) is large enough
   to need its own dedicated session — handed off intentionally with
   scoped follow-up instructions below.

## Outcomes

### `PROMPT-CMD-003` — ✅ FIXED — `smash_tilde` on custom prompt template (2.8.37)

- **Python**: `mud/commands/auto_settings.py:do_prompt` (custom-template branch)
- **ROM C**: `src/act_info.c:945`, `src/db.c:3663-3672`
- **Fix**: Call `mud.utils.text.smash_tilde(arg)` before assigning `char.prompt`.
- **Test**: `tests/integration/test_prompt_cmd_parity.py::test_prompt_cmd_003_smash_tilde_on_custom_template`.
- **Commit**: `2aae0fa`.

### `SAY-001` — ✅ FIXED — `do_say` wording drops the comma (2.8.38)

- **Python**: `mud/commands/communication.py:do_say`
- **ROM C**: `src/act_comm.c:776-777`
- **Fix**: Emit `"<name> says '<msg>'"` and `"You say '<msg>'"` — no comma.
- **Tests**: `tests/integration/test_say_parity.py::test_say_001_room_broadcast_drops_comma` + `::test_say_001_to_char_drops_comma`.
- **Legacy test updates** (per AGENTS.md — tests asserting contradicting Python behaviour are bugs in the test): `tests/test_commands.py`, `tests/test_command_abbrev.py`, `tests/integration/test_communication_enhancement.py`.
- **Commit**: `7d1c332`.

### `SAY-004` — ✅ FIXED — `do_say` TO_ROOM delivered exactly once (2.8.39)

- **Python**: `mud/commands/communication.py:do_say`
- **ROM C**: `src/act_comm.c:776`
- **Fix**: Dropped redundant `broadcast_room` call. `room.broadcast` and `broadcast_room` did identical work (iterate `room.people`, fire-and-forget websocket send, append to `char.messages`), so every `say` was delivered twice — INV-001 SINGLE-DELIVERY violation.
- **Test**: `tests/integration/test_say_parity.py::test_say_004_listener_receives_broadcast_exactly_once`.
- **Commit**: `8f44ecd`.

### `SAY-003` — ✅ FIXED — `do_say` wraps output with ROM colour codes (2.8.40)

- **Python**: `mud/commands/communication.py:do_say`
- **ROM C**: `src/act_comm.c:776-777`
- **Fix**: Wrap TO_CHAR and TO_ROOM strings with ROM's `{6...{7$T{6'{x` cyan/white colour sequence. The ANSI translation layer at `mud/net/ansi.py` consumes those tokens on websocket send.
- **Tests**: `tests/integration/test_say_parity.py::test_say_003_to_char_wraps_rom_color_codes` + `::test_say_003_to_room_wraps_rom_color_codes`.
- **Legacy test updates**: `tests/test_commands.py`, `tests/test_command_abbrev.py`, `tests/integration/test_communication_enhancement.py` updated to the ROM-exact colour-wrapped form.
- **Commit**: `07153fa`.

## Open follow-up (deferred intentionally)

### `SAY-002` — 🔄 OPEN — `$n` PERS substitution for invisible/hidden speakers

ROM `act()` routes the speaker name through `PERS()`:

```c
#define PERS(ch, looker) (can_see (looker, ch) ? \
    (IS_NPC(ch) ? ch->short_descr : ch->name) : "someone")
```

Python hardcodes `char.name` so invisible/hidden PCs leak their name
when speaking. Fixing this is **not** a one-liner: no `can_see` or
`pers` helper currently exists in `mud/`. A proper close needs:

1. New `can_see(observer, target)` helper consulting
   `AffectFlag.INVISIBLE` / `HIDDEN`, blindness, room darkness +
   detect-invis / detect-hidden / infrared affects.
2. New `pers(target, observer)` helper using `can_see`.
3. Refactor `do_say` (and likely every `act()`-shaped Python
   broadcast site) to render the message per-listener so each
   recipient sees the appropriate substitution.
4. Integration tests for at least invisible / hidden / blind-observer
   / dark-room cases.

This is 100-200 lines of new subsystem code and likely surfaces
other `act()` call sites that have the same bug. Treat as its own
session — recommended pickup order:

- Audit which Python broadcast sites need `PERS()` (grep
  `room.broadcast`, `broadcast_room`, any `act_*` analogues).
- Build `can_see` + `pers` with their own unit tests first.
- Then refactor `do_say` and lock in SAY-002.
- Sibling commands likely have analogous CRITICAL gaps
  (`do_tell`, `do_shout`, `do_yell`, `do_emote`); audit them in the
  same arc once the helper is in place.

## Files Modified (this session)

- `mud/commands/auto_settings.py` — `do_prompt` calls `smash_tilde` on custom template.
- `mud/commands/communication.py` — `do_say` drops comma, drops double broadcast, wraps colour codes.
- `tests/integration/test_prompt_cmd_parity.py` — added PROMPT-CMD-003 test.
- `tests/integration/test_say_parity.py` — **new file** — five SAY tests (SAY-001×2, SAY-003×2, SAY-004).
- `tests/test_commands.py` — updated 5 `say`-assertions to ROM-exact form.
- `tests/test_command_abbrev.py` — updated 1 `say`-assertion.
- `tests/integration/test_communication_enhancement.py` — updated 1 `say`-assertion.
- `docs/parity/ACT_INFO_C_AUDIT.md` — `do_prompt` row notes PROMPT-CMD-003 ✅, PROMPT-CMD-004/005 stable-IDed for future.
- `docs/parity/ACT_COMM_C_AUDIT.md` — `do_say` row demoted from "VERIFIED ✅" to active gap table; SAY-001/003/004 ✅ FIXED, SAY-002 🔄 OPEN.
- `CHANGELOG.md` — `[2.8.37]`, `[2.8.38]`, `[2.8.39]`, `[2.8.40]` sections.
- `pyproject.toml` — 2.8.36 → 2.8.40.

## Test Status

- Targeted (`tests/integration/test_say_parity.py`): 5/5 passing.
- Targeted (`tests/integration/test_prompt_cmd_parity.py`): 3/3 passing.
- Full suite at each release: 4609 → 4611 → 4612 → 4614 passed; 4 skipped; zero regressions across the four releases.

## Operational follow-ups

- `log/orphaned_helps.txt` still tracked + still drifting. Repo hygiene commit pending.
- GitNexus 32 KB scope-extractor failures persist on the documented file list; this session's edits did not touch any of the listed files except `mud/commands/dispatcher.py` (untouched this session) — no fallback was needed.
- SAY-002 carried as the next intended task. PROMPT-CMD-004 / PROMPT-CMD-005 stable-IDed but no behavioural payoff for typical play; only worth surfacing as warm-ups before a heavier session.
- Local commits NOT pushed yet — four `[master 2aae0fa..07153fa]` releases waiting on explicit user push approval.
