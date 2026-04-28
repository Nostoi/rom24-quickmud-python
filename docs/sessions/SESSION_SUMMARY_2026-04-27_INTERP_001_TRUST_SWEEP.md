# Session Summary — 2026-04-27 — `interp.c` INTERP-001 trust sweep

## Scope

Continuation of the same-day `interp.c` audit (release 2.6.7 closed the
social cluster). This session tackled INTERP-001 — the trust-table
drift on immortal commands, which is the only security-relevant gap
left in `interp.c`. Used a two-agent split: a Sonnet verification agent
re-checked every row in the `INTERP_C_AUDIT.md` "INTERP-001 detail"
table against `src/interp.c:63-381`, `src/interp.h:34-44`, and the
current `mud/commands/dispatcher.py` COMMANDS list. A Sonnet executor
agent then applied the verified fix list, gated by one parametrized
integration test.

Treated INTERP-001 as a single audit-table gap (one parametrized test,
one commit) since the Phase 3 gap row is one entry; the per-command
breakdown is sub-detail.

## Outcomes

### `INTERP-001` — ✅ FIXED (CRITICAL — security)

- **Python**: `mud/commands/dispatcher.py` (43 `min_trust` updates
  across the COMMANDS table).
- **ROM C**: `src/interp.c:63-381` (`cmd_table[]` trust column),
  `src/interp.h:34-44` (`ML, L1..L8` macros).
- **Gap**: 43 immortal commands had `min_trust` set lower than ROM's
  `cmd_table[]` `trust_level` column. Concretely, a `LEVEL_IMMORTAL`
  (52) character could invoke commands ROM gates at L1..ML (53..60),
  including `reboot`, `shutdown`, `purge`, `restore`, `force`,
  `advance`, `copyover`, `trust`, `violate`, `dump`, `slay`,
  `freeze`, `disconnect`, `pardon`, etc.
- **Fix**: per-tier symbolic constants (`MAX_LEVEL`, `MAX_LEVEL - 1`,
  …, `MAX_LEVEL - 7`) replacing the drifted values. `admin_only=True`
  preserved on the rows that had it (`ban`, `permban`, `deny`,
  `allow`, `log`, `wizlock`, `newlock`, `qmconfig`).
- **Tests**: new parametrized test
  `tests/integration/test_interp_trust.py::test_interp_001_command_trust_matches_rom`
  with 50 cases (47 drift fixes + 3 already-correct rows: `goto`,
  `poofin`, `poofout` at L8=52=`LEVEL_IMMORTAL`). All 50 green.
- **Commit**: `548098d`.

### Tier breakdown (rows fixed)

| ROM tier | Numeric | Commands |
|----------|---------|----------|
| ML | 60 | advance, copyover, dump, trust, violate, qmconfig |
| L1 | 59 | deny, permban, protect, reboo, reboot, shutdow, shutdown, log |
| L2 | 58 | allow, ban, set, wizlock |
| L3 | 57 | disconnect, pardon, sla, slay |
| L4 | 56 | flag, freeze, guild, load, newlock, pecho, purge, restore, sockets, vnum, zecho, gecho |
| L5 | 55 | nochannels, noemote, noshout, notell, peace, snoop, string, transfer, teleport, clone |
| L6 | 54 | at, echo, recho, return, switch |
| L7 | 53 | force |

## Files Modified

- `mud/commands/dispatcher.py` — 43 `min_trust` corrections.
- `tests/integration/test_interp_trust.py` — new parametrized test
  (50 cases) asserting each command's `min_trust` matches ROM.
- `docs/parity/INTERP_C_AUDIT.md` — INTERP-001 row flipped to ✅ FIXED.
- `CHANGELOG.md` — `[2.6.8] - 2026-04-27` entry with `Fixed`.
- `pyproject.toml` — `2.6.7` → `2.6.8` (patch — parity gap closure).

## Recent Commits

- `548098d` — `fix(parity): interp.c:INTERP-001 — raise immortal command trust to ROM tiers`
- (handoff commit follows: `chore(release): 2.6.8 — interp.c INTERP-001 trust sweep`)

## Test Status

- `pytest tests/integration/test_interp_trust.py` → **50 / 50 passing**.
- Pre-existing `ruff` findings on `dispatcher.py` (`raw_head`/`raw_tail`
  unused vars, I001 import order) confirmed not introduced by this
  session.
- Full suite: not re-run (the documented full-suite hang in this shell
  still applies; previously-documented RNG-isolation flake remains).

## Audit Progress

- `interp.c`: **7 / 24 gaps closed** (29%). Gap row INTERP-001 is the
  single largest remaining `interp.c` row by impact (security drift on
  43 commands). Tracker row stays ⚠️ Partial — 17 dispatcher /
  command-mapping gaps remain.
- ROM C files audited overall: **16 / 43**.

## Next Steps

The remaining `interp.c` work is no longer security-relevant — it's
correctness/cleanup. Reasonable continuations:

1. **Pure-dispatcher gaps** — INTERP-002 (snoop forwarding to
   `desc->snoop_by`), INTERP-003 (wiznet `WIZ_SECURE` log mirror),
   INTERP-007 (silent return on empty input — currently emits "What?"),
   INTERP-008 (`.`/`,`/`/` aliases in COMMAND_INDEX), INTERP-017
   (prefix-match table-order divergence — empirical sweep test).
2. **Command-mapping cleanup** — INTERP-009..014 — `hit`, `take`,
   `junk`, `tap`, `go`, `wield`, `hold`, `:` should dispatch to ROM's
   canonical handlers (`do_kill`, `do_get`, `do_sacrifice`, `do_enter`,
   `do_wear`, `do_immtalk`) rather than separate Python stubs.
3. **`do_commands`/`do_wizhelp`** — INTERP-024: verify column format
   (12-char left-justified, 6 per line) and `LEVEL_HERO` mortal/immortal
   split.
4. **Pre-existing RNG-isolation flake** — still open from prior
   sessions. Add a session-scoped `rng_mm.seed_mm` autouse fixture to
   `tests/conftest.py`.
