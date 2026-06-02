# Session Summary — 2026-06-02 — ACT_COMM-002 + HANDLER-003 + HANDLER-005 CLOSED

## Scope

Picked up from the prior session (2.12.61), which closed HANDLER-002 + ACT_COMM-001
and left two documented gaps OPEN: **ACT_COMM-002** (normal-follow double
"You now follow X." message) and **HANDLER-003** (`get_char_room`/`get_char_world`
match `short_descr`; ROM matches only `name`). Both were the SESSION_STATUS-
recommended next tasks. This session closed both — one gap, one failing-test-first
commit each — and then closed a third gap, **HANDLER-005**, surfaced by advisor
review inside the same `get_char_world` function as HANDLER-003. Cross-file
invariants remains the active pass; all three are local single-function
divergences. Everything pushed to `master` (2.12.62 → 2.12.64).

## Outcomes

### `ACT_COMM-002` — ✅ FIXED (2.12.62 / `9f73c6d3` + `be5f4047`)

- **Python**: `mud/commands/group_commands.py:do_follow`
- **ROM C**: `src/act_comm.c:1586-1605` (`do_follow` success path calls
  `add_follower` and `return;` void; `add_follower:1605`'s
  `act("You now follow $N.", …TO_CHAR)` is the sole emitter)
- **Gap**: `do_follow`'s success path returned `"You now follow {victim}."` *and*
  `add_follower` already appended the same line to `char.messages`. The command
  loop sends the return value AND drains `char.messages`, so a connected actor saw
  the line twice.
- **Fix**: success path returns `""` (matching ROM's void return), leaving
  `add_follower` the sole emitter.
- **Test churn**: two existing tests asserted the *return* value and were
  retargeted to `char.messages` — `test_group_combat.py:162` (found at fix time)
  and `test_player_npc_interaction.py` (lowercase `"you now follow"`, surfaced
  only by the full-suite run — a case-sensitive grep missed it; fixed in the
  follow-up commit `be5f4047`). `test_shops.py:1365` needed no change (buy-pet
  path calls `add_follower` directly and already asserts `pet.messages`).
- **Tests**: `tests/integration/test_act_comm002_follow_other_single_message.py`
  (1 test: `follow bob` → `result == ""` and exactly one "You now follow bob." in
  `char.messages`). Fails pre-fix (return value carried the line), passes post-fix.

### `HANDLER-003` — ✅ FIXED (2.12.63 / `defaf313`)

- **Python**: `mud/world/char_find.py:get_char_room` / `get_char_world`
- **ROM C**: `src/handler.c:2207` (`is_name(arg, rch->name)`) / `:2237`
  (`is_name(arg, wch->name)`) — gate solely on the keyword `name` list
- **Gap**: both helpers additionally substring-matched `short_descr` (and a
  defensive `keywords` field), so `look city` resolved "a city guard" (keyword
  name "guard") where ROM returns nothing.
- **Fix**: both helpers now gate each occupant on `is_name(name, occupant.name)`
  alone; the `short_descr`/`keywords` branches were dropped. The shared `is_name`
  helper was **not** touched (it has its own callers in `mob_cmds`, `build`,
  `info`, `account_service`).
- **Blast radius**: `gitnexus_impact` flagged CRITICAL (15 direct callers, 58
  total, 9 modules). The full-suite run confirmed **zero** caller fallout — the
  one failure it surfaced was the ACT_COMM-002 lowercase assertion, not the
  tightening. The original gap note's "likely load-bearing" warning was
  conservative; callers/tests target mobs by keyword, not description words.
- **Tests**: `tests/integration/test_handler003_get_char_matches_name_only.py`
  (2 tests: room + world, unique-token keyword matches / short_descr word does
  not). Fails pre-fix (descword matched short_descr), passes post-fix.

### `HANDLER-005` — ✅ FIXED (2.12.64 / `70e7aa61`)

- **Python**: `mud/world/char_find.py:get_char_world`
- **ROM C**: `src/handler.c:2236` (`if (wch->in_room == NULL || !can_see(...) ||
  !is_name(...)) continue;`)
- **Gap**: ROM skips any world-list char whose `in_room == NULL` before the
  `can_see`/`is_name` tests; Python's loop omitted that guard. **Live** since
  VISION-001 (2026-05-29) dropped the `target_room is None` bail in
  `can_see_character` — a roomless registry char (e.g. the `CON_GET_NEW_CLASS`
  wiznet subject, `src/nanny.c:547`, whose `in_room` is NULL) became visible and
  thus resolvable by a world lookup.
- **Fix**: added `if getattr(ch, "room", None) is None: continue` as the first
  loop gate, mirroring ROM.
- **Surfaced by**: advisor review while closing HANDLER-003 (same function).
- **Tests**: `tests/integration/test_handler005_get_char_world_skips_roomless.py`
  (1 test: a roomless registry char is not resolved world-wide). Empirically
  confirmed **live** — fails pre-fix (returns the roomless ghost), passes post-fix.

## Out-of-scope gaps filed durably

- **HANDLER-004** (`docs/parity/HANDLER_C_AUDIT.md`, ❌ OPEN) — Python's shared
  `is_name` is looser than ROM in two ways: (1) it uses a **substring** test
  (`name_lower in word`) rather than ROM's `str_prefix` whole-word prefix, so
  `is_name("uard", "guard")` returns `True` where ROM returns `FALSE`; (2) it does
  not enforce ROM's "**all** space-separated parts of `arg` must match" rule.
  Surfaced while closing HANDLER-003 (which routed both char-lookup helpers
  through `is_name`). Left scoped out because tightening `is_name` widens the
  blast radius to its other callers (`mob_cmds`, `build` ×3, `info`,
  `account_service`). **Recommended top task for the next session.**

## Files Modified

- `mud/commands/group_commands.py` — `do_follow` success path returns `""` (ACT_COMM-002).
- `mud/world/char_find.py` — `get_char_room`/`get_char_world` gate on `is_name(name, occupant.name)` only (HANDLER-003); `get_char_world` skips roomless chars (HANDLER-005).
- `tests/integration/test_act_comm002_follow_other_single_message.py` — new (ACT_COMM-002).
- `tests/integration/test_handler003_get_char_matches_name_only.py` — new (HANDLER-003).
- `tests/integration/test_handler005_get_char_world_skips_roomless.py` — new (HANDLER-005).
- `tests/integration/test_group_combat.py` — retargeted follow assertion to `char.messages` (ACT_COMM-002).
- `tests/integration/test_player_npc_interaction.py` — retargeted follow-mob assertion to `char.messages` (ACT_COMM-002).
- `docs/parity/ACT_COMM_C_AUDIT.md` — ACT_COMM-002 → ✅ FIXED; do_follow parity check flipped.
- `docs/parity/HANDLER_C_AUDIT.md` — HANDLER-003 → ✅ FIXED; HANDLER-004 → ❌ OPEN (new); HANDLER-005 → ✅ FIXED (new).
- `CHANGELOG.md` — three `Fixed` entries.
- `pyproject.toml` — 2.12.61 → 2.12.62 → 2.12.63 → 2.12.64.

## Test Status

- ACT_COMM-002 / HANDLER-003 / HANDLER-005 area + new tests: green.
- Full suite: **5323 passed, 4 skipped** (`pytest`, parallel, ~137s) — run twice
  this session (after HANDLER-003 and after HANDLER-005), zero failures both times
  bar the ACT_COMM-002 lowercase assertion caught and fixed mid-run.
- `ruff check` on all touched files: clean (the 4 pre-existing UP037 quoted-
  annotation errors in `char_find.py` predate this work — confirmed via
  `git stash` against HEAD — and were left untouched to keep the commits scoped).
- `gitnexus_impact` (CRITICAL flagged before the HANDLER-003 edit) and
  `gitnexus_detect_changes` (scope confined to the edited functions + docs) run
  per the rules. Index reindexed after the push (44,394 nodes / 83,229 edges).

## Next Steps

Cross-file invariants remains the active pass. Candidate next tasks:

1. **Close HANDLER-004** (recommended first) — rewrite
   `mud/world/char_find.py:is_name` to mirror ROM's `one_argument` tokenization +
   `str_prefix` all-parts whole-word match (`src/handler.c:932-969`), replacing
   the current substring test. Then audit the other callers (`mob_cmds`,
   `build` ×3, `info`, `account_service`) for fallout — they rely on the looser
   substring behavior, so tighten test-first.
2. **Probe a fresh cross-file candidate** — position transitions
   (`do_stand`/`do_sit`/`do_rest`/`do_sleep`/`do_wake` — deterministic, no RNG),
   group/follower chains, or mob trigger ordering. Method: read ROM C contract →
   read Python equivalent → one failing test → close as gap or file as next free
   INV-NNN.
