# Session Summary — 2026-05-27 — BCAST door-command burn-down (2.9.59)

## Headline

Class 1 BROADCAST_COVERAGE burn-down continued. **Four door-command
gaps closed** (BCAST-016 `do_open`, BCAST-003 `do_close`, BCAST-013
`do_lock`, BCAST-027 `do_unlock`) — 13 new broadcast emissions total
across portal/container/door/linked-room paths. **Three combat-skill
rows collapsed as false positives** (BCAST-004 `do_dirt`, BCAST-005
`do_disarm`, BCAST-026 `do_trip`) after a parallel-subagent probe
confirmed they emit via `mud/skills/handlers.py` rather than the
`mud/commands/combat.py` dispatcher the audit's static scan inspected.

Cumulative Class 1 progress: **11 of 29 ❌ rows resolved** (7 fixed,
4 false-positive collapses) since the burn-down opened in 2.9.58.

## Commits (5 on master, ahead of `origin/master`)

| SHA | Gap | File |
|-----|-----|------|
| `f8370790` | BCAST-016 | `mud/commands/doors.py:do_open` + `test_door_broadcasts.py` (4/4) |
| `47fd235e` | BCAST-003 | `mud/commands/doors.py:do_close` + `test_close_broadcasts.py` (4/4) |
| `b76194da` | BCAST-013 | `mud/commands/doors.py:do_lock` + `test_lock_broadcasts.py` (3/3) |
| `896c72ff` | BCAST-027 | `mud/commands/doors.py:do_unlock` + `test_unlock_broadcasts.py` (3/3) |
| (pending) | Chore: false-positive row flips + version bump + CHANGELOG + session docs | — |

## Gaps closed

| ID | Bug | Pre-fix | Fix |
|----|-----|---------|-----|
| BCAST-016 | `do_open` returned only "Ok." / "You open $p." — portal, container, and door TO_ROOM broadcasts all silently dropped; linked-room never saw the door open from the other side | 0 broadcasts | Added 4 broadcasts: portal `$n opens $p.`, container `$n opens $p.`, door `$n opens the $d.`, linked-room `The $d opens.`. Introduced `_door_keyword(pexit)` helper for ROM's `$d` first-word-of-keyword substitution |
| BCAST-003 | `do_close` symmetric to BCAST-016 — same 4 missing broadcasts | 0 broadcasts | Added all 4 close-side broadcasts using `_door_keyword` |
| BCAST-013 | `do_lock` returned only "*Click*" — 3 TO_ROOM broadcasts missing | 0 broadcasts | Added portal/container/door TO_ROOM broadcasts. **Pinned ROM asymmetry**: lock does NOT broadcast to linked room (silent `SET_BIT`); negative assertion in test enforces this |
| BCAST-027 | `do_unlock` symmetric to BCAST-013 — same 3 missing | 0 broadcasts | Added unlock-side broadcasts; same linked-room-silent asymmetry pinned |

## False positives collapsed

- **BCAST-004** (`do_dirt`): audit-counted 2 ROM acts vs Py=0. Probe
  confirmed `mud/skills/handlers.py:3018-3026` emits TO_ROOM
  `"$n is blinded by the dirt in their eyes!"` and TO_VICT
  `"$n kicks dirt in your eyes!"`. **No code commit** — audit-doc flip
  rolled into the chore commit.
- **BCAST-005** (`do_disarm`): all three ROM branches (success / failure
  / NOREMOVE) emit TO_VICT + TO_NOTVICT in `handlers.py:3108-3134`.
- **BCAST-026** (`do_trip`): TO_VICT + manual `room.people`-loop TO_NOTVICT
  in `handlers.py:7691-7701`.

The audit's static scan inspected the `combat.py` dispatcher entries
(`do_dirt`, `do_disarm`, `do_trip`) but those are thin wrappers — the
actual broadcasts live in the skill-handler module. Helper-transitivity
caveat (analogous to the BCAST-001/008 `_act_room` collapse in 2.9.58).

## Method notes

- **Parallel-subagent probe pattern worked well.** Two read-only
  Sonnet subagents in parallel: one probed combat-skill BCAST coverage
  (returned all 3 COVERED with file:line evidence), one probed door
  commands (returned 2 REAL GAPS + 2 PARTIAL with file:line evidence).
  Total probe wall-clock ~60s; the alternative was sequential reads
  worth ~5-10 minutes of mainline tool calls. The subagents had no
  conversation context but needed none — the BCAST IDs from the audit
  doc were sufficient briefing.
- **Sequential gap-closes on mainline.** Per AGENTS.md "one gap = one
  test = one commit", each of the four door fixes was its own
  failing-test-first commit. The four touch the same file (`doors.py`)
  but the file is small (~600 lines) and no merge hazard, so sequential
  edits worked cleanly. Total mainline wall-clock ~30 min for 4 commits.
- **Pre-existing pytest slowness re-encountered.** `pytest -q` (full
  suite) hung past 15 minutes on this machine; killed and validated
  on `pytest tests/integration/` (2270 passed, 3 documented skips,
  2:13). Per AGENTS.md the integration suite is the right surface for
  parity work, so this was sufficient.

## New integration tests (4 files, 14 cases)

- `tests/integration/test_door_broadcasts.py` (4 cases — open)
- `tests/integration/test_close_broadcasts.py` (4 cases — close)
- `tests/integration/test_lock_broadcasts.py` (3 cases — lock, + negative pin)
- `tests/integration/test_unlock_broadcasts.py` (3 cases — unlock, + negative pin)

## Audit doc updates

`docs/parity/audits/BROADCAST_COVERAGE.md` rows flipped:

- Row 3 (`close`) → ✅ FIXED (2.9.59), broadcast count 0 → 3
- Row 4 (`dirt`) → ✅ COVERED (2.9.59), false positive
- Row 5 (`disarm`) → ✅ COVERED (2.9.59), false positive
- Row 13 (`lock`) → ✅ FIXED (2.9.59), broadcast count 0 → 3
- Row 16 (`open`) → ✅ FIXED (2.9.59), broadcast count 0 → 3
- Row 26 (`trip`) → ✅ COVERED (2.9.59), false positive
- Row 27 (`unlock`) → ✅ FIXED (2.9.59), broadcast count 0 → 3

Burn-down state (cumulative since burn-down opened in 2.9.58):
**11 of 29 ❌ rows resolved** (7 fixed, 4 false-positive collapses).
18 ❌ + 10 ⚠️ rows remain (out of 209 ✅ baseline).

## Outstanding

1. **Movement / position commands** — likely the most expensive
   remaining BCAST rows by act count:
   - BCAST-006 `enter` (5 ROM acts, `src/act_enter.c:43`)
   - BCAST-021 `rest` (12 acts, `src/act_move.c:1078`)
   - BCAST-022 `sit` (10 acts, `src/act_move.c:1217`)
   - BCAST-023 `sleep` (4 acts, `src/act_move.c:1343`)
   - BCAST-024 `stand` (8 acts, `src/act_move.c:967`)
2. **Shop commands** — high-cardinality TO_VICT acts:
   - BCAST-028 `value` (4 TO_VICT, `src/act_obj.c:2904`)
   - BCAST-031 `buy` ⚠️ partial (3 of 9), BCAST-037 `sell` ⚠️ (2 of 5)
3. **Wiz / immortal commands** — BCAST-002 `clone`, BCAST-014 `mload`,
   BCAST-015 `oload`, BCAST-018 `quit`, BCAST-020 `report`,
   BCAST-029 `violate`. Mostly 1-2 acts each — cheap closures.
4. **Group / communication** — BCAST-009 `group`, BCAST-010 `gtell`,
   BCAST-017 `order`, BCAST-019 `reply` (all 1-5 acts).
5. **Combat (real gaps remaining)** — BCAST-007 `envenom`
   (2 acts, `src/act_obj.c:820`), plus the ⚠️ partials
   BCAST-030 `bash`, BCAST-032 `force`, BCAST-033 `give`,
   BCAST-034 `pick`, BCAST-035 `purge`, BCAST-036 `recall`,
   BCAST-038 `steal`, BCAST-039 `transfer`.
6. **INV-024 candidate (VISIBILITY-TRANSITION-BROADCAST-ORDERING)**:
   no new instances this session (door commands don't carry visibility
   transitions). Still 2 instances logged from 2.9.58; await a third
   before promoting.
7. **GitNexus reindex** still stale (last `069f17f`); now ~20 commits
   behind. The MCP server reported FTS index read-only/broken
   throughout the session — `gitnexus_impact` calls would have been
   unreliable, so falls back to `grep` + integration-suite-as-blast-
   radius were used per CLAUDE.md.
8. **Worktree hygiene** still pending from prior session (5 locked
   worktrees in `.claude/worktrees/`).
9. **Pre-existing flake**
   `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`
   — still unresolved.
