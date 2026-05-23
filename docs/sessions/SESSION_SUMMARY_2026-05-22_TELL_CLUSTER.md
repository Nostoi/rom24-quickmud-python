# Session Summary — 2026-05-22 — `do_tell` re-audit (TELL-001..005)

## Scope

Fourth slice of the 2026-05-22 act_comm.c re-audit arc. Applied the
now-proven channel-message lens to `do_tell`. Like `do_say` and
`do_emote` earlier this run, the prior "100% VERIFIED" claim in
`ACT_COMM_C_AUDIT.md` was incorrect (December 2025 audit-doc
inflation). Six gaps surfaced; closed five in this session, deferred
one (MINOR cosmetic) for next session.

## Outcomes

### `TELL-001` — ✅ FIXED — TO_CHAR wording drops comma (2.8.44 / `4ff037a`)

- **Python**: `mud/commands/communication.py:do_tell` return
- **ROM C**: `src/act_comm.c:941`
- **Fix**: `"You tell {N}, '{t}'"` → `"You tell {N} '{t}'"`. Legacy assertions in `tests/test_communication.py` (×2) and `tests/integration/test_communication_enhancement.py` updated.
- **Test**: `tests/integration/test_tell_parity.py::test_tell_001_to_char_wording_drops_comma`.

### `TELL-002` — ✅ FIXED — TO_VICT wording drops comma (2.8.45 / `c4cb39b`)

- **Python**: `mud/commands/communication.py:_handle_buffered_tell`
- **ROM C**: `src/act_comm.c:942`
- **Fix**: `"{n} tells you, '{t}'"` → `"{n} tells you '{t}'"`. Legacy assertions in `tests/test_communication.py` (×4) updated.
- **Test**: `tests/integration/test_tell_parity.py::test_tell_002_to_vict_wording_drops_comma`.

### `TELL-003` — ✅ FIXED — TO_VICT `$n` routes through PERS (2.8.46 / `c2f9aa8`)

- **Python**: `mud/commands/communication.py:_handle_buffered_tell`
- **ROM C**: `src/act_comm.c:942`, `src/handler.c:2618`
- **Fix**: `pers(sender, target)` substituted for `sender.name`. Invisible sender renders as `"someone"` to target without `DETECT_INVIS`. Same PERS pattern as SAY-002 / EMOTE-001. Buffered tells (linkdead/AFK/note-writing branches) get the same protection because they share the formatted string.
- **Test**: `tests/integration/test_tell_parity.py::test_tell_003_invisible_sender_renders_as_someone_to_target`.

### `TELL-004` — ✅ FIXED — TO_CHAR `$N` routes through PERS (defensive parity) (2.8.47 / `3aabbe8`)

- **Python**: `mud/commands/communication.py:do_tell` return
- **ROM C**: `src/act_comm.c:941`, `src/handler.c:2618`
- **Fix**: `pers(target, char)` substituted for `target.name`.
- **Note**: Behaviorally masked — `get_char_world` (ROM + Python) filters via `can_see` during name lookup, so an invisible target returns `"They aren't here."` before PERS ever evaluates. The fix is defensive code-parity: macro structure now matches ROM regardless of future lookup-path changes.
- **Test**: `tests/integration/test_tell_parity.py::test_tell_004_to_char_uses_pers_for_target_name` (visible-target path).

### `TELL-005` — ✅ FIXED — both lines wrap ROM `{k...{K...{k...{x` charcoal codes (2.8.48 / `7f64764`)

- **Python**: `mud/commands/communication.py:do_tell` + `_handle_buffered_tell`
- **ROM C**: `src/act_comm.c:941-942`
- **Fix**: Wrap TO_CHAR and TO_VICT strings with `{k...{K...{k...{x` charcoal/black colour sequence; `mud/net/ansi.py` consumes them on websocket send. Legacy assertions in `tests/test_communication.py` (×5) and `tests/integration/test_communication_enhancement.py` updated.
- **Tests**: `tests/integration/test_tell_parity.py::test_tell_005_to_char_wraps_rom_color_codes` + `::test_tell_005_to_vict_wraps_rom_color_codes`.

## Deferred

### `TELL-006` — 🔄 OPEN — capitalize first char of buffered tells (MINOR)

ROM `do_tell` calls `buf[0] = UPPER(buf[0])` after building the
buffered tell string (lines 893, 926, 937). Python's
`_handle_buffered_tell` does not. Cosmetic only — affects the very
first character of tells delivered to linkdead / AFK / note-writing
targets. Stable-IDed in `ACT_COMM_C_AUDIT.md` for a future session.

## Investigation discipline note (TELL-004)

TELL-004 surfaced an interesting class of audit finding: a true
code-structure divergence from ROM that is behaviorally masked by
an upstream filter. The reflex response would be to either (a) skip
it as "not a real bug" or (b) construct an artificial test setup
to exercise the unreachable branch. Both are wrong.

Right answer: fix the code-structure divergence (so the macro
intent is preserved against future refactors) AND pin the test to
the actually-reachable behavior. The `someone` branch protection
is verified transitively via SAY-002 / EMOTE-001 / TELL-003 which
do exercise it. The audit-doc row makes the masking explicit so
the next auditor knows why the test asserts the visible path.

## Files Modified

- `mud/commands/communication.py` — `do_tell` and `_handle_buffered_tell` for all 5 fixes.
- `tests/integration/test_tell_parity.py` — **new file** — 6 tests (TELL-001/002/003/004/005×2).
- `tests/test_communication.py` — updated 7 assertions to ROM-exact form.
- `tests/integration/test_communication_enhancement.py` — updated 1 assertion.
- `docs/parity/ACT_COMM_C_AUDIT.md` — `do_tell` row demoted from "VERIFIED ✅" to active gap table; TELL-001..005 ✅, TELL-006 deferred.
- `CHANGELOG.md` — `[2.8.44]` → `[2.8.48]` sections.
- `pyproject.toml` — 2.8.43 → 2.8.48.

## Test Status

- Targeted (`tests/integration/test_tell_parity.py`): 6/6 passing.
- Full suite: **4625 passed, 4 skipped** (+6 vs 2.8.43 baseline 4619/4; zero regressions across all five releases).

## Next Steps

Two `act_comm.c` re-audits still in play, plus the deferred items
already on the shelf:

1. **`do_shout` / `do_yell`** — global broadcast channels. Per-listener
   PERS cost higher but ROM does it. Verify INV-001 single-delivery
   (probably OK since `broadcast_global` is one call). Existing
   audit doc claims `do_shout` VERIFIED — high probability the same
   audit-doc inflation pattern; expect SHOUT-001 wording / SHOUT-002
   colour / SHOUT-003 PERS gaps.
2. **PMOTE-001** — greenfield port of ROM `do_pmote` (~50 lines of
   C string matching for per-recipient second-person name
   substitution). Larger; its own session.
3. **TELL-006** — uppercase first char of buffered tells. MINOR
   cosmetic; quick warm-up if you want one.
4. **PROMPT-CMD-004 / PROMPT-CMD-005** — corner-case warm-ups still
   stable-IDed from earlier this run.

Recommendation: **#1 (`do_shout`/`do_yell`)** to complete the major
channel-command quartet (say/tell/emote/shout) before tackling
PMOTE or warm-ups.

## Operational follow-ups

- `log/orphaned_helps.txt` still tracked + still drifting. Repo hygiene commit pending.
- GitNexus 32 KB scope-extractor failures persist on the documented file list; this slice did not touch any listed file.
- Local commits `4ff037a..7f64764` (5 fixes) not pushed yet — waiting on explicit user push approval.
