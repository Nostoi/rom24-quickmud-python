# Session Summary — 2026-05-22 — `do_say` PERS substitution (SAY-002)

## Scope

Closed the deferred fourth slice of the 2026-05-22 `do_say`
re-audit. SAY-002 covers ROM's `act()` substituting `$n` through
the `PERS()` macro so invisible/hidden speakers render as
`"someone"` to unaided listeners. Was deferred from the prior
session under the assumption it needed a 100-200 line subsystem
build (new `can_see` + `pers` helpers + per-listener broadcast
refactor).

Reality: `mud/world/vision.py:can_see_character` already mirrors
ROM `src/handler.c:2618-2664 can_see` faithfully (blind, dark,
INVISIBLE, SNEAK, HIDE, DETECT_INVIS, DETECT_HIDDEN, HOLYLIGHT,
infrared, trust+invis_level+incog_level — all handled). The
remaining work was small: a 12-line `pers()` wrapper and an
in-place per-listener broadcast loop inside `do_say`. Closed in one
TDD commit.

## Outcomes

### `SAY-002` — ✅ FIXED — `do_say` renders `$n` per-listener via PERS (2.8.41)

- **Python helper**: `mud/world/vision.py:pers(target, observer)`
- **Python caller**: `mud/commands/communication.py:do_say`
- **ROM C**: `src/act_comm.c:776` + ROM `PERS()` macro + `src/handler.c:2618-2664 can_see`
- **Fix**:
  1. Added `pers()` wrapper around the existing
     `can_see_character`. Returns `"someone"` if observer cannot
     see target, otherwise the NPC `short_descr` or PC `name`.
     Deliberately does NOT include aura prefixes (that's
     `show_char_to_char_0`'s job) or self-handling ("You" lives in
     the caller's TO_CHAR branch).
  2. Refactored `do_say` to drop `char.room.broadcast(message, ...)`
     and instead loop over `char.room.people`, building one
     substituted string per listener:
     `f"{{6{pers(speaker, listener)} says '{{7{args}{{6'{{x"`.
- **Tests**:
  - `tests/integration/test_say_parity.py::test_say_002_invisible_speaker_renders_as_someone_to_unaided_listener` —
    speaker has `AffectFlag.INVISIBLE`, listener has no
    `DETECT_INVIS` → listener sees `"someone says 'boo'"`, not the
    speaker's real name.
  - `tests/integration/test_say_parity.py::test_say_002_invisible_speaker_seen_by_detect_invis_listener` —
    same setup but listener has `DETECT_INVIS` → listener sees the
    real name. Pins both sides of the branch.
- **Commit**: `7465ac0`.

## Implications for sibling commands

The hard part of any "act() with `$n`" path now exists. Analogous
CRITICAL gaps almost certainly exist in:

- `do_tell` (target name through PERS for the
  `"$N tells you '$t'"` line — though the recipient ALWAYS sees
  the sender by name in ROM, so this may not actually divulge,
  worth checking).
- `do_shout`, `do_yell` (global broadcasts — per-listener PERS
  cost is higher, but ROM does it).
- `do_emote`, `do_pose`, `do_pmote` (`$n` substitution definitive).
- All combat damage messages (`act()` with `$n` / `$N`).

The pattern is now clean: per-listener loop + `pers(speaker,
listener)`. Recommended pickup order for the next session is
`do_emote` (lowest blast radius, mirrors `do_say` structure), then
`do_tell` (most-used), then the broadcast channels.

## Files Modified

- `mud/world/vision.py` — added `pers(target, observer)` helper (12 lines).
- `mud/commands/communication.py` — `do_say` refactored to per-listener PERS substitution.
- `tests/integration/test_say_parity.py` — added two SAY-002 tests.
- `docs/parity/ACT_COMM_C_AUDIT.md` — `do_say` row flipped to ✅ RE-AUDITED 100%; SAY-002 row ✅ FIXED.
- `CHANGELOG.md` — `[2.8.41]` section.
- `pyproject.toml` — 2.8.40 → 2.8.41.

## Test Status

- Targeted (`tests/integration/test_say_parity.py`): 7/7 passing (SAY-001×2, SAY-002×2, SAY-003×2, SAY-004).
- Full suite: **4616 passed, 4 skipped** (+2 vs 2.8.40 baseline 4614/4; zero regressions despite the per-listener broadcast refactor).

## Next Steps

`do_say` is ✅ done. Natural continuations:

1. **Audit `do_emote` / `do_pose` / `do_pmote`** — mirrors `do_say`
   structure exactly. PERS helper exists; should be a fast cluster
   to close.
2. **Audit `do_tell`** — high-traffic, but PERS impact may be
   limited because the recipient receives by direct lookup.
3. **PROMPT-CMD-004 / PROMPT-CMD-005** still stable-IDed warm-ups.

## Operational follow-ups

- `log/orphaned_helps.txt` still tracked + still drifting. Repo hygiene commit pending.
- GitNexus 32 KB scope-extractor failures persist on the documented file list. This session's edits did not touch any listed file.
- Local commit `7465ac0` not pushed yet — waiting on explicit user push approval.
