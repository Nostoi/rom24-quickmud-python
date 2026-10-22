# Session Summary — 2026-07-16 — FIGHT-101 closed (do_flee non-ROM wait-gate/lag removed)

## Scope

Autonomous loop iteration 5/10. Probe-then-close on **FIGHT-101** (filed last
iteration): Python `do_flee` carried a wait-gate ("You are still
recovering.") and a `PULSE_VIOLENCE` WAIT_STATE that ROM's `do_flee` does not
have.

## Outcomes

### `FIGHT-101` — ✅ FIXED

- **Probe finding**: the gate was double-counting. ROM enforces player wait
  at the descriptor input loop (`src/comm.c:619-623` — typed input stays
  buffered until wait expires), which Python already mirrors at
  `mud/net/connection.py:1039-1047`; ALL player input paths (telnet, SSH,
  websocket) route through that handler. ROM's direct dispatch
  (`do_function` — mobprogs, `damage()`'s FIGHT-100 auto-flee) bypasses wait
  entirely. ROM `do_flee` itself (`src/fight.c:2970-3030`) neither checks
  wait nor applies WAIT_STATE.
- **Fix**: removed both the gate and the `_apply_wait_state(ch,
  get_pulse_violence())` lag from `mud/commands/combat.py:do_flee`.
  Observable repairs: (1) the FIGHT-100 wimpy auto-flee now fires at wait
  1..5 (ROM's only gate is `wait < PULSE_VIOLENCE / 2` in damage()); (2)
  fleeing no longer costs 12 pulses of invented lag.
- **Tests**: `tests/integration/test_fight101_flee_no_wait_gate.py` (2,
  failing-first).
- **Commit**: `93fcba45` (v2.14.327).

### `FIGHT-102` — ⚠️ FILED OPEN

Six sibling combat commands (`do_kick`, `do_rescue`, `do_backstab`,
`do_bash`, `do_berserk`, `do_cast`) carry the same non-ROM in-function
wait-gate class. Unlike flee they DO apply ROM WAIT_STATEs on use, and their
gates are reachable only via direct dispatch — per-site ROM read required
before removal (e.g. `mob_hit`'s own `ch->wait > 0` guard at
`src/fight.c:305` covers the NPC off-skill dispatch). Row in
`FIGHT_C_AUDIT.md`.

## Files Modified

- `mud/commands/combat.py` — do_flee gate + lag removed (ROM citation added)
- `tests/integration/test_fight101_flee_no_wait_gate.py` — new (2)
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-101 ✅, FIGHT-102 filed
- `CHANGELOG.md`, `pyproject.toml` — 2.14.326 → 2.14.327

## Test Status

- Unit layer: **2798 passed, 1 skipped**; integration: **3436 passed,
  3 skipped** (+2). Flee-area suites (fight043/054/061/062, move009,
  still-recovering guard, state transitions): 53/53. Zero fallout — no test
  asserted the invented lag.
- Differential harness: 99/99.

## Next Steps

**FIGHT-102** is scoped but needs six per-site ROM reads — good candidate for
the next iteration. Alternatives: HANDLER-009 (test-only), deferred C-oracle
scenarios (DB-005 census, FIGHT-098 area-attack, FIGHT-100 wimpy-flee),
carry-overs (FIGHT-094, DESC-001, OLC spell-name, IS_BUILDER).
