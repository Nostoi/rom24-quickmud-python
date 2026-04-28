# Session Summary — 2026-04-27 — `interp.c` dispatcher hook gaps

## Scope

Continuation of the same-day `interp.c` audit (release 2.6.8 closed
INTERP-001 trust drift). This session worked through the
"pure-dispatcher" gap cluster identified in the prior session's next
steps: empty-input behavior, ROM punctuation aliases, snoop
forwarding, and the wiznet `WIZ_SECURE` log mirror. One gap = one
parametrized test = one commit, per `rom-gap-closer` discipline.

## Outcomes

### `INTERP-007` — ✅ FIXED

- **Python**: `mud/commands/dispatcher.py:768-772`
- **ROM C**: `src/interp.c:401-404`
- **Gap**: empty-input dispatch returned the literal `"What?"`; ROM
  strips leading whitespace and returns silently.
- **Fix**: replaced `return "What?"` with `return ""` plus a ROM
  citation comment.
- **Tests**: 4 (parametrized over `""`, `"   "`, `"\t"`, `"  \t  "`)
  in `tests/integration/test_interp_dispatcher.py::test_interp_007_empty_input_returns_silently`.
- **Commit**: `6146ea5`.

### `INTERP-008` — ✅ FIXED

- **Python**: `mud/commands/dispatcher.py:280, 283, 347`
- **ROM C**: `src/interp.c:184, 186, 272`
- **Gap**: punctuation aliases `.` → `do_gossip`, `,` → `do_emote`,
  `/` → `do_recall` were missing from `COMMAND_INDEX`.
- **Fix**: added the three aliases via `Command(..., aliases=(...,))`.
- **Tests**: 3 parametrized cases asserting `COMMAND_INDEX[punct].func`
  matches the ROM handler.
- **Commit**: `42dc0d1`.

### `INTERP-002` — ✅ FIXED

- **Python**: `mud/commands/dispatcher.py` `process_command` (after
  `trimmed = input_str.lstrip()`).
- **ROM C**: `src/interp.c:491-496`.
- **Gap**: dispatcher had no snoop hook; ROM forwards the input
  logline to `ch->desc->snoop_by` prefixed with `"% "`.
- **Fix**: lookup `desc.snoop_by.character` via `getattr` chain;
  append `f"% {trimmed.rstrip()}"` to that character's `messages`
  queue. No-op when no snooper is attached.
- **Tests**: 2 cases — positive snoop forwarding and negative
  guard-when-no-snooper.
- **Commit**: `1ef8a10`.

### `INTERP-003` — ✅ VERIFIED (no production change)

- **Python**: `mud/admin_logging/admin.py:107-114`
  (`log_admin_command`).
- **ROM C**: `src/interp.c:468-489`.
- **Gap (audit row was stale)**: `log_admin_command` already invokes
  `wiznet(_duplicate_wiznet_chars(f"Log {actor}: {sanitized}"), char,
  None, WiznetFlag.WIZ_SECURE, None, _get_effective_trust(char))`
  with ROM-style `$`/`{` doubling. Audit description "Python only
  writes the admin log file" was incorrect.
- **Fix**: none — verification only. Audit row flipped to ✅ VERIFIED
  with citation.
- **Tests**: 1 case (`test_interp_003_logged_command_mirrors_to_wiznet_secure`)
  monkeypatches `wiznet` and confirms the call with `WIZ_SECURE`
  flag and `"Log <name>: ..."` message format.
- **Commit**: `b17ad93`.

## Files Modified

- `mud/commands/dispatcher.py` — empty-input return, snoop hook,
  punctuation aliases on gossip/emote/recall.
- `tests/integration/test_interp_dispatcher.py` — new file, 10
  test cases across 5 functions.
- `docs/parity/INTERP_C_AUDIT.md` — flipped rows: INTERP-007,
  INTERP-008, INTERP-002, INTERP-003.
- `CHANGELOG.md` — `[2.6.9]` entry with four `Fixed`/verified lines.
- `pyproject.toml` — `2.6.8` → `2.6.9` (patch — parity gap closures).

## Recent Commits

- `6146ea5` — `fix(parity): interp.c:INTERP-007 — empty input returns silently`
- `42dc0d1` — `fix(parity): interp.c:INTERP-008 — add ., ,, / punctuation aliases`
- `1ef8a10` — `fix(parity): interp.c:INTERP-002 — forward snoop logline to snooper`
- `b17ad93` — `test(parity): interp.c:INTERP-003 — verify wiznet WIZ_SECURE log mirror`
- (handoff commit follows: `chore(release): 2.6.9 — interp.c dispatcher hook gaps`)

## Test Status

- `pytest tests/integration/test_interp_dispatcher.py tests/integration/test_interp_trust.py tests/test_alias_parity.py` →
  **73 / 73 passing**.
- Full suite: not re-run (the documented full-suite hang in this
  shell still applies; the long-standing RNG-isolation flake remains).
- Pre-existing `ruff` findings on `dispatcher.py` (`raw_head`/`raw_tail`
  unused vars, I001 import order) confirmed not introduced by this
  session.

## Audit Progress

- `interp.c`: **11 / 24 gaps closed** (46%). Tracker row stays
  ⚠️ Partial — 13 gaps remain.
- ROM C files audited overall: **16 / 43**.

## Next Steps

The remaining `interp.c` work is correctness-only:

1. **INTERP-017** — prefix-match table-order divergence. Needs an
   empirical sweep test verifying the `resolve_command` prefix
   tie-break matches ROM `cmd_table[]` order.
2. **INTERP-009..014** — command-mapping cleanup: route `hit`,
   `take`, `junk`, `tap`, `go`, `wield`, `hold`, `:` to ROM's
   canonical handlers (`do_kill`, `do_get`, `do_sacrifice`,
   `do_enter`, `do_wear`, `do_immtalk`) rather than separate Python
   stubs.
3. **INTERP-024** — verify `do_commands`/`do_wizhelp` column format
   (12-char left-justified, 6 per line) and `LEVEL_HERO`
   mortal/immortal split.
4. **Pre-existing RNG-isolation flake** — still open from prior
   sessions. Add a session-scoped `rng_mm.seed_mm` autouse fixture to
   `tests/conftest.py`.
