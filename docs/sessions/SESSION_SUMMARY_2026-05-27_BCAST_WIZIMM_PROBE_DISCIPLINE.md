# Session Summary — 2026-05-27 — BCAST wiz/imm probe + bug-filing discipline (2.9.60)

## Headline

Second session of 2026-05-27. Continuation of Class 1 BROADCAST_COVERAGE
burn-down on the wiz/immortal cluster. **One real gap closed (BCAST-018
`do_quit`)**, **three rows reclassified ✅ COVERED** (BCAST-007 `do_envenom`,
BCAST-020 `do_report`, BCAST-029 `do_violate` — all false-positive
helper-transitivity matches), and **three rows annotated ⚠️ BLOCKED**
(BCAST-002 `do_clone`, BCAST-014 `do_mload`, BCAST-015 `do_oload`) by a
newly-filed pre-existing bug **WIZLOAD-001** (3 layered name typos in the
wiz-load/clone surface).

The session also produced a **workflow-discipline upgrade**: AGENTS.md
and `rom-gap-closer` SKILL.md now require out-of-scope bugs surfaced
mid-audit to be filed durably (INV-NNN, audit-doc IDs, or ⚠️ BLOCKED
annotations) before pivoting away. Chat-only mentions evaporate at
session end and have caused real regressions to ship.

Cumulative Class 1 BROADCAST_COVERAGE burn-down (since opening in 2.9.58):
**21 of 29 ❌ rows now resolved or routed** (8 fixed, 7 COVERED collapses,
3 ⚠️ BLOCKED, 3 deferred to next session). 8 ❌ + 10 ⚠️ remain (out of 209
✅ baseline).

## Commits (4 on master, ahead of `origin/master`)

| SHA | Type | Content |
|-----|------|---------|
| `f475d5e` | chore(workflow) | AGENTS.md + rom-gap-closer SKILL.md durable-bug-filing rule. Files INV-027 candidate (ACT-INVIS-TRUST-GATE) on the Watch list and WIZLOAD-001 in BROADCAST_COVERAGE.md "Blocked rows". |
| `54df514` | fix(parity) | BCAST-018 `do_quit` — TO_ROOM `$n has left the game.` emitted before disconnect. `tests/integration/test_quit_broadcasts.py` (3/3, incl. 2 negative pins). |
| `91e8969` | chore(parity) | BCAST-007/020/029 → ✅ COVERED row flips. BCAST-002/014/015 → ⚠️ BLOCKED annotations. WIZLOAD-001 expanded from 1 bug to 3 layered. |
| (pending) | chore(parity) | Session handoff: 2.9.60 version, CHANGELOG, summary, STATUS. |

## Outcomes

### `BCAST-018` — ✅ FIXED

- **Python**: `mud/commands/session.py:do_quit` (lines 36-67 post-fix)
- **ROM C**: `src/act_comm.c:1462-1518`, specifically `:1482`
  `act("$n has left the game.", ch, NULL, NULL, TO_ROOM)`
- **Fix**: emit `broadcast_room(room, f"{actor_name} has left the
  game.", exclude=ch)` after `save_character` and before the
  `_quit_requested` flag. The existing fight / below-STUNNED
  position guards already short-circuit before the broadcast,
  matching ROM ordering — no broadcast on blocked quit.
- **Tests**: `tests/integration/test_quit_broadcasts.py` (3/3 pass).
  Two negative-pin tests verify the broadcast does NOT fire when ROM
  blocks the quit (fighting or below STUNNED).
- **Adjacent suite**: 24/24 `quit`/`session` tests still green.

### `BCAST-007` — ✅ COVERED (false positive)

- **Python**: `mud/skills/handlers.py:envenom` (lines 3742, 3847)
- **ROM C**: `src/act_obj.c:887` (food/drink path), `:946` (weapon path)
- **Why false positive**: audit's static scan inspected
  `mud/commands/remaining_rom.py:do_envenom` (the dispatcher) but the
  real broadcasts live in `handlers.py:envenom`. Same helper-
  transitivity caveat as BCAST-004/005/026 (combat skills) collapsed
  in 2.9.59. No commit; audit-doc row flipped to ✅ COVERED.

### `BCAST-020` — ✅ COVERED (false positive)

- **Python**: `mud/commands/info.py:do_report` (lines 583-595)
- **ROM C**: `src/act_info.c:2673` (`$n says 'I have %d/%d hp...'`)
- **Why false positive**: Python uses an **inline `room.people`
  loop** that calls `desc.send(room_msg)` per non-self witness —
  semantically equivalent to `broadcast_room(room, msg, exclude=ch)`
  for the audit's act-coverage check. The regex scan only matches
  named helpers (`broadcast_room`, `_act_room`, etc.) and missed
  the inline form. No commit.

### `BCAST-029` — ✅ COVERED (false positive on act-emission axis)

- **Python**: `mud/commands/imm_server.py:do_violate` (lines 193-205)
  → `_act_room` helper at `imm_commands.py:473-481`.
- **ROM C**: `src/act_wiz.c:1031-1033` (bamfout), `:1046-1049` (bamfin)
- **Why false positive**: Python routes through `_act_room` for both
  old_room and new_room broadcasts; the helper iterates `room.people`
  and delivers to every non-self member. ROM's per-person loop is
  trust-gated by `get_trust(rch) >= ch->invis_level`; Python's
  `_act_room` has no such filter — that's a separate fidelity bug,
  not a missing broadcast.
- **Separate bug filed**: **INV-027 candidate ACT-INVIS-TRUST-GATE**
  in `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` Watch list. Wiz-
  invis actors are visible in every room/event broadcast regardless
  of witness trust — a long-standing parity gap any ROM player would
  notice. Proposed enforcement point: `_can_witness(actor, witness)`
  helper threaded through `_act_room` and `broadcast_room`.

### `BCAST-002` / `BCAST-014` / `BCAST-015` — ⚠️ BLOCKED by WIZLOAD-001

Three pre-existing bugs surfaced this session, all in the wiz-load/
clone command surface. All three commands silently broken in production
(no test coverage on the success path):

1. **`do_mload` registry-lookup name typo** (`mud/commands/imm_load.py:68`):
   reads `getattr(registry, "mob_prototypes", {}).get(vnum)`. Canonical
   attribute is `mob_registry`. Always early-returns "No mob has that
   vnum." regardless of vnum.

2. **`do_oload` double-broken** (`mud/commands/imm_load.py:121, 126-127`):
   (a) reads `registry.obj_prototypes` (canonical: `obj_registry`).
   (b) imports `spawn_obj` from `mud.spawning.obj_spawner` (canonical:
   `spawn_object`, no `level` arg).

3. **`do_clone` object-branch `spawn_obj` ImportError**
   (`mud/commands/imm_search.py:417, 424`): same import-name bug as
   `do_oload`. Mob branch (line 472, `spawn_mob`) is functional.

Filed as **WIZLOAD-001** in `docs/parity/audits/BROADCAST_COVERAGE.md`
"Blocked rows" section. Fix shape and effort estimate included; can be
closed in one ~25-line + 3 lookup-fix-test commit before BCAST-002/014/015
gap-closers can layer the broadcasts on top.

### Workflow-discipline upgrade

- **`AGENTS.md`** "Trackers" section now has an "Out-of-scope bugs
  surfaced mid-audit (file durably, do not just mention)" subsection
  with a routing table by bug shape: cross-file contract → INV-NNN;
  local divergence → per-file `<FILE>_C_AUDIT.md` with stable ID;
  blocks a gap → ⚠️ BLOCKED annotation + bug-ID reference; feature
  gap → `ROM_PARITY_FEATURE_TRACKER.md`.
- **`.claude/skills/rom-gap-closer/SKILL.md`** Anti-patterns gains a
  matching entry so the skill itself reminds the agent: "❌ Surfacing
  an unrelated pre-existing bug while closing the gap and only
  mentioning it in chat."

This was triggered by the do_mload bug being initially mentioned only
in chat — would have been lost at session end. The rule + checklist
now make verbal-only filings a recognized anti-pattern.

## Files Modified

- `mud/commands/session.py` — `do_quit` emits TO_ROOM before disconnect.
- `tests/integration/test_quit_broadcasts.py` (new, 3 tests).
- `AGENTS.md` — new "Out-of-scope bugs" subsection under Trackers.
- `.claude/skills/rom-gap-closer/SKILL.md` — new Anti-pattern.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-027 candidate
  ACT-INVIS-TRUST-GATE on Watch list.
- `docs/parity/audits/BROADCAST_COVERAGE.md` — 7 row updates
  (BCAST-002, 007, 014, 015, 018, 020, 029) + WIZLOAD-001 expanded
  in "Blocked rows" section.
- `CHANGELOG.md` — 2.9.60 section with Fixed (BCAST-018) and Changed
  (3 COVERED collapses + 3 BLOCKED annotations).
- `pyproject.toml` — 2.9.59 → 2.9.60.
- `docs/sessions/SESSION_SUMMARY_2026-05-27_BCAST_WIZIMM_PROBE_DISCIPLINE.md` (new).
- `docs/sessions/SESSION_STATUS.md` — refreshed, points at new summary.

## Test Status

- `pytest tests/integration/test_quit_broadcasts.py` — 3/3 passing.
- `pytest tests/integration/ -k "quit or session"` — 24/24 passing.
- Full `pytest tests/integration/` — not re-run this sub-session;
  validated 2270/2270 + 3 documented skips in 2:13 during the prior
  2.9.59 session (an hour earlier). My changes only touch
  `mud/commands/session.py:do_quit` (additive — a new broadcast
  before an existing flag set) and audit-doc/CHANGELOG/skill files;
  no regression vector beyond the quit/session adjacent suite.

## Next Steps

1. **Finalize session chore commit** (in progress as this summary is
   written) — 2.9.60 version bump, CHANGELOG header, this summary,
   refreshed SESSION_STATUS.
2. **Push approval** required for 2.9.60 (4 commits to push).
3. **WIZLOAD-001** — close the 3 layered name typos as a single
   ~25-line + 3-test commit. Unblocks BCAST-002/014/015 immediately.
   Skill: ad-hoc bug-fix commit (not a `rom-gap-closer` pass — it's
   not a parity gap, it's a typo).
4. **Then BCAST-002/014/015 gap closures** — standard `rom-gap-closer`
   per ID, single broadcast each.
5. **Remaining viable BCAST real gaps** (next-session priorities):
   - **BCAST-017 `do_order`** (1 TO_VICT, `act_comm.c:1650`).
   - **BCAST-019 `do_reply`** (1 TO_VICT, `act_comm.c:928`) —
     symmetric to do_tell which was fixed in 2.9.17.
   - **BCAST-010 `do_gtell`** (1 TO_VICT, `act_comm.c:1948`).
   - **BCAST-028 `do_value`** (4 TO_VICT, `act_obj.c:2904`)
     shopkeeper haggle responses.
   - **BCAST-009 `do_group`** (5 acts) — 2.9.20 already shipped a
     fix per session notes; re-verify whether the regex missed it
     and it's now ✅ COVERED.
6. **Expensive remaining BCAST** (large act counts, do later):
   BCAST-006 `enter` (5), BCAST-021-024 `rest`/`sit`/`sleep`/`stand`
   (4-12 each).
7. **⚠️ Partial closures** (BCAST-030 `bash`, 031 `buy`, 032 `force`,
   033 `give`, 034 `pick`, 035 `purge`, 036 `recall`, 037 `sell`,
   038 `steal`, 039 `transfer`).
8. **INV-027 promotion** (ACT-INVIS-TRUST-GATE): write the
   regression test, thread `_can_witness` through `_act_room` and
   `broadcast_room`, promote from Watch list to ✅ ENFORCED.
9. **Pre-existing flake** at
   `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`
   — still unresolved.
10. **GitNexus reindex** still stale (last `069f17f`); now ~25 commits
    behind. FTS index still read-only per the per-tool warnings this
    session. Run `npx gitnexus analyze --skip-agents-md` before the
    next probe session.
11. **Worktree hygiene** still pending (5 locked worktrees).
