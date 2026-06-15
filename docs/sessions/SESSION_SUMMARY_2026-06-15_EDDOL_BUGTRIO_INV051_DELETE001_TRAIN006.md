# Session Summary — 2026-06-15 — Eddol bug-trio (INV-051 + DELETE-001 + TRAIN-006)

## Scope

A player reported three interrelated symptoms against a half-created character
named `Eddol`: (1) `do_train` crashed with an `IndexError` / error message when
training with no sessions left; (2) `Eddol` was loginable despite the player
never finishing creation (they quit at the password prompt); (3) typing
`delete` twice did not actually delete the character — it stayed loginable.

Root-cause analysis showed (2) was the upstream cause of (1): the Python nanny
persisted a **bare level-0 DB row** the instant a new player chose a password,
before any race/class/stats existed. An abandoned creation left that row on
disk, loginable, and `do_train` then crashed on its empty `perm_stat`. (3) was
an independent bug — `do_delete` unlinked a phantom JSON pfile path while the
canonical store is the `characters` DB row (INV-008). This session closed all
three; INV-051 (the deferred-persistence fix) was the final and structural one.

## Outcomes

### `INV-051` — ✅ ENFORCED (DEFER-PERSIST-UNTIL-CREATION-COMPLETE)

- **Python**: `mud/net/connection.py:_run_character_login` /
  `handle_connection_with_stream` / `handle_connection`;
  `mud/account/account_service.py:mark_character_active` (new public helper).
- **ROM C**: `src/nanny.c` — in-memory `CHAR_DATA` carries the crypted password
  from `CON_GET_NEW_PASSWORD` (`nanny.c:396-410`) through
  race/sex/class/alignment/weapon; the only disk write is `save_char_obj(ch)`
  at the end of `CON_READ_MOTD` (`nanny.c:~790`). A mid-creation link-drop
  leaves nothing on disk.
- **Gap**: the password phase called `create_account` → `create_character_record`,
  INSERTing a bare level-0 row before creation completed — the `Eddol` artefact.
- **Fix**: the password phase now builds a **transient in-memory account**
  (`SimpleNamespace(name, password_hash=hash_password(pw))`) and returns
  `is_new_character=True` with **no DB write**. Both connection handlers were
  reordered so a new character runs `_run_character_creation_flow` (which
  performs the single `create_character` INSERT, `level=1`, at creation end)
  **before** any `load_character` (calling `_select_character` first would fail
  with "Failed to load that character" — no row exists yet). The freshly-created
  character is flagged active via the new public `mark_character_active`, because
  the deferred path no longer routes through `login_with_host` (which used to set
  that marker) — keeping the name-phase `is_account_active` duplicate-login check
  consistent with returning logins.
- **Tests**: 2 — `tests/integration/test_inv051_deferred_persistence.py`
  (no DB row after name+confirm+password; transient account carries a verifiable
  password hash with nothing on disk). End-to-end handler reorder is
  regression-covered by `tests/test_account_auth.py`.

### `TRAIN-006` — ✅ FIXED (committed earlier this session, 409dd5d1)

- **Python**: `mud/skills/advancement.py` do_train stat branch.
- **ROM C**: `src/act_move.c:1781,1791` — `ch->perm_stat[stat]` is always a
  fixed `sh_int[MAX_STATS]`.
- **Fix**: normalize `perm_stat` to `MAX_STATS` length in the stat-train branch
  (mirroring ROM's fixed-length array) so a malformed/short `perm_stat` (an
  abandoned mid-creation row) no longer raises `IndexError`; the player now sees
  ROM's "You don't have enough training sessions." Resolved-by-INV — root cause
  is the bare-row persistence now closed under INV-051.
- **Tests**: `tests/integration/test_recall_train_commands.py::test_train_stat_with_empty_perm_stat_does_not_crash`.

### `DELETE-001` — ✅ FIXED (committed earlier this session, 3ba262c6)

- **Python**: `mud/account/account_manager.py:delete_character`;
  `mud/commands/player_config.py:do_delete`.
- **ROM C**: `src/act_comm.c:54-93` — save-then-`unlink` order.
- **Fix**: `do_delete` unlinked a non-existent pfile path (`player/Name`) while
  the canonical store is the `characters` DB row (INV-008). New
  `delete_character(name)` removes the DB row and drops the name from
  `character_registry`; `do_delete` calls it after `do_quit`.
- **Tests**: `tests/test_account_auth.py::test_delete_removes_character_from_canonical_store`.

## Files Modified (this turn — INV-051)

- `mud/net/connection.py` — transient-account password phase + both handlers
  reordered (creation-before-load) + `mark_character_active` on new-char path.
- `mud/account/account_service.py` — new public `mark_character_active`.
- `mud/account/__init__.py` — export `mark_character_active`.
- `tests/integration/test_inv051_deferred_persistence.py` — new (2 tests).
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-051 row (✅ ENFORCED).
- `CHANGELOG.md` — INV-051 Fixed entry (alongside DELETE-001, TRAIN-006).
- `pyproject.toml` — 2.14.113 → 2.14.114.

## Test Status

- `tests/integration/test_inv051_deferred_persistence.py` — 2/2 passing.
- Login/creation regression net (INV-051 + nanny + creation + telnet +
  websocket + connection-motd + account-auth + INV-009) — 144 passed, 1 skip.
- Full suite: 5807 passed, 4 skipped (pre-INV-051-active-marking run); re-run
  in progress to confirm the active-marking edit (no new tests).
- `ruff check .` — clean.

## Next Steps

Per-file audit tracker remains exhausted (43/43; P0/P1/P2 100%, P3 75% + 3 N/A)
— cross-file invariants / divergence-class sweep is the active pass. Open
follow-ups surfaced this session:

- **DELETE-002 🔄 OPEN** — `do_delete` lacks the ROM wiznet broadcast on
  self-deletion (`src/act_comm.c`). Local divergence, low priority.
- **STEAL-015 🔄 OPEN** (carried) — the steal *skill-handler*
  `skills/handlers.py:steal` has no `is_safe` gate at all.
- **INV-050** (carried) — message-half DONE (6 callers converged); bool
  retirement gated on an `is_safe_spell`-vs-ROM audit.
- **`mud/entrypoint.py`** is dead code (`prompt_account_creation` /
  `prompt_login` — no callers, not in `pyproject` scripts); a candidate for
  removal in a future hygiene pass.
- **Eddol data cleanup** — the existing corrupt `Eddol` DB row (and any
  `data/players/eddol.json`) is *forward-only* unaffected by INV-051; deleting
  it is destructive and **needs explicit user confirmation** before any action.
