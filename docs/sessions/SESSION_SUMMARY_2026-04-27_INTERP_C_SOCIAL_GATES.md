# Session Summary — 2026-04-27 — `interp.c` audit started; social cluster CRITICAL gaps closed

## Scope

Picked the next P1 file from `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
that was still ⚠️ Partial: `interp.c` (P0, 80% audited). It was selected
because it sits *under* every already-audited `act_*.c` file — a parity
gap in the dispatcher would silently invalidate the "✅ COMPLETE" status
of every command file already closed.

Ran `/rom-parity-audit interp.c` end-to-end (Phases 1–3) producing a new
`docs/parity/INTERP_C_AUDIT.md` with **24 stable gap IDs** (`INTERP-001`
… `INTERP-024`). Then closed the entire **social-cluster** CRITICAL/
IMPORTANT subset (4 gaps) via `/rom-gap-closer`, one TDD cycle per gap.

## Outcomes

### `INTERP-018` — ✅ FIXED (CRITICAL)

- **Python**: `mud/commands/socials.py:perform_social`
- **ROM C**: `src/interp.c:603-616` (check_social position gate)
- **Gap**: `perform_social` ignored `Position` entirely; a corpse, mortally
  wounded, incapacitated, or stunned character could emit any social.
- **Fix**: added DEAD/MORTAL/INCAP/STUNNED early-returns with ROM's exact
  wording (`"Lie still; you are DEAD."` etc.).
- **Tests**: 4 cases in `tests/integration/test_socials.py::TestSocialPositionGates`.
- **Commit**: `3577938`.

### `INTERP-019` — ✅ FIXED (IMPORTANT)

- **Python**: `mud/commands/socials.py:perform_social`
- **ROM C**: `src/interp.c:618-626` (POS_SLEEPING branch with snore exception)
- **Gap**: sleeping characters could social freely; ROM blocks all socials
  except `snore` ("In your dreams, or what?").
- **Fix**: SLEEPING gate with the canonical Furey `snore` bypass.
- **Tests**: 2 cases (block + snore guard).
- **Commit**: `7b15bea`.

### `INTERP-020` — ✅ FIXED (IMPORTANT)

- **Python**: `mud/commands/socials.py:perform_social`
- **ROM C**: `src/interp.c:597-601` (`COMM_NOEMOTE` short-circuit)
- **Gap**: punished players (`COMM_NOEMOTE` flag) could still emit socials.
- **Fix**: NOEMOTE early-return with `IS_NPC` bypass; uses `CommFlag.NOEMOTE`
  IntFlag — no hex literals.
- **Tests**: 2 cases (player blocked + NPC bypass).
- **Commit**: `071cdaa`.

### `INTERP-023` — ✅ FIXED (CRITICAL)

- **Python**: `mud/commands/socials.py:perform_social`
- **ROM C**: `src/interp.c:652-685` (NPC reaction switch on `number_bits(4)`)
- **Gap**: when a player socialed at an awake, non-charmed, non-switched
  NPC, ROM rolled `number_bits(4)` and dispatched a slap (9..12) or echoed
  the social back (0..8). Python performed no auto-react at all.
- **Fix**: branch on `mud.utils.rng_mm.number_bits(4)` per AGENTS.md
  (no `random.*`); 0..8 echo (actor/victim swap), 9..12 slap with ROM's
  exact strings, 13..15 silent (ROM has no `case` for those values).
  Gates: `!IS_NPC(actor)`, `IS_NPC(victim)`, `!CHARM`, `position > SLEEPING`,
  `desc is None`.
- **Tests**: 6 cases — slap branch, echo branch, silent branch, charm gate,
  NPC-actor gate, sleeping-victim gate. Each branch is pinned by
  monkey-patching `rng_mm.number_bits` to a fixed value (the dispatch
  logic is what's under test; the RNG itself is unit-tested elsewhere).
- **Commit**: `9b51e40`.

## Files Modified

- `mud/commands/socials.py` — grew from 28 lines to 95; now mirrors
  `check_social` (excluding INTERP-021/022 prefix-lookup and not-found
  message gaps, both still 🔄 OPEN).
- `tests/integration/test_socials.py` — added 14 new tests (13 → 27 total);
  two new test classes `TestSocialPositionGates`, `TestSocialNpcAutoReact`.
- `docs/parity/INTERP_C_AUDIT.md` — **new file** (created by the audit
  pass); rows INTERP-018/019/020/023 flipped 🔄 OPEN → ✅ FIXED with
  closure refs.
- `CHANGELOG.md` — `[Unreleased]` block with 3 `Fixed` and 1 `Added` entry.
- `pyproject.toml` — version bumped 2.6.5 → 2.6.6.

## Recent Commits

- `3577938` — `fix(parity): interp.c:INTERP-018 — socials refuse DEAD/INCAP/MORTAL/STUNNED`
- `7b15bea` — `fix(parity): interp.c:INTERP-019 — sleeping blocks socials except snore`
- `071cdaa` — `fix(parity): interp.c:INTERP-020 — COMM_NOEMOTE silences player socials`
- `9b51e40` — `feat(parity): interp.c:INTERP-023 — NPC slap/echo auto-react to player socials`

## Test Status

- `pytest tests/integration/test_socials.py -v` ⇒ **27/27 passing** (was
  13 before this session).
- `ruff check mud/commands/socials.py tests/integration/test_socials.py`
  ⇒ clean across all four commits.
- Full suite: not re-run wall-to-wall (the prior session's note about
  `pytest` hanging in this shell still applies); the previously-documented
  RNG-isolation flake on `tests/test_mobprog_commands.py` remains
  outstanding (see `SESSION_STATUS.md` from the previous session — not
  in scope for this work).

## Audit Progress

- `interp.c` ROM-C audit progress: **4 / 24 gaps closed** (16.7%). Tracker
  status remains ⚠️ Partial — file is **not** at 100% yet, so the
  `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` row stays put. The full
  `INTERP_C_AUDIT.md` (24 gaps documented) is the new source of truth.
- Social cluster within `interp.c`: 4 / 6 gaps closed. Remaining:
  - **INTERP-021** (IMPORTANT) — social lookup uses exact-match dict; ROM
    uses `str_prefix` so `gigg` matches `giggle`.
  - **INTERP-022** (MINOR) — Python emits `social.not_found` placeholder;
    ROM hard-codes `"They aren't here."`.

## Notes for Next Session

- **Highest leverage remaining `interp.c` work**: **INTERP-001** — the
  trust-table drift, ~40 immortal commands granted at lower trust than
  ROM. Security-relevant. Mechanical edits, but per the rom-gap-closer
  rule each row needs its own commit + test, so this is multi-session.
  See the "INTERP-001 detail" table in `INTERP_C_AUDIT.md` for the full
  per-command drift mapping.
- **Pure-dispatcher gaps**: INTERP-002 (snoop forwarding), INTERP-003
  (wiznet `WIZ_SECURE` log mirror), INTERP-007 (silent empty input),
  INTERP-008 (`.`/`,`/`/` aliases), INTERP-017 (prefix-match table-order
  divergence — needs an empirical sweep test).
- **Command-mapping cleanup**: INTERP-009..014 — `hit`, `take`, `junk`,
  `tap`, `go`, `wield`, `hold`, `:` should dispatch to ROM's canonical
  handlers (`do_kill`, `do_get`, `do_sacrifice`, `do_enter`, `do_wear`,
  `do_immtalk`) rather than separate Python stubs. Each closure should
  also delete the redundant stub if it adds nothing ROM-required.
- **Pre-existing RNG-isolation flake** (from prior session, still open):
  `tests/test_mobprog_commands.py::test_combat_cleanup_commands_handle_inventory_damage_and_escape`
  passes alone but fails after integration tests run because there's no
  session-scoped `rng_mm.seed_mm` fixture in `tests/conftest.py`. Not
  introduced by this session; see `SESSION_STATUS.md` from
  `2026-04-27_MOB_PROG_C_AUDIT_COMPLETE`.
