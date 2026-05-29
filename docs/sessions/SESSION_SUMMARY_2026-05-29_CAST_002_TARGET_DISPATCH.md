# Session Summary — 2026-05-29 — CAST-002 do_cast TAR_OBJ_CHAR_DEF self-default

## Scope

Continued from the MAGIC-002 bless handoff. `SESSION_STATUS.md` named
**CAST-002** as the next task — the only player-facing bug in the residual
MAGIC-002 affect-message family: a no-arg `cast bless` / `cast invis` /
`cast 'remove curse'` errored `"Cast the spell on whom?"` instead of
self-casting. This session closed it via the standard gap-closer TDD flow
(failing test → fix → tracker/changelog → single commit), then filed the
two divergences surfaced while doing so.

## Outcomes

### `CAST-002` — ✅ FIXED (2.11.22)

- **Python**: `mud/commands/combat.py` (`do_cast` target dispatch),
  `mud/scripts/convert_skills_to_json.py`, `data/skills.json`,
  `mud/mob_cmds.py`
- **ROM C**: `src/magic.c:514-519` (`TAR_OBJ_CHAR_DEF`) vs `:466-473`
  (`TAR_OBJ_CHAR_OFF`); `src/const.c` per-spell `TAR_*`
- **Gap**: ROM has two distinct object/character target types that differ by
  their **no-argument default**: `TAR_OBJ_CHAR_DEF` defaults to **self**;
  `TAR_OBJ_CHAR_OFF` defaults to `ch->fighting` (errors if not fighting). The
  Python skill-conversion **collapsed both** into one `"character_or_object"`
  string, and `do_cast` routed that single string through the *offensive*
  default. So the three defensive object/char spells — `bless`, `invisibility`,
  `remove curse` (all `TAR_OBJ_CHAR_DEF` in `src/const.c`) — wrongly demanded a
  target on a no-arg self-cast.
- **Fix**: restored ROM's 1:1 `TAR_*` mapping by splitting the JSON target
  vocabulary:
  - `convert_skills_to_json.py` now emits `defensive_character_or_object`
    (`TAR_OBJ_CHAR_DEF`) and `offensive_character_or_object`
    (`TAR_OBJ_CHAR_OFF`).
  - `data/skills.json` patched **by spell name in place** for the 5 affected
    spells (3 defensive, 2 offensive) — **not** regenerated (the converter is
    lossy; see Outstanding).
  - `do_cast` routes the defensive string with `"friendly"` (self default,
    `src/magic.c:514-519`) and the offensive string with `"victim"` (fighting
    default — **byte-identical** to prior behavior, so `curse`/`poison` are
    untouched).
  - `mob_cmds._TARGET_STRINGS` maps both new strings (ROM `do_mpcast` collapses
    DEF/OFF identically, `src/mob_cmds.c:1060-1065`); the legacy
    `character_or_object` key is retained for backward compatibility.
  - `magic_items._resolve_target_kind` docstring updated to the new vocabulary
    (brandish's unsupported-kind `else` branch is unaffected).
- **Tests**: `tests/test_skills_spells_cast_listing.py` (CAST-001's home file) —
  `test_do_cast_defensive_obj_char_no_target_defaults_to_self` (fail-first
  verified: errored `"Cast the spell on whom?"` before the fix) + an
  offensive-unchanged guard `test_do_cast_offensive_obj_char_no_target_no_fight_still_errors`
  (asserts on the `whom` substring so it survives the future CAST-003 fix).

### `CAST-003` — filed (🔄 OPEN) — offensive obj/char no-fight error wording

- **Python**: `mud/commands/combat.py` (`do_cast` offensive branch).
- **ROM C**: `src/magic.c:471` (`TAR_OBJ_CHAR_OFF` → `"Cast the spell on whom
  or what?"`) vs `:376` (`TAR_CHAR_OFFENSIVE` → `"Cast the spell on whom?"`).
- **Gap**: Python routes `offensive_character_or_object` through the same
  branch as `"victim"`, so `curse`/`poison` emit `"Cast the spell on whom?"`
  instead of ROM's `"Cast the spell on whom or what?"`. Left byte-identical
  during CAST-002 on purpose, to keep that a clean single-gap commit (per
  advisor). Filed in `docs/parity/MAGIC_C_AUDIT.md`.

### Tooling: `convert_skills_to_json.py` is lossy (hardening note added)

- The converter only emits the ~132 skills parseable from `src/const.c`, but
  `data/skills.json` has **134** entries — hand-augmented with `cancellation`,
  `harm`, … that are not in/parseable from `const.c`. A straight regeneration
  silently drops them (verified: regen produced 132 skills, missing both). The
  CAST-002 mapping change was therefore applied by spell name in place. Added a
  prominent `⚠️ LOSSY` warning to the converter's module docstring documenting
  the regenerate-to-scratch-and-`diff` workflow (commit `86eee6ef`). Genuine
  tooling-hardening (merge-not-replace) is left as Outstanding.

## Files Modified

- `mud/commands/combat.py` — `do_cast` splits defensive/offensive object/char dispatch (CAST-002)
- `mud/scripts/convert_skills_to_json.py` — split target mapping + `⚠️ LOSSY` docstring warning
- `data/skills.json` — 5 spell `target` values split (bless/invis/remove curse → defensive; curse/poison → offensive)
- `mud/mob_cmds.py` — `_TARGET_STRINGS` maps the two new strings (DEF/OFF collapse retained)
- `mud/commands/magic_items.py` — `_resolve_target_kind` docstring vocabulary
- `tests/test_skills_spells_cast_listing.py` — 2 regression tests (defensive self-default + offensive guard)
- `tests/integration/test_magic_002_bless_message.py` — refreshed now-stale CAST-002 rationale comment
- `tests/integration/test_mob_cmds_cast.py` — refreshed stale JSON-string comment
- `docs/parity/MAGIC_C_AUDIT.md` — CAST-002 → ✅ FIXED (2.11.22); CAST-003 row added (🔄 OPEN)
- `CHANGELOG.md` — `## [2.11.22]` Fixed entry
- `pyproject.toml` — 2.11.21 → 2.11.22

Commits: `835755b3` (`fix(parity)` CAST-002), `86eee6ef` (`docs(parity)` converter warning).

## Test Status

- `pytest tests/test_skills_spells_cast_listing.py` — 17/17 passing (incl. the 2 new).
- Broad consumer net (`test_spell_casting`, `test_mob_cmds_cast`,
  `test_magic_002_bless_message`, `test_skill_registry`, `test_skill_conversion`,
  `test_skills_learned`, `test_practice`, `test_advancement`, `test_consumables`) —
  125 passed.
- **Full suite** (run because `data/skills.json` is loaded by all tests):
  **4965 passed, 4 skipped** (~568s serial; +2 vs the prior 4963 from the two
  new CAST-002 tests).
- `ruff check` on touched files: zero **new** errors (baseline HEAD had the same
  15 pre-existing issues in `combat.py`/`magic_items.py` — untouched).
- `gitnexus_detect_changes`: LOW risk, 0 affected processes; changed symbols =
  `do_cast`/`_find_in_room`, `_TARGET_STRINGS`, `target_mapping`, audit sections,
  the two refreshed test comments. Index reindexed post-commit.

## Outstanding

- **`CAST-003` (OPEN)** — `do_cast` offensive obj/char branch should emit
  `"Cast the spell on whom or what?"` (`src/magic.c:471`) for `curse`/`poison`,
  not `"Cast the spell on whom?"`. Low value (wording only). When fixed, update
  the `test_do_cast_offensive_obj_char_no_target_no_fight_still_errors` guard.
- **`MAGIC-003` (OPEN)** — migrate `shield`/`sanctuary`/`weaken`/`blindness`
  room/self messages off `char.messages.append` onto canonical
  `_send_to_char`/`broadcast_room`; needs a **connected-PC** delivery test
  (mailbox-only tests pass before the fix). INV-001 SINGLE-DELIVERY family.
- **Converter hardening** — `convert_skills_to_json.py` is lossy (drops the
  hand-added `cancellation`/`harm`); make it merge-not-replace (or parse the
  augmented entries) so a future regen is safe. Warning documented in the
  script docstring (`86eee6ef`) as the interim guard.
- **Object targeting in `do_cast`** — the `TAR_OBJ_CHAR_*` object-target legs
  (`src/magic.c:502-506`, `:525-529`) and `TAR_OBJ_INV` still fall back to the
  caster; named-not-found returns the char-only `"They aren't here."` rather
  than ROM's `"You don't see that here."` (`:509`/`:532`). Deferred (Scope Notes).
- **`SHOP-PET-002`** (open, `FIGHT_C_AUDIT.md`) — pet purchase should
  `create_mobile(pIndexData)` (fresh re-roll), not clone the template.
- **`test_combat_death.py` xdist flake** (carried) — seed RNG in the unit death tests.
- **`affect_flags` case-normalization** (diff-harness, deferred) — fix with the
  first flag-setting affect scenario.
- Stray uncommitted 1-line doc tweak to
  `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` (present across sessions;
  unrelated to parity — left uncommitted).

## Next Steps

The MAGIC-002 affect-message family is now down to two low-value residuals:
**CAST-003** (offensive obj/char error wording — trivial, one string + guard
update) and **MAGIC-003** (channel-migration sweep — needs a connected-PC
delivery test). Either closes cleanly with `rom-gap-closer`. Beyond that, the
per-file tracker is exhausted; the active pass remains cross-file invariants
(`docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`) — candidate areas: affect
ticks, position transitions, mob script triggers, group/follower chain.
