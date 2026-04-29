# Session Summary — 2026-04-29 — `nanny.c` NANNY-008 + tracker flip

## Scope

Picked up at master `497db19` (v2.6.42) right after the `comm.c`
session wrapped. Scanned `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
for the next P1/P3 ⚠️ Partial row; chose `nanny.c` (40%) as the highest-
leverage remaining target — login flow is player-visible and the audit
doc (`docs/parity/NANNY_C_AUDIT.md`) was already at Phase 3 with one
remaining IMPORTANT gap (NANNY-008) closeable in a single TDD cycle.

Goal: close NANNY-008, document the architectural deferrals for
NANNY-009 (data-port task) and NANNY-010 (architectural carve-out), and
flip the tracker row to ✅ Audited paralleling the `comm.c` precedent.

## Outcomes

### `NANNY-008` — ✅ FIXED — pet follows owner into login room (IMPORTANT)

- **Python**: `mud/net/connection.py:broadcast_entry_to_room`.
- **ROM C**: `src/nanny.c:810-815` —
    ```c
    if (ch->pet != NULL) {
        char_to_room(ch->pet, ch->in_room);
        act("$n has entered the game.", ch->pet, NULL, NULL, TO_ROOM);
    }
    ```
- **Fix**: extended `broadcast_entry_to_room` so that after the owner's
  entry broadcast, if `char.pet` is not None and not already in
  `char.room`, the pet is moved via `mud.models.room.char_to_room` and a
  second TO_ROOM `"$n has entered the game."` broadcast fires for the
  pet (excluding the pet itself). Wires through the same `act_format`
  pipeline used for the owner so name/short_descr fallback is consistent.
- **Tests**: `tests/integration/test_nanny_login_parity.py::test_login_pet_follows_owner_into_room` (new). Existing `::test_login_broadcasts_entry_to_room` (NANNY-007) verified unchanged.
- **Commit**: `d884a63`.

### `NANNY-009` — 🔄 DEFERRED — `title_table` data port (IMPORTANT)

ROM `src/const.c:421-721` defines a `char *const title_table[MAX_CLASS][MAX_LEVEL+1][2]` — 4 classes × 61 levels × 2 sexes = **488 string entries**. The first-login block at `src/nanny.c:778-780` calls
`set_title(ch, sprintf("the %s", title_table[class][level][sex]))`.
Closing the gap is mechanically simple but the data block is large
enough that it deserves a dedicated session so the strings are reviewed
in isolation. Audit doc updated to reflect the deferral with explicit
data-port pointer.

### `NANNY-010` — ✅ DEFERRED-BY-DESIGN — full descriptor sweep (IMPORTANT)

ROM `src/nanny.c:307-352` (`CON_BREAK_CONNECT` Y-path) iterates
`descriptor_list` and `close_socket`s every entry whose
`character->name` (or `original->name` for switched immortals) matches
`ch->name`. The Python port's `SESSIONS` dict at
`mud/net/connection.py:1517` is keyed by character name, so the
dictionary invariant structurally enforces ROM's "close all duplicates"
guarantee — by definition there is at most one descriptor per name. The
switched-immortal branch is also covered: `do_switch`
(`mud/commands/imm_admin.py:198`) preserves the immortal's name as the
SESSIONS key, so a re-login attempt under that name still hits the
existing single-session disconnect path. Architectural twin of the
`comm.c:COMM-005` deferred-by-design carve-out. Audit doc updated.

## Files Modified

- `mud/net/connection.py` — `broadcast_entry_to_room` extended for pet follow-on (NANNY-008).
- `tests/integration/test_nanny_login_parity.py` — added `test_login_pet_follows_owner_into_room`.
- `docs/parity/NANNY_C_AUDIT.md` — flipped status header to ✅ Audited; NANNY-008 row → ✅ FIXED; NANNY-009 row → 🔄 DEFERRED with data-port rationale; NANNY-010 row → ✅ DEFERRED-BY-DESIGN with architecture rationale.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — `nanny.c` row flipped ⚠️ Partial 40% → ✅ Audited 90%; module list expanded; description references the audit doc + deferrals. Audit Statistics block: P3 row 2→3 audited / 8→7 partial / 69%→75%; Total row 15→16 audited / 17→16 partial / 69%→72%.
- `CHANGELOG.md` — Added `Fixed: NANNY-008` entry.
- `pyproject.toml` — 2.6.42 → 2.6.43 (one patch bump for NANNY-008; handoff commit reuses).

## Test Status

- `pytest tests/integration/test_nanny_login_parity.py` — 14/14 green.
- Full suite: `pytest tests/integration/` — 1374 passed, 10 skipped, 0 failed in 357s.
- `ruff check mud/net/connection.py` — clean (33 pre-existing repo-wide lint errors unchanged; none in modified region).

## Next Intended Task

`nanny.c` is done for parity-audit purposes (✅ Audited 90%). Two
known follow-ups:

1. **NANNY-009 dedicated session**: port the 488-entry `title_table`
   from `src/const.c:421-721` (`mage`, `cleric`, `thief`, `warrior` × levels 0..60 × M/F)
   into `mud/models/constants.py` (or a new `mud/data/title_table.py`),
   wire `set_title(ch, "the <title>")` into the first-login finalization
   path in `mud/net/connection.py`. ROM also re-applies titles on level-up
   (`src/update.c:73`) — handle that callsite in the same session.
2. **Next P1/P2 audit target**: pick from ⚠️ Partial rows — top
   candidates are `db.c + db2.c` (P1, 55%, world loading), `music.c`
   (P2, 60%), `const.c` (P3, 80%). `db.c` is highest-impact; `music.c`
   is smallest scope.

NANNY-010 stays deferred-by-design; revisit only if the asyncio
SESSIONS architecture is itself reworked for parity.
