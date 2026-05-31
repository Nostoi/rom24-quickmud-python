# Session Summary — 2026-05-31 — In-Game Bug Fixes (training, mana, room flags)

## Scope

Departed from the cross-file invariants probe pass to triage three bugs the
user found by **actually playing the MUD** (creating an elf mage, training,
casting magic missile, entering a dark school room). Each was verified against
ROM C before any change. Three turned into clean one-gap/one-test/one-commit
closures; a fourth (room flags) turned out to be a large systemic bug and was
filed durably for its own session. A theme emerged worth recording (see below).

## Outcomes

### NANNY-015 — ✅ FIXED (new PC starts with 3 training sessions, not 18)

- **ROM C**: `src/nanny.c:776-777` — the `CON_READ_MOTD` level-0 block sets
  `ch->train = 3; ch->practice = 5;` unconditionally for every new PC,
  overwriting the `(40 - points + 1)/2` formula at `nanny.c:684` (dead code —
  never survives to play).
- **Python**: `mud/account/account_service.py:CreationSelection.train_value`
- **Fix**: `train_value()` now returns 3. It had ported only the dead formula,
  giving an elf (race points 5) `(40-5+1)//2 = 18`; `practice` was already
  correctly hardcoded to 5 (the mismatched half of the pair was the tell).
- **Tests**: `tests/integration/test_nanny_login_parity.py::test_new_character_starts_with_three_training_sessions` (1, green).

### TRAIN-002 — ✅ FIXED (training a stat costs 1 session, not 2)

- **ROM C**: `src/act_move.c:1665-1799` (`do_train`) — `cost = 1;` set once;
  every `if (attr_prime == STAT_X) cost = 1;` branch is a no-op and there is
  **no** `else cost = 2;`. All stats (and hp/mana) cost exactly 1.
- **Python**: `mud/commands/advancement.py:264-296`
- **Fix**: removed the invented `cost = 1 if prime else 2` and the dead
  prime-stat map; `cost` is unconditionally 1.
- **Tests**: `tests/integration/test_recall_train_commands.py::test_train_nonprime_stat_costs_one_session` (new); corrected `::test_train_int_increases_stat` which had asserted the cost=2 divergence.

### CAST-008 — ✅ FIXED (failed cast costs half mana, not 1.5×)

- **ROM C**: `src/magic.c:551-558` — deducts *either* `mana/2` (failure) *or*
  `mana` (success), never both, and nothing before the concentration roll.
- **Python**: `mud/commands/combat.py:do_cast`
- **Fix**: removed the upfront full `char.mana -= mana_cost`; failure now
  deducts `mana_cost//2` and success deducts the full `mana_cost`. A level-1
  magic missile (cost 50) previously cost 75 on failure (100→25) instead of 25
  (100→75) — exactly the user's "costs 75 of my 100 mana" report.
- **Note**: originally mis-triaged (by both me and the advisor) as ROM-correct;
  reading the deduction **order** (full upfront + half on fail) revealed the bug.
- **Tests**: `tests/integration/test_spell_casting.py::TestCastManaDeductionCAST008` (2, green).

### TRAIN-003 — ✅ FIXED (train requires an ACT_TRAIN mob in the room)

- **ROM C**: `src/act_move.c:1643-1656` — `do_train` scans the room for an
  `IS_NPC(mob) && IS_SET(mob->act, ACT_TRAIN)` mob; if none, "You can't do that
  here." before any session/stat handling.
- **Python**: `mud/commands/advancement.py:_find_trainer`, `do_train`
- **Fix**: re-enabled the `_find_trainer` gate (was commented out behind a stale
  "no trainer mobs exist yet" TODO) and added ROM's `IS_NPC` guard (PC `act`
  PlayerFlag bits can alias `ACT_TRAIN`=0x200). Train tests updated to place an
  ACT_TRAIN NPC (they had asserted train-works-without-trainer).
- **Tests**: `tests/integration/test_recall_train_commands.py::test_train_without_trainer_in_room_fails` (new).

### DB-001 / INV-032 — 🔄 FILED, DEFERRED (room flags dropped game-wide)

- **ROM C**: `src/db.c:1149-1151` (`load_rooms`) — room header is
  `<area-number(discard)> <room_flags via fread_flag> <sector_type>`.
- **Python**: `mud/loaders/room_loader.py:41` reads `int(tokens[0])` (the
  discarded area-number, always 0) for `room_flags` and can't decode letter
  bitvectors anyway. **Every room in every area loads flagless** — no
  ROOM_DARK / ROOM_SAFE / ROOM_NO_RECALL / ROOM_LAW / access-control flags. The
  converter baked the zeros into all 52 `data/areas/*.json` (0/~3,800 rooms
  flagged; all 52 regenerate byte-identical → JSONs are faithful, no hand-edits).
- **Surfaced**: elf could read the school "Darkened Room" (vnum 3720, ROM `ADR`
  = ROOM_DARK|ROOM_INDOORS|ROOM_NEWBIES_ONLY); infravision (correct) masked the
  missing darkness during initial triage.
- **Filed**: `DB-001` in `DB_C_AUDIT.md` (root cause + fix plan), `INV-032` in
  `CROSS_FILE_INVARIANTS_TRACKER.md` (room-flags-survive-load contract, ❌ OPEN).
- **Why deferred**: the fix (loader correction + regenerate all 52 JSONs +
  triage the test fallout when SAFE/NO_RECALL/DARK switch on game-wide) is a
  different size class and warrants its own session. User chose to defer.

## Files Modified

- `mud/account/account_service.py` — `train_value()` returns 3 (NANNY-015).
- `mud/commands/advancement.py` — `do_train` cost always 1 (TRAIN-002);
  `_find_trainer` gate re-enabled with IS_NPC guard (TRAIN-003).
- `mud/commands/combat.py` — `do_cast` mana deduction order fixed (CAST-008).
- `tests/integration/test_nanny_login_parity.py` — NANNY-015 test.
- `tests/integration/test_recall_train_commands.py` — TRAIN-002/003 tests + fixture trainer.
- `tests/integration/test_spell_casting.py` — CAST-008 tests + skill-load fixture.
- `tests/integration/test_character_advancement.py`, `tests/test_advancement.py` — trainer added to train tests (TRAIN-003).
- `docs/parity/NANNY_C_AUDIT.md` — NANNY-015 row + corrected stale "train=3 set in creation ✅" claim.
- `docs/parity/ACT_MOVE_C_AUDIT.md` — TRAIN-002 + TRAIN-003 rows; corrected "prime stat costs" claim.
- `docs/parity/MAGIC_C_AUDIT.md` — CAST-008 row.
- `docs/parity/DB_C_AUDIT.md` — DB-001 Known Gaps; downgraded false "100% COMPLETE" / load_rooms "Implemented".
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-032 (OPEN) + budget footer.
- `CHANGELOG.md` — Fixed entries for NANNY-015, TRAIN-002, CAST-008, TRAIN-003.
- `pyproject.toml` — 2.11.59 → 2.11.60.

## Test Status

- Per-area suites green throughout (one failing test per gap before its fix).
- Full suite after all fixes: **5099 passed, 4 skipped** (no regressions from
  the TRAIN-003 gate change beyond the train tests updated in-session).

## Theme worth recording

All four confirmed bugs were **false-✅ rows**: the audit docs or code comments
asserted the buggy behavior was ROM-correct (`train=3 set in creation ✅`,
`prime stat costs`, `resolved the target and immediately deducted mana`,
`load_rooms ✅ Implemented`, DB `100% COMPLETE`). The per-file audit pass had
marked all four areas done; **in-game play caught all four**. The per-file
methodology structurally misses bugs where the doc *describes* the divergence
as intended — hands-on play is a complementary discovery channel that finds a
class of bug the systematic pass cannot. (CAST-008 additionally shows the value
of reading ROM C *operation order*, not just the operations.)

## Next Steps / Outstanding

1. **DB-001 / INV-032 — highest impact, own session.** Fix `room_loader.py`
   flag parsing (discard token0, letter-decode token1, assert len==3), then
   regenerate all 52 `data/areas/*.json` (proven safe — only `flags` change),
   then triage the test fallout when ROOM_SAFE/NO_RECALL/DARK/LAW activate
   game-wide. Write `tests/integration/test_inv032_room_flags_survive_load.py`
   (boot data, assert room 3720 is dark at runtime).
2. **Exit/door flags** — likely the same loss; the converter only decodes the
   `locks` field via `_locks_to_exit_bits`. Verify during the DB-001 fix.
3. **`get_max_train` hardcoded to 22** in `advancement.py` — ROM
   `get_max_train` is race/class dependent (`src/handler.c`). Not yet filed;
   candidate `TRAIN-004` in `ACT_MOVE_C_AUDIT.md`.
4. **Pre-existing lint** in `tests/integration/test_spell_casting.py` (F401
   unused `Room`/`room_registry`) and `test_recall_train_commands.py` (F841
   unused `result`) — present on HEAD before this session, not introduced here.
