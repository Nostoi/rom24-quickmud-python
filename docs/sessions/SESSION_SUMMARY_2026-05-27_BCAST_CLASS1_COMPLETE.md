# Session Summary — 2026-05-27 — BCAST Class 1 burn-down COMPLETE (2.9.63)

## Scope

Picked up immediately after the 2.9.62 handoff with three ⚠️ Partial-blocked
BCAST rows remaining: `BCAST-009` (GROUP-001), `BCAST-017` (ORDER-001), and
`BCAST-038` (STEAL-001). Goal: close all three and declare Class 1 META
audit complete.

## Outcomes

### `STEAL-001` — ✅ FIXED — closes BCAST-038

- **Python**: `mud/commands/thief_skills.py:_steal_failure`
- **ROM C**: `src/act_obj.c:2222-2223` (TO_VICT + TO_NOTVICT)
- **Gap**: `_steal_failure` delivered failure-path acts via `.messages` list only — connected players saw nothing.
- **Fix**: New `_send_to_char_sync` helper fires `asyncio.create_task(send_to_char(...))` for connected players and falls back to `.messages` for tests. TO_VICT via helper; TO_NOTVICT via `room.people` loop excluding `{char, victim}`.
- **Tests**: 1/1 — `tests/integration/test_steal_broadcasts.py::test_steal_failure_emits_to_vict_and_to_notvict_via_protocol`.

### `GROUP-001` — ✅ FIXED — closes BCAST-009

- **Python**: `mud/commands/group_commands.py:do_group`
- **ROM C**: `src/act_comm.c:1842-1854` (add + remove TO_VICT + TO_NOTVICT)
- **Gap**: Same `.messages`-only pattern on both add and remove branches.
- **Fix**: Identical `_send_to_char_sync` pattern threaded through both branches; TO_NOTVICT loops exclude `{char, victim}`.
- **Tests**: 2/2 — `tests/integration/test_group_broadcasts.py` (add + remove).

### `ORDER-001` — ✅ FIXED — closes BCAST-017

- **Python**: `mud/commands/group_commands.py:do_order`
- **ROM C**: `src/act_comm.c:1752-1754` (`act(buf, ch, NULL, och, TO_VICT)`)
- **Gap**: Manual `f"{char.name} orders you to '…'"` bypassed ROM `act()` visibility gating; wiz-invis orderers leaked their names. Pre-existing side-bug: `send_to_char(order_message, victim)` had args reversed and was never awaited.
- **Fix**: New `_pers_gated(actor, viewer)` helper mirrors ROM `src/handler.c:pers` — returns `"someone"` when `can_see_character(viewer, actor)` fails, else actor's name. Both all-targets and single-target branches build `order_message` via `_pers_gated` and deliver through `_send_to_char_sync`. Audit's "wrong word-position guard" claim was incorrect (`command.split(None, 1)[0]` IS ROM's `arg2`); explicitly retracted in the close-out.
- **Tests**: 2/2 — `tests/integration/test_order_broadcasts.py` (wiz-invis renders as "someone"; visible orderer renders with name).

## Files Modified

- `mud/commands/thief_skills.py` — `_send_to_char_sync` helper + `_steal_failure` rewrite
- `mud/commands/group_commands.py` — `_send_to_char_sync` + `_pers_gated` helpers + `do_group` rewrite + `do_order` rewrite (including fixing the reversed-args/never-awaited `send_to_char` side-bug)
- `tests/integration/test_steal_broadcasts.py` — new, 1 test
- `tests/integration/test_group_broadcasts.py` — new, 2 tests
- `tests/integration/test_order_broadcasts.py` — new, 2 tests
- `docs/parity/audits/BROADCAST_COVERAGE.md` — BCAST-009/017/038 → ✅ FIXED; Blocked-rows entries for GROUP-001/ORDER-001/STEAL-001 → ✅ FIXED
- `CHANGELOG.md` — new `[2.9.63]` section: Fixed (3 entries) + Changed (Class 1 complete)
- `pyproject.toml` — 2.9.62 → 2.9.63

## Test Status

- `pytest tests/integration/test_steal_broadcasts.py` — 1/1
- `pytest tests/integration/test_group_broadcasts.py` — 2/2
- `pytest tests/integration/test_order_broadcasts.py` — 2/2
- Full integration suite: **2302 passed + 3 documented skips in 84s** (+5 tests since 2.9.62).
- Pre-existing flake `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs` unchanged.
- Full `pytest -q` still hangs past 15min on this machine (pre-existing, unrelated).

## Commits

| SHA | |
|-----|---|
| `29126a5` | `fix(parity): STEAL-001 — _steal_failure broadcasts reach live sockets` |
| `8d1cd99` | `fix(parity): GROUP-001 — do_group add/remove broadcasts reach live sockets` |
| `6c9e8d5` | `fix(parity): ORDER-001 — do_order TO_VICT routes through act() visibility gating` |
| (this) | `chore(parity): session handoff — BCAST Class 1 burn-down COMPLETE 2.9.63` |

## Next Steps

1. **Push approval required** — 4 commits to push to `origin/master` for 2.9.63.
2. **Class 1 META BROADCAST_COVERAGE is COMPLETE.** No ⚠️ Partial rows remain.
3. **INV-027 promotion** (ACT-INVIS-TRUST-GATE) is the natural next-up. The new `_pers_gated` helper in `group_commands.py` is a stepping-stone — the wider fix is a `_can_witness(actor, witness)` helper threaded through `_act_room`/`broadcast_room` (per CROSS_FILE_INVARIANTS_TRACKER.md). Could fold `_pers_gated` into a shared `mud/utils/act.py` symbol when the wider promotion lands.
4. **Move on to a new META class** — pick from Class 2 ARITHMETIC_BOUNDARY, Class 3 GATE_CONSISTENCY, Class 4 TRIGGER_CALL_SITE_MIGRATION, or Class 5 LIFECYCLE_STAGING.
5. **GitNexus reindex** is stale (~36 commits behind, FTS read-only throughout this session). Run `npx gitnexus analyze --skip-agents-md` before the next probe-heavy session.
6. Pre-existing flake at `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
7. Worktree hygiene — 5 locked worktrees in `.claude/worktrees/`.
