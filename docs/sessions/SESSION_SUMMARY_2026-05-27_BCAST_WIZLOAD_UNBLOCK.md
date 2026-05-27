# Session Summary — 2026-05-27 — BCAST WIZLOAD-001 unblock + 3 BCAST closures (2.9.61)

## Headline

Third session of 2026-05-27. Closed **WIZLOAD-001** (four layered pre-existing typos that had left `do_mload`, `do_oload`, and `do_clone` object branch wholly unreachable on real prototypes), then immediately layered the three previously-⚠️ BLOCKED BCAST rows on top: **BCAST-014** (`do_mload` TO_ROOM), **BCAST-015** (`do_oload` TO_ROOM), and **BCAST-002 (obj branch)** (`do_clone` object-branch TO_ROOM). Also reclassified **BCAST-019** (`do_reply`) to ✅ COVERED — another helper-transitivity false positive (delegates to `do_tell` which already broadcasts). One new pre-existing bug filed durably as **CLONE-001** (do_clone mob branch imports non-existent `LEVEL_AVATAR`/`LEVEL_DEMI`/`LEVEL_GOD` constants; blocks BCAST-002 mob branch).

Cumulative Class 1 BROADCAST_COVERAGE burn-down (since opening in 2.9.58): **24 of 29 ❌ rows now resolved or routed** (11 fixed, 8 COVERED collapses, 1 ⚠️ Partial (obj-branch fixed / mob-branch blocked by CLONE-001), 0 ⚠️ BLOCKED — all three unblocked this session, 4 deferred). 5 ❌ + 10 ⚠️ remain (out of 209 ✅ baseline).

## Commits (4 on master this session — 8 ahead of `origin/master` total)

| SHA | Type | Content |
|-----|------|---------|
| `7a6213f` | fix(parity) | WIZLOAD-001 — wiz-load/clone surface name+import typos (`mob_prototypes`→`mob_registry`, `obj_prototypes`→`obj_registry`, `spawn_obj`→`spawn_object`, and `do_clone` attribute-copy skip of read-only `name` property). 3 success-path regression tests. |
| `9b95140` | feat(parity) | BCAST-014 — `do_mload` emits TO_ROOM `$n has created $N!`. |
| `c330e04` | feat(parity) | BCAST-015 — `do_oload` emits TO_ROOM `$n has created $p!`. |
| `15fc350` | feat(parity) | BCAST-002 (obj branch) — `do_clone` object branch emits TO_ROOM `$n has created $p.`. Mob branch deferred — CLONE-001 filed. |
| (pending) | chore(parity) | Session handoff: 2.9.61 version, CHANGELOG, summary, STATUS, BCAST-019 COVERED flip. |

## Outcomes

### `WIZLOAD-001` — ✅ FIXED

- **Python**: `mud/commands/imm_load.py:68, 121, 126-127`; `mud/commands/imm_search.py:417, 424, 432`
- **Bugs (four layered)**:
  1. `do_mload` registry lookup read non-existent `registry.mob_prototypes` (canonical: `mob_registry`) — always early-returned "No mob has that vnum".
  2. `do_oload` registry lookup read non-existent `registry.obj_prototypes` (canonical: `obj_registry`) — always early-returned.
  3. `do_oload` imported non-existent `spawn_obj` from `mud.spawning.obj_spawner` (canonical: `spawn_object`, no `level` arg) — would ImportError even with the registry fix.
  4. `do_clone` object branch had the same `spawn_obj` ImportError; surfaced a fourth bug once that was lifted: the attribute-copy loop called `setattr(clone, "name", ...)` but `Object.name` is a read-only property derived from prototype.
- **Fix**: switch all four call sites to canonical names; set `obj.level = level` post-spawn to preserve the ROM `create_object(pIndex, level)` semantics; drop `"name"` from the do_clone attr-copy list and wrap the loop in try/except AttributeError for similar future property-vs-attr collisions.
- **Tests**: 3 new success-path tests in `tests/integration/test_act_wiz_command_parity.py` (`test_mload_success_places_mob_in_room`, `test_oload_success_places_obj_in_inventory_or_room`, `test_clone_object_success_places_clone`). 111/111 act_wiz tests still green.
- **Unblocks**: BCAST-002, BCAST-014, BCAST-015 (all closed in the same session below).

### `BCAST-014` — ✅ FIXED

- **Python**: `mud/commands/imm_load.py:do_mload`
- **ROM C**: `src/act_wiz.c:2512` — `act("$n has created $N!", ch, NULL, victim, TO_ROOM)`
- **Fix**: `broadcast_room(room, f"{actor_name} has created {victim_short}!", exclude=char)` after spawn/placement, before the wiznet log.
- **Subtlety**: spawned MobInstances populate `name` from `proto.short_descr` and don't separately carry `short_descr`. Resolver tries `victim.short_descr` → `prototype.short_descr` → `victim.name` to recover ROM's `$N` substitution string.
- **Test**: `tests/integration/test_mload_oload_broadcasts.py::test_mload_emits_to_room_broadcast_with_victim_short_descr`.

### `BCAST-015` — ✅ FIXED

- **Python**: `mud/commands/imm_load.py:do_oload`
- **ROM C**: `src/act_wiz.c:2566` — `act("$n has created $p!", ch, obj, NULL, TO_ROOM)`
- **Fix**: TO_ROOM emit after the inventory-or-room placement, before the wiznet log. Same `short_descr` → `prototype.short_descr` → `name` fallback as BCAST-014.
- **Test**: `tests/integration/test_mload_oload_broadcasts.py::test_oload_emits_to_room_broadcast_with_obj_short_descr`.

### `BCAST-002` (obj branch) — ✅ FIXED; mob branch ⚠️ blocked

- **Python**: `mud/commands/imm_search.py:do_clone` object branch (lines 416-462)
- **ROM C**: `src/act_wiz.c:2406` — `act("$n has created $p.", ch, clone, NULL, TO_ROOM)`
- **Fix**: TO_ROOM emit after the inventory/room placement, before the wiznet log.
- **Test**: `tests/integration/test_clone_broadcasts.py::test_clone_object_emits_to_room_broadcast`.
- **Mob branch deferred — CLONE-001**: writing the mob-branch test ImportErrored. Root cause: `mud/commands/imm_search.py:470` imports `LEVEL_AVATAR`, `LEVEL_DEMI`, `LEVEL_GOD` from `mud.models.constants`, but only `LEVEL_IMMORTAL` (52) and `LEVEL_ANGEL` (53) exist. The four-tier trust gate (ROM `:2424-2429`) ImportErrors before any spawn or broadcast. Filed durably as **CLONE-001** in `BROADCAST_COVERAGE.md` "Blocked rows" with full fix shape — note ROM `merc.h` actually has `IMMORTAL=55` and `AVATAR=52`, so Python's existing `LEVEL_IMMORTAL=52` is misnamed and a naive add risks renaming churn; the safe fix is to add the missing constants and gate `do_clone` against a locally-defined ROM-aligned ladder.

### `BCAST-019` — ✅ COVERED (false positive)

- **Python**: `mud/commands/communication.py:do_reply` (lines 244-252)
- **ROM C**: `src/act_comm.c:946-947` — `act_new("{k$n tells you '{K$t{k'{x", ch, argument, victim, TO_VICT, POS_DEAD)`
- **Why false positive**: `do_reply` is a five-line dispatcher that delegates to `do_tell(char, f"{target.name} {args}")`. The TO_VICT `tells you` broadcast is emitted by `do_tell`'s per-victim path (`communication.py:70-83`). Audit's static scan saw the dispatcher but not the helper. Same shape as the BCAST-001/004/005/007/008/020/026/029 collapses.
- **No code change.**

## Files Modified

- `mud/commands/imm_load.py` — fixed registry/spawner identifiers; added BCAST-014/015 TO_ROOM emits.
- `mud/commands/imm_search.py` — fixed `spawn_obj`→`spawn_object`; skipped read-only `name` in clone attr-copy; added BCAST-002 obj-branch TO_ROOM emit.
- `tests/integration/test_act_wiz_command_parity.py` — 3 WIZLOAD-001 success-path tests (and ruff-fix import sorting in adjacent blocks).
- `tests/integration/test_mload_oload_broadcasts.py` (new) — 2 BCAST-014/015 tests.
- `tests/integration/test_clone_broadcasts.py` (new) — 1 BCAST-002 obj-branch test + deferred mob-branch note.
- `docs/parity/audits/BROADCAST_COVERAGE.md` — row flips: BCAST-002 (⚠️ BLOCKED→⚠️ Partial), BCAST-014/015 (❌→✅ FIXED), BCAST-019 (❌→✅ COVERED). WIZLOAD-001 status → ✅ FIXED, CLONE-001 added to Blocked rows.
- `CHANGELOG.md` — new 2.9.61 section (Added BCAST-014/015/002-obj, Fixed WIZLOAD-001, Changed BCAST-019 COVERED).
- `pyproject.toml` — 2.9.60 → 2.9.61.
- `docs/sessions/SESSION_SUMMARY_2026-05-27_BCAST_WIZLOAD_UNBLOCK.md` (new).
- `docs/sessions/SESSION_STATUS.md` — refreshed.

## Test Status

- `pytest tests/integration/test_act_wiz_command_parity.py` — 111/111 passing.
- `pytest tests/integration/test_mload_oload_broadcasts.py` — 2/2 passing.
- `pytest tests/integration/test_clone_broadcasts.py` — 1/1 passing (mob-branch test deferred until CLONE-001 lands).
- **Full integration suite**: `pytest tests/integration/ -q --timeout=60` — **2289 passed + 3 skipped in 87s** (up from 2270/2270 at session start; +19 new tests across this session).

## Next Steps

1. **Push approval required** — 8 commits ahead of `origin/master` (4 from 2.9.60 + 4 from 2.9.61). The push is a single shot covering both versions.
2. **CLONE-001 closure** — add missing `LEVEL_AVATAR`/`LEVEL_DEMI`/`LEVEL_GOD` constants (do NOT rename existing `LEVEL_IMMORTAL=52` — wide blast radius), gate `do_clone` mob branch against a locally-defined ROM-aligned ladder. ~30 lines + the deferred BCAST-002 mob-branch test. Unblocks BCAST-002 mob branch closure (one more TO_ROOM emit on top).
3. **Remaining viable BCAST real gaps** (next-session priorities):
   - **BCAST-017 `do_order`** (1 TO_VICT, `act_comm.c:1650`) — `mud/commands/group_commands.py:473`; no broadcast helpers in file (confirmed).
   - **BCAST-010 `do_gtell`** (1 TO_VICT, `act_comm.c:1948`) — `mud/commands/group_commands.py:303`; no broadcast helpers in file.
   - **BCAST-028 `do_value`** (4 TO_VICT, `act_obj.c:2904`) — shopkeeper haggle responses.
   - **BCAST-009 `do_group`** (5 acts) — 2.9.20 reportedly shipped a fix; re-verify whether the regex missed it (group_commands.py has zero broadcast helper calls, so likely a real gap).
4. **Expensive remaining BCAST** (large act counts, defer): BCAST-006 `enter` (5), BCAST-021-024 `rest`/`sit`/`sleep`/`stand` (4-12 each).
5. **⚠️ Partial closures** (BCAST-030 through 039) — bulk pass when ❌ list is exhausted.
6. **INV-027 promotion** (ACT-INVIS-TRUST-GATE): introduce `_can_witness(actor, witness)`, thread through `_act_room` / `broadcast_room`, regression test.
7. **Pre-existing flake** at `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs` — still unresolved.
8. **GitNexus reindex** still stale (last `069f17f`); now ~28 commits behind. FTS index still read-only per the per-tool warnings this session. Run `npx gitnexus analyze --skip-agents-md` before next probe session.
9. **Worktree hygiene** — 5 locked worktrees still pending in `.claude/worktrees/`.
10. **Remaining META classes**: Class 2 ARITHMETIC_BOUNDARY, Class 3 GATE_CONSISTENCY, Class 4 TRIGGER_CALL_SITE_MIGRATION, Class 5 LIFECYCLE_STAGING.
