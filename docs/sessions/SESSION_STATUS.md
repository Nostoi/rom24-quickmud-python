# Session Status — 2026-05-29 — CAST-002 fixed (do_cast self-default); CAST-003 filed

## Current State

- **Active mode**: closing out the MAGIC-002 affect-message family. `armor`
  (2.11.20), `bless` (2.11.21), and now **CAST-002** (2.11.22 — the family's
  only player-facing bug) are done. Two low-value residuals remain
  (CAST-003, MAGIC-003).
- **Last completed** (this session):
  - **`CAST-002`** ✅ FIXED (master 2.11.22, `835755b3`) — a no-arg
    `cast bless` / `cast invis` / `cast 'remove curse'` errored
    `"Cast the spell on whom?"` instead of self-casting. ROM splits the two
    object/char target types by no-arg default (`TAR_OBJ_CHAR_DEF` → self,
    `src/magic.c:514-519`; `TAR_OBJ_CHAR_OFF` → fighting victim, `:466-473`),
    but the skill-converter collapsed both into one `"character_or_object"`
    string and `do_cast` applied the offensive default to all five. Fix splits
    the JSON vocabulary into `defensive_`/`offensive_character_or_object`
    (restoring ROM's 1:1 `TAR_*` mapping); `do_cast` routes defensive→self,
    offensive→fighting (byte-identical; `curse`/`poison` unchanged). Tests:
    `tests/test_skills_spells_cast_listing.py` (defensive self-default + offensive guard).
  - **Converter hardening note** (`86eee6ef`) — `convert_skills_to_json.py` is
    lossy (emits 132 of `data/skills.json`'s 134 skills, dropping the
    hand-added `cancellation`/`harm`); added a `⚠️ LOSSY` docstring warning and
    the regenerate-to-scratch-and-`diff` workflow. CAST-002's JSON edit was
    applied by spell name in place, not regenerated.
  - **Filed `CAST-003`** (🔄 OPEN) — offensive obj/char no-fight error should be
    `"Cast the spell on whom or what?"` (`src/magic.c:471`), not
    `"Cast the spell on whom?"`. Left byte-identical in CAST-002 to keep that a
    clean single-gap commit.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-29_CAST_002_TARGET_DISPATCH.md](SESSION_SUMMARY_2026-05-29_CAST_002_TARGET_DISPATCH.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.22 |
| Tests | 4965 passed, 4 skipped (full suite, serial, ~568s) |
| ROM C files audited | 43 / 43 (per-file pass complete; differential + cross-file invariants active) |
| Active focus | MAGIC-002 affect-message family residuals (CAST-003 + MAGIC-003 open) |

## Next Intended Task

Close **`CAST-003`** (`MAGIC_C_AUDIT.md`) — trivial: give `do_cast`'s offensive
object/char branch its own no-fight error string `"Cast the spell on whom or
what?"` (`src/magic.c:471`) so `curse`/`poison` match ROM, then update the
`test_do_cast_offensive_obj_char_no_target_no_fight_still_errors` guard (which
currently asserts on the `whom` substring to survive this change).

Then **`MAGIC-003`** — migrate `shield`/`sanctuary`/`weaken`/`blindness`
room/self messages off `char.messages.append` onto canonical
`_send_to_char`/`broadcast_room`; write a **connected-PC** delivery test
(mailbox-only tests pass before the fix). INV-001 SINGLE-DELIVERY family.

Lower priority / carried: harden `convert_skills_to_json.py` to merge-not-replace
(currently lossy); `SHOP-PET-002` (RNG-stream pet re-roll); seed RNG in the
`test_combat_death.py` unit death tests to kill the xdist ordering flake; the
diff-harness `affect_flags` case-normalization (fix with the first flag-setting
affect scenario). The per-file audit tracker is exhausted — cross-file
invariants (`CROSS_FILE_INVARIANTS_TRACKER.md`) remains the standing pass.
