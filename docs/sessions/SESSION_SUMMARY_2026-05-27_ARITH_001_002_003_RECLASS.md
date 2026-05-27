# Session Summary — 2026-05-27 — ARITH-001/002/003 UB-divisor reclass (2.9.68)

## Scope

Picked up immediately after 2.9.67 from `docs/sessions/SESSION_STATUS.md`,
which named ARITH-001/002/003 as the next quick-N/A candidates now that
the UB-divisor policy doc (`docs/divergences/UB_DIVISORS.md`) is in
place. All three are `max(1, max_hit)` divisor floors in mob-program
and damage-message code; the working hypothesis was the same shape as
ARITH-012 (NPC-reachable via degenerate `hit_dice`, kept as deliberate
divergence). Probe confirmed it. Single commit covers all three;
no production behavior change.

## Outcomes

### `ARITH-001` — ⛔ N/A (reclassified, `0af47cf2`)

- **Python**: `mud/mobprog.py:1108` (`hpcnt` check in `_evaluate_if`)
- **ROM C**: `src/mob_cmds.c` — hpcnt check, `current * 100 / max_hit` raw
- **Reachability**: NPC-reachable. `target_char` of an `hpcnt` check
  can be any character (including PCs and NPCs). For an NPC target,
  `mud/spawning/templates.py:170-172` floors `_roll_dice` at 0 (not 1),
  so a mob proto with degenerate `hit_dice = (0,0,0)` spawns with
  `max_hit == 0`. The `getattr(..., 1)` default only fires when the
  attribute is missing entirely — it does NOT mask a literal-zero
  `max_hit`. The floor IS reachable.
- **Decision**: Floor kept per UB-divisor policy; ROM-cite comment
  added at `mud/mobprog.py:1105-1107`.

### `ARITH-002` — ⛔ N/A (reclassified, `0af47cf2`)

- **Python**: `mud/mobprog.py:1651` (HPCT trigger in
  `try_trigger_hpcnt`)
- **ROM C**: `src/mob_cmds.c` — HPCT trigger, `current * 100 / max_hit`
  raw
- **Reachability**: Same shape as ARITH-001 but `mob` is always an
  NPC. Identical degenerate-`hit_dice` reachability.
- **Decision**: Floor kept per UB-divisor policy; ROM-cite comment
  added at `mud/mobprog.py:1649-1650`.

### `ARITH-003` — ⛔ N/A (reclassified, `0af47cf2`)

- **Python**: `mud/combat/messages.py:115` (`_severity_terms`, called
  from `dam_message`)
- **ROM C**: `src/fight.c:dam_message` — `damage * 100 / victim->max_hit`
  raw
- **Reachability**: NPC-reachable. The prior line explicitly
  normalizes a missing/zero attribute to 0
  (`getattr(victim, "max_hit", 0) or 0`), so the `max(1, ...)` floor
  IS the active guard on the divisor — not dead code. ROM dam_message
  divides raw with no guard, SIGFPEs on degenerate mob `max_hit`.
- **Decision**: Floor kept per UB-divisor policy; ROM-cite comment
  added at `mud/combat/messages.py:115-117`.

### Subagent correction

The initial Explore subagent probe classified ARITH-001/002 as "dead
defensive code" by analogy to ARITH-006/007/008, on the theory that
`max_hit` is "always ≥ 1" from character creation. That's wrong:
`_roll_dice` floors at 0, not 1, and the `getattr(..., 1)` defaults
only mask a missing attribute, not a literal-zero value. Direct read
of `mud/spawning/templates.py:170-172` overrode the subagent's claim.
Per `superpowers:receiving-code-review`-style reasoning: primary
source (the spawn code) beats secondary analysis.

## Files Modified

- `mud/mobprog.py` — ROM-cite comments at `:1105-1107` and `:1649-1650`
  (above the two `max(1, ...)` floors).
- `mud/combat/messages.py` — ROM-cite comment at `:115-117`.
- `docs/parity/audits/ARITHMETIC_BOUNDARY.md` — rows 22/23/24 flipped
  to ⛔ N/A with full re-analysis notes; status banner updated
  (tally 56 ✅ / 39 ❌ / 120 N/A, effective open ❌ MISSING 29).
- `CHANGELOG.md` — new `## [2.9.68]` section under `### Changed`.
- `pyproject.toml` — 2.9.67 → 2.9.68.

## Test Status

- `tests/test_arith_max_hit_floor.py` — 2/2 passing (UB-divisor
  regressions for berserk/flee).
- `tests/integration/test_character_advancement.py` — 21/21 passing
  (cross-check that the prior ARITH-024 zero-XP fix still holds).
- `tests/test_mobprog.py` — 2/2 passing.
- `tests/test_combat_messages.py` — 2/2 passing.
- Full suite not re-run this session; 2.9.64 baseline was
  2302/2302 + 3 documented skips in 84s. No production code changed
  this session (comment-only edits to two `.py` files).

## Next Steps

1. **Push approval needed** — local master now 8 commits ahead of
   origin for 2.9.68 (4 from 2.9.66 + 4 from 2.9.67/2.9.68 series
   including this commit).
2. **Continue closing ARITH gaps** via `/rom-gap-closer`. The
   UB-divisor cluster has one row left from the policy doc's
   coverage list:
   - **ARITH-014** (`mud/skills/registry.py:330`,
     `max(1, multiplier * rating * 4)`) — rating == 0 means the skill
     has no class rating and is filtered upstream by `skill_table`.
     Likely dead-code N/A like ARITH-006/007/008. Quick reachability
     probe needed (does the filter actually fire before this divide?).
3. **ARITH-005** needs separate analysis. The `gch_level` floor at
   `mud/groups/xp.py:130` is *not* dead code (`max(1, ...)` changes
   `level_range = victim_level - 1` vs ROM's `victim_level - 0` for
   a level-0 PC). The first `group_gain` loop at `:100-109` skips
   level≤0 members from `total_levels` accumulation, but the second
   loop at `:114-124` only skips NPCs, so a level-0 PC *does* reach
   `xp_compute`. Need a reachability probe on whether `level == 0`
   is itself reachable for a logged-in PC.
4. **ARITH-105 (get_curr_stat)** still the largest remaining ARITH
   gap. ROM uses `URANGE(3, perm+mod, max)` — minimum stat is **3**,
   not 0. Python floors at 0 (`mud/models/character.py:478`). High
   blast radius — every stat-dependent calc (hit/dam/AC/carry/wield/
   sneak). Plan for multiple commits or one careful commit with a
   comprehensive parametrized test across the affected paths.
5. **ARITH-209 spot-check** still pending
   (`mud/loaders/json_loader.py:357` — comment claims a ROM
   `max(1, arg4)` floor that may not exist).
6. **Pre-existing lint** still parked: `mud/handler.py:566-567`
   (F841), `mud/handler.py:960` (F401),
   `tests/integration/test_do_practice_command.py:255` (F841),
   `mud/commands/combat.py:685` (F541) — quick clean-ups available
   in passing.
7. **GitNexus**: stop-and-reindex rule fired once this session (after
   `0af47cf2`); reindex kicked off in background. FTS DB remains
   read-only at the MCP layer (documented upstream issue); node/edge
   graph is current.
8. **Pre-existing flake** at
   `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
9. **Worktree hygiene** — locked worktrees still present in
   `.claude/worktrees/`.
