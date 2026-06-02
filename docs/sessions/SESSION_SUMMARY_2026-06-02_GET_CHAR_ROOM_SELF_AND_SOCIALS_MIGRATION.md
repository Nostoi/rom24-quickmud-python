# Session Summary — 2026-06-02 — HANDLER-001 + INTERP-026 (get_char_room self-by-name; socials migration)

## Scope

Picked up from `SESSION_STATUS.md` (post-INTERP-025, 2.12.57). The prior session
left two filed-open gaps as the recommended next track: **HANDLER-001** (the
shared `get_char_room` skips self by name; CRITICAL 14-caller blast radius) and
**INTERP-026** (socials' hand-rolled victim search lacks `can_see` gating +
N.name). Chose Track 1 (close both together) per the status doc. Verified each
divergence against ROM C before editing; bounded HANDLER-001 with a full
14-caller ROM-C ⇄ Python sweep.

## Outcomes

### `HANDLER-001` — ✅ FIXED (2.12.58)

- **Python**: `mud/world/char_find.py:get_char_room`, `mud/commands/thief_skills.py:do_steal`
- **ROM C**: `src/handler.c:2194-2214` (`get_char_room`), `is_name`, `can_see`
- **Gap**: ROM `get_char_room` has **no self-skip** — only `can_see` + `is_name`
  gate the `in_room->people` loop — so your own name resolves to self (and
  `can_see(ch,ch)` short-circuits TRUE, so it works dark/blind). Python added
  `if occupant is char: continue`, so `<cmd> <ownname>` never resolved to self.
- **Fix**: removed the self-skip. `can_see_character(ch,ch)` already returns
  `True` (`vision.py:158`). **14-caller sweep verified** (no compensating guards
  needed): `do_consider` blocks via `is_safe`; `do_give`/`_give_money` have no
  self-guard in ROM either; `do_group`/`do_order`/`do_murder` already guard
  `victim==ch`; `do_recite`/`do_zap`/`do_pour`/`do_wake`/`look` legitimately
  allow self; `get_char_world` already returned self via its registry loop. **One
  caller adjusted:** removed `do_steal`'s substring pre-check
  (`arg2_lower in own_name`) that papered over the missing self-return and
  wrongly blocked stealing from others whose name is a substring of the thief's;
  the ROM `victim==ch` guard (`act_obj.c:2185-2189`) subsumes it.
- **Tests**: `tests/integration/test_handler001_get_char_room_self.py` (4:
  self-by-name, self-while-blind, `look <ownname>`, steal-substring regression).
  Updated 4 integration tests that targeted a mob via the token "test" — which
  now resolves to the fixture player "TestPlayer" (ROM `is_name` prefix-matches
  "test" → "TestPlayer") — to the unambiguous "mob" keyword
  (`test_player_npc_interaction.py`, `test_new_player_workflow.py`).

### `INTERP-026` — ✅ FIXED (2.12.59)

- **Python**: `mud/commands/socials.py:perform_social`
- **ROM C**: `src/interp.c:630-645` (`do_social`), `src/handler.c:2194-2214`
- **Gap**: social victim search bypassed `get_char_room`, so it lacked `can_see`
  gating (`smile <invisible>` leaked presence as "You smile at someone." instead
  of "They aren't here." — INV-027 family) and N.name parsing (`2.guard` matched
  nobody).
- **Fix**: migrated the victim search to the shared `get_char_room` (now
  self-correct after HANDLER-001), closing self + no-self-skip + can_see + N.name
  in one move; deleted the hand-rolled `startswith` loop.
- **Tests**: `tests/integration/test_interp026_social_can_see_and_nname.py` (2:
  `wibble <invisible>` → "They aren't here."; `wibble 2.guard` → 2nd guard).

## Files Modified

- `mud/world/char_find.py` — removed `get_char_room` self-skip.
- `mud/commands/thief_skills.py` — removed `do_steal` substring self pre-check.
- `mud/commands/socials.py` — `perform_social` victim search → `get_char_room`.
- `tests/integration/test_handler001_get_char_room_self.py` — new (4).
- `tests/integration/test_interp026_social_can_see_and_nname.py` — new (2).
- `tests/integration/test_player_npc_interaction.py`,
  `test_new_player_workflow.py` — "test" target → "mob" (collision fix).
- `docs/parity/HANDLER_C_AUDIT.md` — HANDLER-001 → ✅ FIXED; filed HANDLER-002.
- `docs/parity/INTERP_C_AUDIT.md` — INTERP-026 → ✅ FIXED.
- `docs/parity/ACT_COMM_C_AUDIT.md` — corrected stale do_follow ✅; filed ACT_COMM-001.
- `CHANGELOG.md` — Fixed entries for HANDLER-001 + INTERP-026.
- `pyproject.toml` — 2.12.57 → 2.12.59. `README.md` — version badge → 2.12.59.

## Test Status

- Targeted suites green (socials, interp025/026, npc_interaction, new_player,
  steal/thief/follow/group/give/look/consider).
- **Full suite**: `pytest` — **5316 passed, 4 skipped** (~127s), observed twice
  this session (5314 after HANDLER-001, 5316 after INTERP-026; was 5310 at start).
- `ruff check` — clean on all touched source/test files (pre-existing whitespace
  debt in older test files left untouched — out of scope).
- `gitnexus_detect_changes` — low risk, 0 affected processes for both commits.
- GitNexus reindexed after each commit (index fresh at `fc94e15c`).

## Outstanding (filed durably this session)

- **HANDLER-002** (`docs/parity/HANDLER_C_AUDIT.md`) — `get_char_room` /
  `get_char_world` count an occupant **twice** when its name/short *and* keyword
  list both match `arg`, so `N.name` mis-selects (e.g. a guard whose keywords
  repeat its name makes `2.guard` return the first). ROM `is_name` is one boolean
  test per occupant. Affects every N.name lookup. ❌ OPEN. Fix: collapse to a
  single per-occupant predicate, increment once.
- **ACT_COMM-001** (`docs/parity/ACT_COMM_C_AUDIT.md`) — `follow self` emits a
  **double** "stop following" message: `stop_follower` appends
  "You stop following {master}." (with name) AND `do_follow`'s self-branch then
  returns a bare "You stop following." ROM returns silently after
  `stop_follower` (the act call is the sole emitter). Pre-existing (reachable via
  `follow self` today), surfaced during the HANDLER-001 sweep. ❌ OPEN. Fix: drop
  the `return "You stop following."` in `do_follow`'s self-branch (return `""`).

## Next Steps

Cross-file invariants remains the active pass. Options:
1. **Close HANDLER-002** — single-helper fix in `char_find.py` (count once per
   occupant). Test-first: two mobs sharing name+keyword; `2.<name>` → second.
2. **Close ACT_COMM-001** — one-line `do_follow` self-branch fix + test.
3. **Probe a fresh cross-file candidate** — position transitions
   (`do_stand`/`do_sit`/`do_rest`/`do_sleep`/`do_wake`), group/follower chains,
   or mob trigger ordering.

**Push note:** 2.12.49–59 are committed locally but **NOT yet pushed**; 2.12.48
is the last on `master`.
