# Session Summary — 2026-05-29 — WIZ-048 FIXED (INV-027 PERS contract — `do_transfer` TO_VICT half)

## Scope

Continuation picking up **Next Task #1** from `SESSION_STATUS.md`: close **WIZ-048**,
the `do_transfer` TO_VICT half of the INV-027 (ACT-PERS-NAME-MASKING) cross-file
contract (sibling of WIZ-047, closed in the prior session). Closed via the
standard `rom-gap-closer` TDD flow. Pushed WIZ-047's three commits to `origin/master`
at the start of the session. One sibling leak surfaced while reading `do_force`
and was filed durably as **WIZ-049** (OPEN); one cross-cutting capitalization
divergence (ACT-FIRST-LETTER-CAP → future INV-028) was filed as a note.

One code commit landed: `5cb1c4f8`.

## Outcome

### `WIZ-048` — ✅ FIXED (2.11.36, `5cb1c4f8`)

- **Python**: `mud/commands/imm_commands.py:282-290` (`do_transfer` victim notify).
- **ROM C**: `src/act_wiz.c:874-875` — after moving the victim, `do_transfer`
  notifies it via `act("$n has transferred you.", ch, NULL, victim, TO_VICT)`,
  where `$n` is the **immortal** (`ch`), looker = `victim`. ROM renders it through
  `PERS(ch, victim)` → `"someone has transferred you."` when the victim cannot
  `can_see` the (wiz-invis / invisible) immortal. (PERS substitution at
  `src/comm.c:2289-2291`: `case 'n': i = PERS(ch, to)`.)
- **Gap**: Python used the immortal's real name unconditionally
  (`char_name = getattr(char, "name", "Someone"); _send_to_char(victim, f"{char_name} has transferred you.")`),
  leaking a wiz-invis immortal's identity to every transferred victim.
- **Fix**: notify line now renders via `mud/world/vision.py:pers(char, victim)`
  (target=immortal, observer=victim) — the same helper WIZ-047 / `act_format._pers`
  use. Function-local import to avoid an import cycle. Distinct from WIZ-047
  (TO_ROOM mushroom-cloud/puff-of-smoke, `$n`=victim); this is the TO_VICT notify,
  `$n`=ch.
- **Safety**: `gitnexus_impact` (target_uid `Function:mud/commands/imm_commands.py:do_transfer`)
  = **LOW** — only `do_teleport` calls it (d=1, thin pass-through). `gitnexus_detect_changes`
  confirmed scope = `do_transfer` + `char_name` local only.
- **Tests**: `tests/integration/test_act_wiz_command_parity.py::test_transfer_masks_invisible_immortal_name_for_nonseeing_victim`
  (invisible immortal → victim without detect-invis gets `"someone has transferred you."`)
  + `::test_transfer_shows_immortal_name_to_seeing_victim` (victim with
  DETECT_INVIS gets the real name). Failing test confirmed first (victim received
  the leaked real name); the seeing-victim guard passed pre-fix, proving the
  delivery path is live (not an empty mailbox).

### `WIZ-049` — ❌ FILED OPEN (2.11.36 doc, `5cb1c4f8`)

- **Python**: `mud/commands/imm_commands.py:327,342,357,387` (`do_force`, four
  TO_VICT sites: `force all`, `force players`, `force gods`, single target).
- **ROM C**: `src/act_wiz.c:4205` builds `sprintf(buf, "$n forces you to '%s'.", argument)`
  then delivers via `act(buf, ch, NULL, vch, TO_VICT)` at `:4228,4251,4274,4316`
  — `$n` = the forcer, masked by `PERS(ch, vch)`.
- **Gap**: Python uses `f"{char.name} forces you to '{command}'.\n\r"` at all four
  sites, leaking a wiz-invis immortal's identity to forced victims.
- **Why filed, not fixed**: same INV-027 PERS contract, a different command/line —
  one gap = one test = one commit. Surfaced 2026-05-29 by the advisor's
  "grep the family for a third leak" check while closing WIZ-048. Filed in
  `ACT_WIZ_C_AUDIT.md` + cross-ref'd from INV-027. `rom-gap-closer`-able: failing
  test (forced victim without detect-invis → `"someone forces you to..."`; with
  → `"<Name> forces you to..."`), then `pers(char, vch)` at all four sites.

### `ACT-FIRST-LETTER-CAP` — ❌ FILED OPEN (note, → future INV-028)

ROM `act_new` upper-cases the first letter of every rendered line
(`src/comm.c:2376-2379`: `buf[0] = UPPER(buf[0])`, or `buf[2]` past a `{` color
code). The Python act-family (`mud/utils/act.py:act_format`,
`mud/commands/imm_commands.py:_act_room`, the WIZ-047/048 notify fixes) does NOT
replicate this. It is invisible for already-capitalized names and "You"; it bites
ONLY when `$n`/`$N` masks to `"someone"` at sentence start, where ROM emits
`"Someone …"` and Python emits `"someone …"`. Right fix is a single capitalization
step at the act-render boundary (not per-callsite). The WIZ-047/048 tests assert
lowercase deliberately and will move in lockstep when this is closed. Filed as a
note in `ACT_WIZ_C_AUDIT.md` (WIZ-049 row) + the INV-027 tracker bullet; promote
to a stable cross-file ID (INV-028 ACT-SENTENCE-CASE) when picked up.

## Files Modified (code commit `5cb1c4f8`)

- `mud/commands/imm_commands.py` — `do_transfer` notify renders `$n` via `pers(char, victim)`.
- `tests/integration/test_act_wiz_command_parity.py` — 2 WIZ-048 tests + imports (`do_transfer`, `AffectFlag`, `Sector`).
- `docs/parity/ACT_WIZ_C_AUDIT.md` — WIZ-048 → ✅ FIXED; added WIZ-049 (OPEN) row + ACT-FIRST-LETTER-CAP note.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-027: WIZ-047 + WIZ-048 FIXED, WIZ-049 the new Remaining (OPEN), ACT-FIRST-LETTER-CAP bullet. **Also repairs the INV-027 prose lost from the WIZ-047 commit** (`d7f88228` committed 5 files; that session's tracker edit did not land).
- `CHANGELOG.md` — 2.11.36 section.
- `pyproject.toml` — 2.11.35 → 2.11.36.

(Not in the gap commit: this summary + `SESSION_STATUS.md` — the session-handoff
docs. The pre-existing `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` working-tree
change predates this session and was left untouched.)

## Test Status

- `tests/integration/test_act_wiz_command_parity.py::test_transfer_masks_*` /
  `test_transfer_shows_*` — 2/2 passing (failing-first confirmed).
- Area suite (`test_act_wiz_command_parity.py` + `test_wiz047_*` + `test_inv027_*`)
  — 122 passed.
- Full suite — **4993 passed, 4 skipped, 0 failed** (4991 after WIZ-047 + 2 new
  WIZ-048 tests = 4993; zero regression).
- `ruff check` on the two changed source files — the only findings are 4
  pre-existing test-file lint errors (lines 1081/1101/1138/1538, confirmed present
  on the clean tree via stash round-trip); my added code introduced zero new lint.

## Next Steps

Cross-file invariants remains the standing pass. Concrete next options, in priority:

1. **`WIZ-049`** (`do_force` four TO_VICT `"$n forces you to..."` leaks) — the
   newly-surfaced third sibling, same INV-027 contract. `rom-gap-closer`-able, one
   commit. With WIZ-047 + WIZ-048 + WIZ-049 all closed, the INV-027 PERS contract
   is fully enforced across `act_format`, `_act_room` (TO_ROOM), `do_transfer`
   (TO_VICT), and `do_force` (TO_VICT).
2. **`ACT-FIRST-LETTER-CAP` → INV-028** — promote to a stable cross-file ID and
   add the single act-render-boundary capitalization step; update the WIZ-047/048
   (and WIZ-049, once closed) lowercase `"someone"` assertions to `"Someone"` in
   lockstep.
3. **`VISION-002`** — the dark-gate same-room divergence (`vision.py` vs
   `src/handler.c:2638`; `HANDLER_C_AUDIT.md`). Larger scope; write a failing test first.
4. Fresh cross-file probe (affect ticks, position transitions, mob script
   triggers, group/follower chain).

## Outstanding / carried-open

- **`WIZ-049`** (NEW, OPEN) — see above.
- **`ACT-FIRST-LETTER-CAP`** (NEW, OPEN, → INV-028) — see above.
- **Process note**: the WIZ-047 commit (`d7f88228`) staged 6 files but committed
  only 5 — the `CROSS_FILE_INVARIANTS_TRACKER.md` update silently did not land.
  Repaired in this WIZ-048 commit. Lesson: after `git commit`, verify the file
  list matches what was staged (this session does so via `git show --name-only`).
- Known **xdist flakes**: `test_combat_death.py`, `test_backstab_uses_position_and_weapon`
  — pass in isolation, can flake under some parallel worker groupings (RNG ordering).
- pet-shop haggle / "now follows you" wrong-channel (INV-001 family, mailbox-only);
  `Character.pet` stale type annotation; `do_cast` object-targeting legs; converter hardening.
- Non-blocking (ROM-faithful): `pers`/`_act_room` → `can_see_character` consumes an
  RNG draw on the sneak branch (`src/handler.c:2646-2656`); findability note only.

## Tooling note (session environment)

The Bash/Read/MCP output channels buffered intermittently again (empty returns,
then recovery — same mode as recent sessions). Worked around by routing reads
through temp files + `python3` prints and re-verifying. Every test/ruff/git result
quoted here was read from rendered output, not assumed.
