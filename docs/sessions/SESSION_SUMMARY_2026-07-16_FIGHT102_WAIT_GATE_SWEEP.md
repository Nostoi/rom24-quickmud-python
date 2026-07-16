# Session Summary — 2026-07-16 — FIGHT-102 closed (six non-ROM wait-gates removed)

## Scope

Autonomous loop iteration 6/10. Closed **FIGHT-102** (filed last iteration):
the six sibling in-function wait-gates in `mud/commands/combat.py`
(`do_kick`, `do_rescue`, `do_backstab`, `do_bash`, `do_berserk`, `do_cast`),
completing the class opened by FIGHT-101 (do_flee).

## Outcomes

### `FIGHT-102` — ✅ FIXED

- **Per-site ROM verification**: the only `->wait` READS in `src/fight.c`
  are multi_hit:193 (decrement), mob_hit:305 (dispatch guard),
  damage:986/996/1009 (epilogue), disarm-pickup:2263 — and NONE exist in
  `src/magic.c` or `src/interp.c`. Player wait is enforced solely by the
  descriptor input loop (`src/comm.c:619-623`), already mirrored by
  `mud/net/connection.py` and locked by
  `tests/test_networking_telnet.py::test_wait_state_buffers_command_until_recovered_per_rom`.
- **Fix**: all six `if wait > 0: return "You are still recovering."` entry
  gates removed. WAIT_STATE-on-use per command unchanged (that IS ROM);
  `mob_hit`'s own wait guard still covers the NPC off-skill dispatch path.
- **Locks**: `tests/integration/test_fight102_no_command_wait_gates.py` —
  a Layer-A grep-guard (the recovery line may not reappear in combat.py)
  plus a behavioral test (kick at wait 5 executes and re-applies beats).
- **Test triage**: four stale tests asserting the non-ROM blocking were
  rewritten to the ROM contract:
  `test_skills_integration.py::test_wait_state_blocks_skill_reuse` (→
  `..._set_by_skill_but_not_rechecked_in_command`),
  `test_still_recovering_single_delivery.py::test_kick_while_recovering_...`
  (→ asserts the line never appears),
  `test_skill_combat_rom_parity.py` bash/kick "returns recovering" (→
  "executes when waiting" + WAIT_STATE re-applied).
- **Commit**: `63a27c23` (v2.14.328).

## Files Modified

- `mud/commands/combat.py` — six gates removed
- `tests/integration/test_fight102_no_command_wait_gates.py` — new (2)
- 3 test files — stale non-ROM assertions rewritten
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-102 ✅
- `CHANGELOG.md`, `pyproject.toml` — 2.14.327 → 2.14.328

## Test Status

- Unit layer: **2798 passed, 1 skipped**; integration: **3438 passed,
  3 skipped** (+2 net).
- Differential harness: 99/99.

## Next Steps

Remaining backlog: HANDLER-009 (test-only), deferred C-oracle scenarios
(DB-005 census, FIGHT-098 area-attack, FIGHT-100 wimpy-flee — all unblocked,
`src/diffshim` works), carry-overs (FIGHT-094 check_killer placement,
DESC-001, OLC spell-name lookup, IS_BUILDER, stray db files). Recommended
next: author the three deferred C-oracle scenarios in one session (same
capture workflow), locking DB-005/FIGHT-098/FIGHT-100 against the live C
engine.
