# Session Summary — 2026-05-29 — WIZ-047 FIXED (INV-027 PERS contract — `_act_room` half)

## Scope

Continuation picking up **Next Task #1** from `SESSION_STATUS.md`: close
**WIZ-047**, the remaining `imm_commands._act_room` half of the INV-027
(ACT-PERS-NAME-MASKING) cross-file contract. Closed via the standard
`rom-gap-closer` TDD flow (failing test first → fix → green → trackers →
changelog → version → single commit). One sibling leak surfaced while reading
`do_transfer` and was filed durably as **WIZ-048** (OPEN) rather than folded in.

One code commit landed: `d7f88228` (plus a separate docs-handoff commit).

## Outcome

### `WIZ-047` — ✅ FIXED (2.11.35, `d7f88228`)

- **Python**: `mud/commands/imm_commands.py:_act_room` (line 475).
- **ROM C**: `src/act_wiz.c:870,873` — `do_transfer` announces the mushroom-cloud
  / puff-of-smoke lines via `act("$n ...", victim, NULL, NULL, TO_ROOM)`, so `$n`
  (the transferred **victim**) is rendered per-recipient through
  `PERS(victim, witness)` → `"someone"` for any witness who cannot `can_see` the
  victim. The line is still delivered to every witness; only the **name** is
  masked (ROM masks, it does not suppress).
- **Gap**: `_act_room` did `message.replace("$n", char.name)` once and sent the
  same string to every room occupant — no PERS masking — so an invisible /
  wiz-invis transferred immortal leaked its real name to non-seeing witnesses.
- **Fix**: `_act_room` now renders `$n` per-recipient via
  `mud/world/vision.py:pers(char, person)` (the same helper the 2.11.34
  `act_format._pers` enforcement and the combat path use), masking to
  `"someone"` for non-seeing witnesses while still delivering the line; the actor
  is skipped (ROM `act()` TO_ROOM does not echo to the subject). Function-local
  import to avoid an import cycle. Distinct from WIZ-045/046, which gate the
  *whole* bamf line on `invis_level` via `_act_room_invis_gated` (already
  correct).
- **Safety**: `gitnexus_impact` (target_uid `Function:mud/commands/imm_commands.py:_act_room`)
  = **LOW** — 1 direct caller `do_transfer` (d=1), transitive `do_teleport`
  (d=2). Corroborated by grep (the two `_act_room` calls are at
  `imm_commands.py:275,280`, both inside `do_transfer`).
- **Tests**: `tests/integration/test_wiz047_transfer_pers_name_masking.py` (2) —
  invisible subject → seeing witness (DETECT_INVIS) gets the real name,
  non-seeing witness gets `"someone"`, the subject gets nothing; plus a
  visible-subject regression guard (real name reaches all witnesses). Failing
  test confirmed to fail for the right reason before the fix (non-seeing witness
  received `"Wraith arrives..."` instead of `"someone arrives..."`).

### `WIZ-048` — ❌ FILED OPEN (2.11.35 doc, `d7f88228`)

- **Python**: `mud/commands/imm_commands.py:282-285`.
- **ROM C**: `src/act_wiz.c:874-875` — after moving the victim, `do_transfer`
  notifies it via `act("$n has transferred you.", ch, NULL, victim, TO_VICT)`,
  where `$n` is the **immortal** (`ch`), looker = `victim`. ROM renders it
  through `PERS(ch, victim)` → `"someone has transferred you."` when the victim
  cannot see the (wiz-invis / invisible) immortal.
- **Gap**: Python uses the immortal's real name unconditionally
  (`char_name = getattr(char, "name", "Someone"); _send_to_char(victim, f"{char_name} has transferred you.")`),
  leaking a wiz-invis immortal's identity to the transferred victim.
- **Why filed, not fixed**: same INV-027 PERS contract but a **different line**
  (TO_VICT, `$n` = ch) than the TO_ROOM lines WIZ-047 covers. One gap = one test
  = one commit — surfaced 2026-05-29 while reading `do_transfer` for WIZ-047.
  Filed in `ACT_WIZ_C_AUDIT.md` (Phase 3) + cross-referenced from INV-027.
  `rom-gap-closer`-able: failing test (victim without detect-invis →
  `"someone has transferred you."`; with detect-invis → `"<Name> ..."`), then
  render via `pers(char, victim)`.

## Files Modified (code commit `d7f88228`)

- `mud/commands/imm_commands.py` — `_act_room` renders `$n` per-recipient via `pers`.
- `tests/integration/test_wiz047_transfer_pers_name_masking.py` — new (2 tests).
- `docs/parity/ACT_WIZ_C_AUDIT.md` — WIZ-047 → ✅ FIXED; added WIZ-048 (OPEN) row.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-027: WIZ-047 closed,
  WIZ-048 now the Remaining (OPEN); "Touched by" trail extended.
- `CHANGELOG.md` — 2.11.35 section.
- `pyproject.toml` — 2.11.34 → 2.11.35.

(Not in the gap commit: `docs/sessions/SESSION_STATUS.md` + this summary — the
session-handoff docs. The pre-existing `.claude/skills/gitnexus/gitnexus-cli/SKILL.md`
working-tree change predates this session and was left untouched.)

## Test Status

- `tests/integration/test_wiz047_transfer_pers_name_masking.py` — 2/2 passing
  (and confirmed failing first, for the right reason).
- **Full suite** (parallel, on the committed tree with the fix in place):
  **4991 passed, 4 skipped, 0 failed** (~124s wall-clock). Math reconciles:
  4989 baseline-passed (2.11.34) + 2 new WIZ-047 tests = 4991. Zero failures,
  zero regression. (A mid-session partial run during a `git stash`/`pop` dance
  briefly showed 2 combat-test failures; that was the fix temporarily reverted
  by the stash, not a real flake — the authoritative full run on the committed
  tree is clean.)
- `ruff check` on `imm_commands.py`, the new test — clean. (`mud/world/vision.py`
  carries 3 pre-existing ruff findings — I001 import-sort + 2× UP038
  `isinstance` tuple — untouched by this gap; not introduced here.)
- Scope confirmed via `gitnexus_detect_changes` (LOW risk; changed symbols =
  `imm_commands._act_room` + `formatted` local + the two doc Sections;
  `affected_processes: []`). Code commit `d7f88228` contains the 5 gap files;
  the docs-handoff commit (`SESSION_SUMMARY` + `SESSION_STATUS`) is separate.

## Next Steps

Cross-file invariants remains the standing pass (per-file audit tracker has no
⚠️ Partial / ❌ Not Audited rows). Concrete next options, in priority:

1. **`WIZ-048`** (`do_transfer` `"$n has transferred you."` TO_VICT leak) — the
   newly-surfaced sibling, same INV-027 contract. `rom-gap-closer`-able, one
   commit. With WIZ-047 + WIZ-048 both closed, the INV-027 PERS contract is
   fully enforced across `act_format`, the imm `_act_room` TO_ROOM path, AND the
   `do_transfer` TO_VICT path.
2. **`VISION-002`** — the dark-gate same-room divergence (`vision.py` vs
   `src/handler.c:2638`; `HANDLER_C_AUDIT.md`). Larger scope; write a failing
   test first.
3. Fresh cross-file probe in an area not yet covered by an INV row (affect ticks,
   position transitions, mob script triggers, group/follower chain).

## Outstanding / carried-open

- **`WIZ-048`** (NEW, OPEN) — see above.
- Known **xdist flakes** (documented carried-open): `test_combat_death.py`,
  `test_backstab_uses_position_and_weapon` — pass in isolation, can flake under
  some parallel worker groupings (RNG ordering). This session's full run had
  **zero** failures (4991 passed); they did not surface.
- pet-shop haggle / "now follows you" wrong-channel (INV-001 family, mailbox-only);
  `Character.pet` stale type annotation; `do_cast` object-targeting legs;
  converter hardening.
- Non-blocking (ROM-faithful, not a gap): `_pers`/`_act_room` → `can_see_character`
  consumes an RNG draw on the sneak branch (`src/handler.c:2646-2656`); most
  reachable via a sneaking player moving. Recorded for findability if a future
  seeded `act_format`/`_act_room`-downstream assertion ever flakes.

## Tooling note (session environment)

The Bash/Read/MCP/advisor output channels buffered intermittently this session
(same failure mode as the INV-027-prereq session — calls returning empty, then
recovering). Worked around by routing reads through temp files + `python3`
prints and re-running. Verification was still done honestly: every test/ruff/git
result quoted here was read from a file whose content rendered. No claim of
"passing" was made without reading the actual summary line.
