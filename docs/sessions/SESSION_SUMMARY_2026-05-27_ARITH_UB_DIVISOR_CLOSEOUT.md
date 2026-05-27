# Session Summary — 2026-05-27 — ARITH UB-divisor close-out (2.9.67)

## Scope

Picked up immediately after 2.9.66 from `docs/sessions/SESSION_STATUS.md`.
Continued closing low-impact UB-protection gaps from the META Class 2
ARITHMETIC_BOUNDARY triage (`docs/parity/audits/ARITHMETIC_BOUNDARY.md`).
The session's primary deliverable is a **policy doc**
(`docs/divergences/UB_DIVISORS.md`) that formalizes how the Python port
handles ROM's raw `int / int` divisions where the divisor could be zero
under degenerate state. ROM tolerates SIGFPE (one process); Python cannot
(one ZeroDivisionError would propagate through the dispatcher and crash
the game loop for every connected player) — so the existing `max(1, …)`
floors stay, and the audit rows shift from ❌ MISSING to ⛔ N/A with
ROM-cite comments.

Five ARITH gap rows reclassed to ⛔ N/A across two commits. No production
behavior change this session; the floors that were already in place are
now documented and pinned by regression tests where they materially
prevent a crash.

## Outcomes

### Policy / docs

#### `docs/divergences/UB_DIVISORS.md` — new file (`b5526d03`)

- **Rationale**: ROM 2.4b6 divides several character/object fields raw
  (`hp_percent = 100 * ch->hit / ch->max_hit`, `xp / total_levels`,
  `chance / (multiplier * rating * 4)`, …). Under degenerate state the
  divisor can be 0; ROM crashes one process with SIGFPE. Python's
  asymmetry: `ZeroDivisionError` would propagate through `command
  dispatcher → connection layer` and kill the whole MUD's game loop,
  not just one offender.
- **Policy**: For each ROM raw-division identified in the ARITH triage,
  the steps are (1) reachability probe, (2) keep the Python floor,
  (3) add a ROM-cite comment referencing the divergence doc,
  (4) reclass the audit row to ⛔ N/A, (5) add a regression test if the
  floor materially prevents a crash.
- **Anti-goal**: not a license to add new `max(1, …)` floors to ROM-parity
  code. Default for new code remains raw ROM math via `c_div`/`c_mod`.

### Gap reclassifications

#### `ARITH-011` — ⛔ N/A (reclassified, `b5526d03`)

- **Python**: `mud/commands/combat.py:512`
- **ROM C**: `src/fight.c:2310` (`hp_percent = 100 * ch->hit / ch->max_hit`)
- **Reachability**: PC-only path (gate at `combat.py:492` rejects NPCs
  without BERSERK off_flag, gate at `:504` requires mana ≥ 50). PC
  `max_hit` init defaults to `saved_hp or 20` at
  `mud/models/character.py:951-976`, so no steady-state PC path reaches
  the divide with `max_hit == 0`.
- **Decision**: Floor kept per UB-divisor policy; ROM-cite comment added.
- **Tests**: 1 new —
  `tests/test_arith_max_hit_floor.py::TestMaxHitFloorDivergence::test_berserk_with_zero_max_hit_does_not_raise`
  (pins the divergence so a future "ROM-strict" refactor can't quietly
  reintroduce the crash path).

#### `ARITH-012` — ⛔ N/A (reclassified, `b5526d03`)

- **Python**: `mud/commands/combat.py:636`
- **ROM C**: `src/act_move.c` do_flee `100 * ch->hit / ch->max_hit`
- **Reachability**: NPC-reachable. `_roll_dice` at
  `mud/spawning/templates.py:170-172` floors at 0 (not 1), so a mob proto
  with `hit_dice = (0, 0, 0)` will spawn with `max_hit == 0`. Any
  fighting NPC can invoke `do_flee`.
- **Decision**: Floor kept per UB-divisor policy; ROM-cite comment added.
  This is the materially-reachable case that justifies the policy doc.
- **Tests**: 1 new —
  `tests/test_arith_max_hit_floor.py::TestMaxHitFloorDivergence::test_flee_with_zero_max_hit_does_not_raise`.

#### `ARITH-006`/`ARITH-007`/`ARITH-008` — ⛔ N/A (reclassified, `fb8d97d2`)

- **Python**: `mud/groups/xp.py:166` (align > 500), `:170` (align < -500), `:174` (neutral)
- **ROM C**: `src/fight.c:1892` / `:1900` / `:1908` (`… / total_levels` raw)
- **Reachability**: dead defensive code. The upstream guard at
  `mud/groups/xp.py:111-112` floors `total_levels` to `max(1, ch.level)`
  *before* the loop at `:114-124` invokes `xp_compute` at `:117`.
  Therefore `total_levels` is always ≥ 1 inside `xp_compute`, and the
  inner `max(1, total_levels)` floors at the three alignment branches
  are unreachable. Same shape as ARITH-013 — post-gate dead code, not a
  UB-policy keeper.
- **Decision**: Single ROM-cite comment added at the three call sites
  pointing to the audit rows and the upstream guard. Audit row 44 (the
  upstream `xp.py:111-112` floor) is already ⛔ N/A with the canonical
  reachability note ("only used when entire group has 0 levels").

### Tally movement

Before this session: **56 ✅ / 44 ❌ / 115 N/A** (after 2.9.66).
After this session:  **56 ✅ / 39 ❌ / 120 N/A**.

ARITH gap-ID tally: **7 FIXED + 7 N/A** (ARITH-009, 011, 012, 006, 007,
008, 013), **32 ❌ MISSING remaining** (was 37 after 2.9.66).

## Files Modified

- `mud/commands/combat.py` — ROM-cite comments at :512 (ARITH-011) and :636 (ARITH-012). Comment-only.
- `mud/groups/xp.py` — single ROM-cite comment block above the three alignment branches at :166/:170/:174 (ARITH-006/007/008). Comment-only.
- `docs/divergences/UB_DIVISORS.md` — new policy doc.
- `docs/parity/audits/ARITHMETIC_BOUNDARY.md` — rows 46 / 48 / 51 / 62 / 64 flipped from ❌ MISSING to ⛔ N/A; status header and inline tally updated; ARITH-008 row line number corrected (`:173` → `:174`) and ARITH-006/007 line numbers similarly bumped to current source.
- `tests/test_arith_max_hit_floor.py` — new file, 2 regression tests pinning the UB-policy floors.
- `CHANGELOG.md` — two entries under `## [Unreleased]` documenting both reclass batches.
- `pyproject.toml` — 2.9.66 → 2.9.67 (handoff bump).

## Test Status

- `tests/test_arith_max_hit_floor.py` — 2/2 passing (new this session).
- `tests/test_skill_combat_rom_parity.py` + `tests/integration/test_flee_moves_character.py` — 105/105 passing.
- `tests/test_advancement.py` + `tests/integration/test_character_advancement.py` — 40/40 passing.
- Full integration suite not re-run this session; 2.9.64 baseline was
  2302/2302 + 3 documented skips in 84s and no production code changed
  this session (comments + audit doc + tests only).
- `ruff check mud/commands/combat.py tests/test_arith_max_hit_floor.py`
  — clean for the new test file; one pre-existing F541 at
  `combat.py:685` (unrelated, present before this session — see
  `do_flee` `messages.append(f"You flee from combat!")`).

## Next Steps

1. **Push approval still pending** — local `master` is now **6 commits**
   ahead of `origin/master` (4 from 2.9.66 + 2 this session, plus the
   handoff commit once it lands = 7).
2. **Continue closing ARITH gaps** via `/rom-gap-closer`. The UB-divisor
   policy lights up the path for **ARITH-001/002/003/014**:
   - **ARITH-001/002/003** — `max_hit`/`max_mana`/`max_move`
     `update_pos` floors at `mud/handler.py` (combat.py? confirm site)
     — likely same shape as ARITH-011 (PC-only divisors that init non-zero).
   - **ARITH-014** — `mud/skills/registry.py:330`
     (`max(1, multiplier * rating * 4)`) — ROM divides `chance / (mul *
     rating * 4)` raw; rating == 0 is upstream-filtered (skill table
     drop), so likely dead-code N/A. Quick reachability probe via the
     `skill_table` filter.
3. **ARITH-005** still needs separate analysis — the `gch_level` floor
   at `mud/groups/xp.py:130` is *not* dead code (changes
   `level_range = victim_level - 1` vs ROM's `victim_level - 0` for a
   level-0 PC). Need to determine whether a PC can actually reach
   `xp_compute` with `level == 0` (the first `group_gain` loop at
   `:100-109` skips level≤0 members from `total_levels` accumulation,
   but the second loop at `:114-124` only skips NPCs, so a level-0 PC
   *does* reach `xp_compute`).
4. **ARITH-105 (get_curr_stat)** still the largest remaining ARITH gap.
   High blast radius — every stat-dependent calc — plan for multiple
   commits or one careful commit with a comprehensive parametrized
   test across hit/dam/AC/carry/wield/sneak paths.
5. **Pre-existing lint** still parked at `mud/handler.py:566-567`,
   `mud/handler.py:960`, `tests/integration/test_do_practice_command.py:255`,
   `mud/commands/combat.py:685` — quick clean-ups available in passing.
6. **GitNexus**: stop-and-reindex rule fired twice this session
   (after `b5526d03` and after `fb8d97d2`); both reindexes were run
   in the background and completed before the next commit. FTS DB
   remains read-only at the MCP layer (documented upstream issue);
   node/edge graph is current.
7. **Worktree hygiene** — locked worktrees still present in
   `.claude/worktrees/`.
