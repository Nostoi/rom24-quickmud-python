# Session Summary — 2026-05-30 — WIZ-049 FIXED (INV-027 PERS contract fully enforced)

## Scope

Continuation picking up **Next Task #1** from `SESSION_STATUS.md`: close **WIZ-049**,
the `do_force` TO_VICT half of the INV-027 (ACT-PERS-NAME-MASKING) cross-file
contract — the third and final PERS-leak sibling after WIZ-047 (TO_ROOM) and
WIZ-048 (`do_transfer` TO_VICT). Closed via the standard `rom-gap-closer` TDD flow.
**With WIZ-049 closed, the INV-027 PERS-masking contract is fully enforced** —
no known `$n`/`$N` name-leak sites remain across the act-family.

One code commit landed: `a667507a`.

## Outcome

### `WIZ-049` — ✅ FIXED (2.11.37, `a667507a`)

- **Python**: `mud/commands/imm_commands.py:do_force` — all four TO_VICT delivery
  sites (lines 339 `force all`, 354 `force players`, 369 `force gods`, 399 single
  target).
- **ROM C**: `src/act_wiz.c:4205` builds `sprintf(buf, "$n forces you to '%s'.", argument)`,
  delivered via `act(buf, ch, NULL, vch, TO_VICT)` at `:4228/4251/4274/4316` —
  `$n` = the forcer (`ch`), rendered through `PERS(ch, vch)` → `"someone"` when
  the victim cannot `can_see` the (invisible / wiz-invis) immortal. (`PERS`
  substitution at `src/comm.c:2289-2291`.)
- **Gap**: Python used `f"{char.name} forces you to '{command}'.\n\r"`
  unconditionally at all four sites, leaking a wiz-invis immortal's identity to
  every forced victim.
- **Fix**: each site now renders via `mud/world/vision.py:pers(char, vch)`
  (single-target: `pers(char, victim)`), with a function-local `from mud.world.vision import pers`
  at the top of `do_force` (import-cycle safe). Same helper the WIZ-047/048 and
  `act_format._pers` enforcements use.
- **Safety**: `gitnexus_impact` (target_uid `Function:mud/commands/imm_commands.py:do_force`)
  = **LOW** (0 direct callers in the graph — `do_force` is a top-level command
  dispatched by the interpreter, not called by other Python symbols).
  `gitnexus_detect_changes` confirmed scope = `do_force` (+ adjacent `do_peace`
  whose line numbers shifted) + the doc Sections.
- **Tests**: `tests/integration/test_act_wiz_command_parity.py::test_force_masks_invisible_immortal_name_for_nonseeing_victim`
  (invisible forcer → victim without detect-invis gets `"someone forces you to 'smile'."`)
  + `::test_force_shows_immortal_name_to_seeing_victim` (victim with DETECT_INVIS
  gets the real name). Exercises the single-target branch; the all/players/gods
  branches share the identical `pers(char, vch)` call. Failing test confirmed
  first (victim received the leaked `"Tyrant forces you to..."`); the seeing-victim
  guard passed pre-fix (proves the delivery path is live).

### INV-027 — fully enforced (milestone)

With WIZ-049 closed, the ACT-PERS-NAME-MASKING contract is enforced everywhere a
`$n`/`$N` is rendered to a per-recipient viewer:

| Path | Enforcement | Version |
|------|-------------|---------|
| `act_format` (`$n`/`$N`) | `mud/utils/act.py:_pers` → `can_see_character` | 2.11.34 |
| `_act_room` (TO_ROOM, `do_transfer` announces) | WIZ-047, `pers(char, person)` | 2.11.35 |
| `do_transfer` TO_VICT notify | WIZ-048, `pers(char, victim)` | 2.11.36 |
| `do_force` TO_VICT ×4 | WIZ-049, `pers(char, vch)` | 2.11.37 |

The only INV-027-adjacent item left open is the cross-cutting **ACT-FIRST-LETTER-CAP**
divergence (below).

### `ACT-FIRST-LETTER-CAP` — carried OPEN (→ future INV-028)

ROM `act_new` upper-cases `buf[0]` of every rendered line (`src/comm.c:2376-2379`);
the Python act-family does not. Invisible for already-capitalized names and "You";
bites ONLY when a masked `$n` lands at sentence start (ROM `"Someone …"`, Python
`"someone …"`). Right fix is a single capitalization step at the act-render
boundary. The WIZ-047/048/049 tests assert lowercase `"someone"` deliberately and
move in lockstep when this is closed. Filed in `ACT_WIZ_C_AUDIT.md` (WIZ-049 row)
+ the INV-027 tracker bullet; promote to INV-028 when picked up.

## Files Modified (code commit `a667507a`)

- `mud/commands/imm_commands.py` — `do_force` renders `$n` via `pers()` at all four TO_VICT sites + function-local import.
- `tests/integration/test_act_wiz_command_parity.py` — 2 WIZ-049 tests + `do_force` import.
- `docs/parity/ACT_WIZ_C_AUDIT.md` — WIZ-049 → ✅ FIXED.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-027: WIZ-049 FIXED + "fully enforced" note; header line updated.
- `CHANGELOG.md` — 2.11.37 section.
- `pyproject.toml` — 2.11.36 → 2.11.37.

(Not in the gap commit: this summary + `SESSION_STATUS.md`. The pre-existing
`.claude/skills/gitnexus/gitnexus-cli/SKILL.md` working-tree change predates the
session and was left untouched.)

## Test Status

- `tests/integration/test_act_wiz_command_parity.py::test_force_masks_*` /
  `test_force_shows_*` — 2/2 passing (failing-first confirmed).
- `tests/integration/test_act_wiz_command_parity.py` (full file) — 120 passed
  (116 base + 2 WIZ-048 transfer + 2 WIZ-049 force).
- Full suite — **4995 passed, 4 skipped, 0 failed** (4993 after WIZ-048 + 2 new
  WIZ-049 tests = 4995; zero regression).
- `ruff check mud/commands/imm_commands.py` — All checks passed. (The 4
  pre-existing `test_act_wiz_command_parity.py` lint errors at lines
  1081/1101/1138/1538 are unrelated and predate this work.)

## Next Steps

Cross-file invariants remains the standing pass. Concrete next options, in priority:

1. **`ACT-FIRST-LETTER-CAP` → INV-028** — promote to a stable cross-file ID; add
   the single act-render-boundary `buf[0]` capitalization step (`mud/utils/act.py`
   + the `imm_commands` `_act_room`/notify paths, or a shared render helper); flip
   the WIZ-047/048/049 lowercase `"someone"` assertions to `"Someone"` in lockstep.
   Now that all PERS sites are masked, this is the natural completion of the
   act-rendering parity.
2. **`VISION-002`** — the dark-gate same-room divergence (`vision.py` vs
   `src/handler.c:2638`; `HANDLER_C_AUDIT.md`). Larger scope; write a failing test first.
3. Fresh cross-file probe (affect ticks, position transitions, mob script
   triggers, group/follower chain).

## Outstanding / carried-open

- **`ACT-FIRST-LETTER-CAP`** (OPEN, → INV-028) — see above.
- **`VISION-002`** (OPEN) — dark-gate same-room divergence.
- Known **xdist flakes**: `test_combat_death.py`, `test_backstab_uses_position_and_weapon`
  — pass in isolation, can flake under some parallel worker groupings (RNG ordering);
  this session's full run had zero failures.
- pet-shop haggle / "now follows you" wrong-channel (INV-001 family, mailbox-only);
  `Character.pet` stale type annotation; `do_cast` object-targeting legs; converter hardening.
- Non-blocking (ROM-faithful): `pers`/`_act_room` → `can_see_character` consumes an
  RNG draw on the sneak branch (`src/handler.c:2646-2656`); findability note only.

## Commit / push state

- This session: `a667507a` (WIZ-049 fix) + the upcoming session-docs commit.
- **Local-only, NOT pushed**: `66758fd1` (WIZ-048) + `f84a1c47` (WIZ-048 docs) +
  `a667507a` (WIZ-049) + docs. WIZ-047 (`d7f88228` + `40a5e289`) was pushed to
  `origin/master` earlier when the user said "push". WIZ-048 + WIZ-049 await the
  user's say-so.

## Tooling note (session environment)

The Bash/Read/MCP output channels buffered heavily this session (long stretches of
empty returns, then recovery). Worked around by routing every check through temp
files + `python3` prints, writing execute-ready handoff docs at each risk point
(deleted once the channel recovered and the step completed), and re-verifying.
Every test/ruff/git/impact result quoted here was read from rendered output, not
assumed. **Process catch carried from WIZ-048**: `git show --name-only HEAD` after
every commit — the WIZ-047 commit silently dropped a staged file; WIZ-048 and
WIZ-049 both verified all 6 files landed.
