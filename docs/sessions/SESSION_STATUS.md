# Session Status — 2026-05-29 — MAGIC-002 bless message fixed; MAGIC-003 / CAST-002 filed

## Current State

- **Active mode**: closing the MAGIC-002 affect-message family (affect spells
  silent / wrong-channel on success when cast through `do_cast`). `armor`
  (2.11.20) and now `bless` (2.11.21) are done.
- **Last completed** (this session):
  - **`MAGIC-002` (bless instance)** ✅ FIXED (master 2.11.21, `47d6ce53`) — ROM
    `spell_bless` (`src/magic.c:836-865`) sends "You feel righteous." (TO_VICT) +
    `act("You grant $N the favor of your god.")` (TO_CHAR cross-target) on success,
    and "You are already blessed." / `act("$N already has divine favor.")` on the
    already-affected branch (which ROM also takes when the victim is fighting,
    `src/magic.c:840`). The Python `bless` handler was the one *genuinely silent*
    affect buff; it now mirrors ROM messaging. Object-target branch deferred
    (unreachable). Tests: `tests/integration/test_magic_002_bless_message.py` (5).
  - **Corrected the audit doc's premise** — most affect-buff handlers already use
    canonical `_send_to_char`; the "bless + shield sweep" was overstated. `bless`
    was the only truly-silent one.
  - **Filed `MAGIC-003`** (🔄 OPEN) — `shield`/`sanctuary`/`weaken`/`blindness`
    deliver via the divergent `char.messages.append` channel (wrong-channel, not
    silent; INV-001 family). Needs a connected-PC test.
  - **Filed `CAST-002`** (🔄 OPEN) — `do_cast` maps `character_or_object` to the
    offensive default, so the defensive `TAR_OBJ_CHAR_DEF` spells `bless` /
    `invisibility` / `remove curse` wrongly error "Cast the spell on whom?" on a
    no-arg self-cast instead of defaulting to self.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-29_MAGIC_002_BLESS_MESSAGE.md](SESSION_SUMMARY_2026-05-29_MAGIC_002_BLESS_MESSAGE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.21 |
| Tests | 4963 passed, 4 skipped (full suite, parallel, ~147s) |
| ROM C files audited | 43 / 43 (per-file pass complete; differential + cross-file invariants active) |
| Active focus | MAGIC-002 affect-message family (armor + bless done; MAGIC-003 / CAST-002 open) |

## Next Intended Task

Close **`CAST-002`** (`MAGIC_C_AUDIT.md`) — the only player-facing bug in the
residual set: a no-arg `cast bless` / `cast invis` / `cast 'remove curse'`
currently errors `"Cast the spell on whom?"` instead of defaulting to self, because
`do_cast` maps the `character_or_object` target string to the offensive default and
does not distinguish ROM's defensive `TAR_OBJ_CHAR_DEF` (no-arg → self,
`src/magic.c:514-519`) from offensive `TAR_OBJ_CHAR_OFF`. The fix likely splits the
skills.json target vocabulary (defensive vs offensive `character_or_object`) and
dispatches the defensive case to self. **Touches `do_cast` — run `gitnexus_impact`
first** (blast radius = every spell) and lean on the existing CAST-001 tests.

Then **`MAGIC-003`** — migrate `shield`/`sanctuary`/`weaken`/`blindness` room/self
messages off `char.messages.append` onto canonical `_send_to_char`/`broadcast_room`;
write a **connected-PC** delivery test (mailbox-only tests pass before the fix).

Also pending (carried): seed RNG in the `test_combat_death.py` unit death tests to
kill the xdist ordering flake; `SHOP-PET-002` (RNG-stream pet re-roll); the
diff-harness `affect_flags` case-normalization (fix with the first flag-setting
affect scenario).
