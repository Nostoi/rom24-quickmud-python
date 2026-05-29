# Session Summary — 2026-05-29 — CAST-003 + MAGIC-003 (MAGIC-002 family complete)

## Scope

Continued from the CAST-002 handoff. `SESSION_STATUS.md` named **CAST-003** as
the next task, with **MAGIC-003** the last residual of the MAGIC-002
affect-message family. Both were closed this session via the standard
gap-closer TDD flow (failing test → fix → tracker/changelog/version → single
commit). The advisor pass after MAGIC-003 surfaced a real out-of-scope
SINGLE-DELIVERY bug in `do_rescue`, filed durably as **FIGHT-029**. With these
two closures the MAGIC-002 affect-message family is **complete** (armor 2.11.20
→ bless 2.11.21 → CAST-002 2.11.22 → CAST-003 2.11.23 → MAGIC-003 2.11.24).

## Outcomes

### `CAST-003` — ✅ FIXED (2.11.23, `6551a743`)

- **Python**: `mud/commands/combat.py` (`do_cast` offensive branch)
- **ROM C**: `src/magic.c:471` (`TAR_OBJ_CHAR_OFF`) vs `:376` (`TAR_CHAR_OFFENSIVE`)
- **Gap**: ROM gives `TAR_OBJ_CHAR_OFF` (`curse`/`poison`) its own no-fight
  error — `"Cast the spell on whom or what?"` (the trailing "or what?"
  reflecting that an object is a legal operand) — distinct from
  `TAR_CHAR_OFFENSIVE`'s char-only `"Cast the spell on whom?"`. Python routed
  `offensive_character_or_object` through the same no-fight branch as `victim`,
  so both emitted `"Cast the spell on whom?"`.
- **Fix**: the offensive object/char no-fight branch in `do_cast` now returns
  `"Cast the spell on whom or what?"`; the `victim` (`TAR_CHAR_OFFENSIVE`)
  branch is unchanged.
- **Tests**: `tests/test_skills_spells_cast_listing.py::test_do_cast_offensive_obj_char_no_target_no_fight_still_errors`
  — tightened the CAST-002 guard from a `whom` substring check to the exact
  wording (fail-first verified: returned `"Cast the spell on whom?"` before the
  fix). The `TAR_CHAR_OFFENSIVE` magic-missile guard still asserts plain
  `"whom?"` (the other branch unchanged).

### `MAGIC-003` — ✅ FIXED (2.11.24, `95a6d776`)

- **Python**: `mud/skills/handlers.py` — `shield`, `sanctuary`, `blindness`,
  `weaken`
- **ROM C**: `src/magic.c:4326-4327` (`spell_shield`), `:4296-4297`
  (`spell_sanctuary`), `:888-889` (`spell_blindness`), `:4580-4581`
  (`spell_weaken`)
- **Gap**: these four affect handlers applied the affect correctly but
  delivered their victim line (`send_to_char` TO_VICT) and room broadcast
  (`act` TO_ROOM) by appending straight to `target.messages` /
  `occupant.messages`. Per `mud/utils/messaging.py` (DUPL-002) and AGENTS.md
  "Message Delivery", `char.messages` is a fallback for disconnected
  characters and tests only — a connected PC must receive via the async
  `send_to_char` task fired by `push_message` so the line reaches the live
  prompt immediately (ROM `write_to_buffer`). A raw `.append` stranded a room
  broadcast in a connected bystander's mailbox until the next command drained
  it (the differential harness, reading the descriptor, saw nothing).
- **Fix**: each leg now routes through `_send_to_char` (self/victim + the
  already-affected branch + the per-occupant room loop), mirroring the existing
  `fly`/`giant_strength` handlers. `_send_to_char` (`send_to_char_buffered`)
  keeps the mailbox fallback for disconnected/test chars, so the existing
  mailbox-reading affect tests stay green. INV-001 SINGLE-DELIVERY family.
- **Tests**: `tests/integration/test_magic_003_affect_message_channel.py` —
  8 parametrized cases. The connected-PC half (4) asserts the line lands on the
  connection's immediate async channel with the mailbox left empty (fail-first:
  4 failed before the fix — lines stranded in mailbox / not on async channel);
  the disconnected mailbox-fallback half (4) pre-passes, proving the fallback
  contract is preserved.

### `FIGHT-029` — filed (🔄 OPEN, `7d602d2f`) — `do_rescue` SINGLE-DELIVERY violation

- **Python**: `mud/commands/combat.py:do_rescue` (~263, `return message`) +
  `mud/skills/handlers.py:rescue` (7081-7091)
- **ROM C**: `src/fight.c` `do_rescue` (void; all output via `act()`/`send_to_char`)
- **Gap**: `rescue()` does `caster.messages.append(char_msg)` AND `do_rescue`
  returns it; the connection loop sends the return value AND drains
  `char.messages`, so a connected PC rescuer receives `"You rescue X!"` **twice**
  — the exact INV-001 shape fixed for `do_kill` (FIGHT-020) and `do_surrender`.
  The victim/room legs additionally use the raw mailbox (MAGIC-003
  wrong-channel shape). Surfaced by the advisor while closing MAGIC-003 (rescue
  sits directly above `sanctuary`). Filed in `FIGHT_C_AUDIT.md` (FIGHT-029) +
  INV-001 cross-ref; **not** folded into MAGIC-003 (separate gap). Fix:
  `do_rescue` returns `""`; migrate `rescue`'s three legs to
  `_push_message`/`_send_to_char`. Needs a connection-loop double-delivery test
  (template `test_kill_command_single_delivery.py` /
  `test_surrender_single_delivery.py`).

## Files Modified

- `mud/commands/combat.py` — `do_cast` offensive obj/char no-fight wording (CAST-003)
- `mud/skills/handlers.py` — `shield`/`sanctuary`/`blindness`/`weaken` channel migration (MAGIC-003)
- `tests/test_skills_spells_cast_listing.py` — tightened CAST-003 guard
- `tests/integration/test_magic_003_affect_message_channel.py` — new (8 tests)
- `docs/parity/MAGIC_C_AUDIT.md` — CAST-003 + MAGIC-003 → ✅ FIXED
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-029 row added (🔄 OPEN)
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-001 "Touched by" trail +
  FIGHT-029 cross-ref; status note → "⚠️ ENFORCED — one open violation"
- `CHANGELOG.md` — `[2.11.23]` (CAST-003) + `[2.11.24]` (MAGIC-003) Fixed entries
- `pyproject.toml` — 2.11.22 → 2.11.24

Commits: `6551a743` (CAST-003), `95a6d776` (MAGIC-003), `7d602d2f` (FIGHT-029 filing).

## Test Status

- `tests/test_skills_spells_cast_listing.py` — 15/15 (CAST-003).
- `tests/integration/test_magic_003_affect_message_channel.py` — 8/8 (MAGIC-003).
- Broad consumer net (skills/debuffs/cancellation/spec-funs/cast-dispatch/magic-002) — 216 passed.
- **Full suite**: **4973 passed, 4 skipped** (+8 vs prior 4965 from the new
  MAGIC-003 tests; CAST-003 tightened an existing test, no count change).
- `ruff check` on touched files: the 5 errors (handlers.py 672/1783/3518/3665/6298,
  combat.py 718 do_flee) are all **pre-existing**, none in edited regions; the
  new test file is clean.
- `gitnexus_detect_changes`: LOW risk, 0 affected processes for both commits
  (the `word_of_recall` flag on MAGIC-003 was a diff-boundary artifact — verified
  untouched). Index reindexed after each commit.

## Outstanding

- **`FIGHT-029` (OPEN)** — `do_rescue` SINGLE-DELIVERY double-delivers the
  rescuer line + wrong-channels the victim/room legs (INV-001 family). Closes
  cleanly with `rom-gap-closer FIGHT-029` (discard the return like `do_kill`;
  migrate `rescue`'s three legs to `_push_message`/`_send_to_char`).
- **Converter hardening** — `convert_skills_to_json.py` is lossy (drops the
  hand-added `cancellation`/`harm`); make it merge-not-replace. Warning
  documented in the script docstring (`86eee6ef`) as the interim guard.
- **Object targeting in `do_cast`** — the `TAR_OBJ_CHAR_*` object-target legs
  (`src/magic.c:502-506`, `:525-529`) and `TAR_OBJ_INV` still fall back to the
  caster; named-not-found returns `"They aren't here."` rather than ROM's
  `"You don't see that here."` (`:509`/`:532`). Deferred (MAGIC_C_AUDIT Scope Notes).
- **`SHOP-PET-002`** (open, `FIGHT_C_AUDIT.md`) — pet purchase should
  `create_mobile(pIndexData)` (fresh re-roll), not clone the template.
- **`test_combat_death.py` xdist flake** (carried) — seed RNG in the unit death tests.
- **`affect_flags` case-normalization** (diff-harness, deferred) — fix with the
  first flag-setting affect scenario.
- Stray uncommitted 1-line doc tweak to
  `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` (present across sessions;
  unrelated to parity — left uncommitted).

## Next Steps

The MAGIC-002 affect-message family is **complete**. The clearest next gap is
**FIGHT-029** (`do_rescue` SINGLE-DELIVERY — `rom-gap-closer FIGHT-029`), which
keeps the work in the INV-001 family already in context. Beyond that, the
per-file audit tracker is exhausted; the active pass remains cross-file
invariants (`docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`) — candidate areas:
affect ticks, position transitions, mob script triggers, group/follower chain.
A focused sweep for other return-value-plus-mailbox commands (the `do_rescue`
shape) would likely surface more INV-001 siblings.
