# Session Summary — 2026-05-28 — FIGHT-018 combat dam_message TRIG_ACT dispatch (2.9.90)

## Scope

The user asked whether a Ralph loop could autonomously work through "these
issues" with less intervention. We scoped the actual backlog first rather than
starting a loop blind. Finding: the per-file audit queue is fully drained — all
40 audit-bound ROM C files ✅ (3 N/A), and the ~80 scary `❌`/`⚠️`/`OPEN`
grep hits across the per-file audit docs are **all** either stale
function-comparison rows (e.g. ACT_COMM's status header says "EMOTE-002 OPEN"
but its resolution row is ✅ FIXED) or DEFERRED-by-design entries. Zero
genuinely-open gap-ID resolution rows. Conclusion: a Ralph loop is the wrong
tool — the queue it would drain is empty, and the remaining work (cross-file
invariant *discovery*) is judgment-heavy, which is Ralph's documented weak spot.

The one genuinely-uncovered, ROM-accurate gap surfaced during scoping was the
**INV-025 act()-dispatch follow-up** as it applies to combat: the sweep was
already wired into give/put/drop/get/wear/remove/sacrifice and the
position-transition broadcast, but **combat damage messages** still never fired
TRIG_ACT. Filed as **FIGHT-018** and closed via `/rom-gap-closer`
(one gap, two tests, one commit).

GitNexus MCP query path was read-only all session (`Cannot execute write
operations in a read-only database`), so impact analysis used the documented
`grep` + test-suite fallback. `_broadcast_damage_messages` is a leaf helper
called only from `apply_damage` (`engine.py:567`) and the dam-message PERS test
(LOW risk). The on-disk graph is also stale (`last indexed: 6b7f80d`); the CLI
`analyze` rebuild was **not** re-run this session because the read-only DB state
would fail the write — re-run `npx gitnexus analyze --skip-agents-md` once the
lock clears.

## Outcomes

### `FIGHT-018` — ✅ FIXED

- **Python**: `mud/combat/engine.py:_broadcast_damage_messages` (after the
  TO_NOTVICT room loop, ~line 245)
- **ROM C**: `src/fight.c:2215-2226` (`dam_message`)
- **Gap**: ROM `dam_message` emits the combat hit line TO_ROOM (self-inflicted,
  `ch == victim`) or TO_NOTVICT (normal) via `act()` with no
  `MOBtrigger = FALSE` wrap. Per `src/comm.c:2384`, every NPC recipient in the
  room then fires `mp_act_trigger(buf, to, ch, ..., TRIG_ACT)`, so mob ACT-progs
  respond to combat happening around them. Python's `_broadcast_damage_messages`
  PERS-renders the per-recipient combat text (the DAMMSG-001/002/003 fix) but
  never dispatched TRIG_ACT, so every combat-watching mobprog silently no-opped.
- **Fix**: after the room broadcast loop, render the room template canonically
  (real attacker/victim names — same pattern as `_broadcast_pos_change`) and call
  `mp_act_trigger_room(canonical, room, attacker, exclude=victim)`. `exclude=victim`
  reproduces TO_NOTVICT's actor+victim exclusion; the self-inflicted case
  (`attacker is victim`) collapses to TO_ROOM's single-actor exclusion. Six lines,
  guarded by the existing `if not messages.room: return` early-exit so a
  message-less path dispatches nothing.
- **Tests**: `tests/integration/test_fight_018_dam_message_act_trigger_dispatch.py`
  — 2 cases, first verified failing pre-fix:
  - `..._fires_act_trigger_on_listening_npc` — third-party NPC with a TRIG_ACT
    prog (phrase "mauls") fires on a combat hit.
  - `..._excludes_attacker_and_victim` — neither attacker nor victim receives the
    trigger (TO_NOTVICT semantics).
- **Commit**: `f2bd9723`.

## Files Modified

- `mud/combat/engine.py` — `_broadcast_damage_messages` now fans the room line into `mp_act_trigger_room` (FIGHT-018).
- `tests/integration/test_fight_018_dam_message_act_trigger_dispatch.py` — new file, 2 cases.
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-018 row added ✅ FIXED (2.9.90); status header updated.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-025 follow-up trail: combat `dam_message` added to the closed-callsite list; remaining open surface narrowed to non-combat `_push_message`/`broadcast_room`.
- `CHANGELOG.md` — 2.9.90 section (FIGHT-018).
- `pyproject.toml` — 2.9.89 → 2.9.90.

## Test Status

- `tests/integration/test_fight_018_dam_message_act_trigger_dispatch.py` — 2/2.
- Combat + mobprog + INV-025 regression slice — 53 passed.
- `ruff check` on changed files — clean (repo-wide baseline debt unchanged).
- Full suite: **run 1** — 1 failed, 4901 passed, 4 skipped (the failure was
  `test_group_combat.py::TestGroupExperienceSharing::test_group_xp_split_between_members`,
  an `AttributeError` at `reset_handler.py:178` in area-reset exit-flag logic);
  **run 2** — 4902 passed, 4 skipped, **0 failed**. The failure is a
  pre-existing, intermittent cross-file `room_registry` isolation leak surfaced by
  worker-grouping shift (the 2 new tests changed the xdist distribution), **not**
  caused by FIGHT-018: the failing test passes in isolation, and its failure path
  (`reset_area` iterating `room_registry`) is disjoint from the combat-message
  change. See Outstanding.

## Outstanding

- **Intermittent xdist isolation flake — `test_group_combat.py::TestGroupExperienceSharing::test_group_xp_split_between_members`.**
  Fails non-deterministically with `AttributeError` at
  `mud/spawning/reset_handler.py:178` (`exit_obj.exit_info = base_flags`) when
  `reset_area` iterates a `room_registry` polluted by another test file that left
  a Room/exit object without a settable `exit_info`. Passes alone and on re-run;
  surfaced this session only because the 2 new FIGHT-018 tests shifted worker
  grouping. Root cause is a sibling test leaking `room_registry` (per AGENTS.md
  "Parallel test execution & isolation"), not a production bug. Next agent: run
  the full suite a few times to pin which file leaks (the leaker, not
  `test_group_combat`, is the bug), then snapshot/clear/restore `room_registry`
  in that file's autouse fixture. Not a ROM parity gap.
- **INV-025 follow-up remaining**: the non-combat `_push_message` /
  `broadcast_room` narration surface still doesn't feed `mp_act_trigger_room`.
  Each is one-callsite-per-commit, gated on whether the matching ROM `act()` site
  carries a `MOBtrigger = FALSE` wrap. Judgment-per-callsite — surface a concrete
  gap, then close it directly (not a Ralph-loop queue).

## Next Steps

1. **Push approval** — `master` is now 2 commits ahead of `origin/master`
   (`dbcd5735` FIGHT-017 / 2.9.89 + `f2bd9723` FIGHT-018 / 2.9.90). Not pushed
   (awaiting approval).
2. **Pin the `room_registry` isolation leaker** (see Outstanding) — highest-value
   test-infra cleanup; it will keep surfacing under different worker groupings.
3. **INV-025 non-combat narration sweep** (see Outstanding) — optional, ad-hoc.
4. **GitNexus** — MCP query path read-only this session; on-disk graph stale
   (`6b7f80d`). Re-run `npx gitnexus analyze --skip-agents-md` once the DB lock
   clears.
