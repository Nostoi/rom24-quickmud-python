# Session Summary — 2026-04-27 — `interp.c` social cluster complete (INTERP-021, INTERP-022)

## Scope

Continuation of the same-day `interp.c` audit session
(`SESSION_SUMMARY_2026-04-27_INTERP_C_SOCIAL_GATES.md`, release 2.6.6).
Picked option 1 from the prior session's "Next Intended Task": close
the two remaining social-cluster gaps so `check_social` reaches full
ROM parity. Both are small, isolated to `socials.py` /
`mud/models/social.py`. After this session the **entire 6-gap social
cluster of `check_social`** is ✅ FIXED.

## Outcomes

### `INTERP-021` — ✅ FIXED (IMPORTANT)

- **Python**: new `find_social()` in `mud/models/social.py:38-58`;
  `mud/commands/socials.py:10`; `mud/commands/dispatcher.py:851`.
- **ROM C**: `src/interp.c:584-592` (`check_social` table loop with
  `str_prefix`).
- **Gap**: `perform_social` and the dispatcher fallback both used
  `social_registry.get(name.lower())` — exact-match only. ROM iterates
  the social table in load order and accepts any prefix, so `gigg`
  matches `giggle`, `sm` matches `smile`, etc.
- **Fix**: added `find_social(name)` helper that first tries an exact
  dict lookup (insertion-order preserved → load order) and falls back
  to scanning for the first key that `startswith(query)`. Routed both
  the dispatcher (line 851) and `perform_social` (line 10) through it.
  IMC's separate `social_registry.get` path (`mud/commands/imc.py:293`)
  intentionally stays exact-match — it's a different subsystem and
  not part of `check_social`.
- **Tests**: 3 cases in `tests/integration/test_socials.py::TestSocialPrefixLookup`
  (full-prefix match, load-order tie-break, unknown prefix still
  returns `"Huh?"`).
- **Commit**: `b9e4bf2`.

### `INTERP-022` — ✅ FIXED (MINOR)

- **Python**: `mud/commands/socials.py:77-80`.
- **ROM C**: `src/interp.c:637-640` (`get_char_room` NULL branch).
- **Gap**: when the social target wasn't in the room, Python emitted
  `expand_placeholders(social.not_found, char)`. ROM has no
  `not_found` field in its social table; it hard-codes
  `send_to_char ("They aren't here.\n\r", ch)`. Players therefore saw
  whatever placeholder happened to be loaded into the fabricated
  Python field, not ROM's canonical wording.
- **Fix**: replaced the `expand_placeholders(social.not_found, char)`
  call with the literal string `"They aren't here."`.
- **Tests**: `tests/integration/test_socials.py::TestSocialNotFoundMessage::test_not_found_emits_rom_literal`
  asserts the exact string. The pre-existing
  `test_social_nonexistent_target` continues to pass (its loose
  `"around"/"here"/"isn't"/"not"` matcher still hits "here").
- **Commit**: `b57ef3e`.

## Files Modified

- `mud/models/social.py` — added `find_social()` (load-order
  `str_prefix` lookup mirroring ROM `check_social`'s table scan).
- `mud/commands/socials.py` — `perform_social` uses `find_social` and
  emits literal `"They aren't here."` (no more `social.not_found`).
- `mud/commands/dispatcher.py` — fallback social detection at
  line 851 routed through `find_social` so the prefix match takes
  effect *before* the perform_social call.
- `tests/integration/test_socials.py` — added `TestSocialPrefixLookup`
  (3 cases) and `TestSocialNotFoundMessage` (1 case); 27 → 31.
- `docs/parity/INTERP_C_AUDIT.md` — flipped INTERP-021 and
  INTERP-022 from 🔄 OPEN → ✅ FIXED with closure refs.
- `CHANGELOG.md` — promoted `[Unreleased]` block to
  `[2.6.7] - 2026-04-27` with both `Fixed` entries.
- `pyproject.toml` — `2.6.6` → `2.6.7` (patch — parity gap closures).

## Recent Commits

- `b9e4bf2` — `fix(parity): interp.c:INTERP-021 — social lookup uses str_prefix`
- `b57ef3e` — `fix(parity): interp.c:INTERP-022 — literal "They aren't here." on missing target`
- (handoff commit follows: `chore(release): 2.6.7 — interp.c social cluster complete`)

## Test Status

- `pytest tests/integration/test_socials.py` → **31 / 31 passing**
  (was 27 before this session).
- `ruff check mud/commands/socials.py mud/commands/dispatcher.py mud/models/social.py tests/integration/test_socials.py`
  → only pre-existing dispatcher findings (`raw_head`/`raw_tail` unused
  vars, I001 import order) — none introduced by this session.
- Full suite: not re-run wall-to-wall (the documented full-suite hang
  in this shell still applies; previously-documented RNG-isolation
  flake on `tests/test_mobprog_commands.py` remains outstanding).

## Audit Progress

- `interp.c`: **6 / 24 gaps closed** (25%). The complete social
  cluster of `check_social` (INTERP-018, 019, 020, 021, 022, 023) is
  now ✅ FIXED. Tracker row stays ⚠️ Partial — 18 dispatcher / trust
  / command-mapping gaps remain open.
- ROM C files audited overall: **16 / 43** (no change — `interp.c`
  still ⚠️ Partial).

## Next Steps

The natural next focus is one of two non-social `interp.c` clusters:

1. **`INTERP-001` — trust-table drift sweep.** Security-relevant. The
   `INTERP_C_AUDIT.md` "INTERP-001 detail" table lists ~40 immortal
   commands granted at lower trust than ROM's `merc.h:147-167` tier
   table. Each row needs its own commit + test per rom-gap-closer
   discipline, so plan for a multi-session sweep. Highest leverage
   remaining work in `interp.c`.
2. **Pure-dispatcher gaps.** `INTERP-002` (snoop forwarding),
   `INTERP-003` (wiznet `WIZ_SECURE` log mirror), `INTERP-007`
   (silent empty input), `INTERP-008` (`.`/`,`/`/` aliases),
   `INTERP-017` (prefix-match table-order divergence — needs an
   empirical sweep test). Smaller scope, less critical than the
   trust drift.
3. **Command-mapping cleanup.** `INTERP-009..014` — `hit`, `take`,
   `junk`, `tap`, `go`, `wield`, `hold`, `:` should dispatch to ROM's
   canonical handlers (`do_kill`, `do_get`, `do_sacrifice`, `do_enter`,
   `do_wear`, `do_immtalk`) rather than separate Python stubs.
4. **Pre-existing RNG-isolation flake** (carried from
   `2026-04-27_MOB_PROG_C_AUDIT_COMPLETE`): add a session-scoped
   `rng_mm.seed_mm` autouse fixture to `tests/conftest.py` so
   `tests/test_mobprog_commands.py::test_combat_cleanup_commands_handle_inventory_damage_and_escape`
   stops flaking when the integration suite collects first.
