# Session Summary — 2026-05-27 — ARITH coin weights, zero-XP delivery, ARITH-009 reclass (2.9.66)

## Scope

Picked up immediately after 2.9.65 from `docs/sessions/SESSION_STATUS.md`.
Continued closing high-impact gaps from the META Class 2
ARITHMETIC_BOUNDARY triage (`docs/parity/audits/ARITHMETIC_BOUNDARY.md`).
The session's next-suggested gap was **ARITH-009** (`xp_compute` floor) —
but careful re-analysis showed that floor is dead-code defensive (parallel
to ARITH-013). Reclassifying it surfaced the *real* divergence the audit
prose was groping at: an unconditional `group_gain` gate that swallows
both the message and the `gain_exp` call when xp == 0. That became
ARITH-024, filed and immediately closed. Then closed the
**ARITH-101/102/103** coin-weight sibling cluster in a single commit
(same ROM function, three branches, parametrized test).

## Outcomes

### Process / docs

#### `ARITH-009` — ⛔ N/A (reclassified, `8c7bce55`)

- **Python**: `mud/groups/xp.py:257`
- **ROM C**: `src/fight.c:2031`
- **Re-analysis**: `xp_compute` arithmetic has no path to a negative
  result. `base_exp >= 0` (line 156 early-returns 0 if not), all
  subsequent `c_div` ops preserve sign, `number_range(low, high)` is
  well-formed because `low = xp*3/4 <= high = xp*5/4` when xp >= 0, and
  the final `c_div(xp * gch_level, divisor)` is positive/positive. The
  `max(0, xp)` floor at line 257 is unreachable. Audit prose's "ROM can
  return negative XP via alignment math" was a misdiagnosis — alignment
  math mutates `gch.alignment`, it does not feed back into xp.
- **Real divergence** surfaced and filed as **ARITH-024** (see below).

### Gap closures

#### `ARITH-024` — ✅ FIXED (`687aca2c`)

- **Python**: `mud/groups/xp.py:117-122`
- **ROM C**: `src/fight.c:1786-1789`
- **Gap**: `group_gain` had `if xp <= 0: continue` between
  `xp_compute(...)` and the message + `gain_exp` calls. ROM's `group_gain`
  members loop is unconditional — `sprintf "You receive %d experience
  points."`, `send_to_char`, and `gain_exp(gch, xp)` always fire.
  Reachable when `xp_compute` returns 0 — i.e. when `level_range < -9`
  or sits outside the `base_exp` table (any time the group has a player
  far above the kill's level).
- **Fix**: Removed the `xp <= 0` early-continue. The
  `_drop_alignment_conflicts(ch)` call after each member still runs
  unconditionally, matching ROM's anti-alignment zap loop at
  `fight.c:1791-1806`.
- **Tests**: 1 new —
  `tests/integration/test_character_advancement.py::test_group_gain_zero_xp_still_delivers_message_and_gain_exp`
  (forces `xp_compute -> 0` via monkeypatch, asserts message hits
  `char.messages` and `gain_exp` is called with 0).

#### `ARITH-101`/`ARITH-102`/`ARITH-103` — ✅ FIXED (`c105ed0f`)

- **Python**: `mud/handler.py:995` (gold-only), `:1003` (silver-only),
  `:1011` (mixed).
- **ROM C**: `src/handler.c:2455` / `:2465` / `:2477`.
- **Gap**: Each branch used `max(1, ...)` on the weight computation,
  inflating small coin stacks to weight 1 when ROM gives weight 0:
  1–4 gold (gold-only), 1–19 silver (silver-only), small mixed stacks
  whose components both quotient to 0.
- **Fix**: Replaced with raw `c_div(gold, 5)`, `c_div(silver, 20)`,
  `c_div(gold, 5) + c_div(silver, 20)` respectively. Added function-
  local `from mud.math.c_compat import c_div` (style matches the
  function's other lazy imports). Closed in a single commit because the
  divergence is one ROM function across three branches.
- **Tests**: 1 new parametrized test with 9 cases —
  `tests/integration/test_money_objects.py::test_create_money_weight_matches_rom_raw_division`
  (below-floor / at-floor / above-floor per branch).
- **Note on existing tests**: `test_money_object_small_amount_has_minimum_weight`
  uses `(gold=0, silver=1)` which hits the OBJ_VNUM_SILVER_ONE early
  branch (hardcoded `weight = 1` in both ROM and Python). It still
  passes — the fix only affects the GOLD_SOME / SILVER_SOME / COINS
  branches.

## Files Modified

- `mud/groups/xp.py` — ARITH-024 fix (removed `xp <= 0` early-continue;
  added ROM citation comment).
- `mud/handler.py` — ARITH-101/102/103 fix (3 weight expressions
  replaced with raw `c_div`; added function-local import).
- `tests/integration/test_character_advancement.py` — new test
  `test_group_gain_zero_xp_still_delivers_message_and_gain_exp`.
- `tests/integration/test_money_objects.py` — new parametrized test
  `test_create_money_weight_matches_rom_raw_division` (9 cases).
- `docs/parity/audits/ARITHMETIC_BOUNDARY.md` — rows flipped:
  ARITH-009 ⛔ N/A, ARITH-024 newly filed and ✅ FIXED,
  ARITH-101 ✅ FIXED, ARITH-102 ✅ FIXED, ARITH-103 ✅ FIXED.
  Summary tally / status header / high-impact section all refreshed.
- `CHANGELOG.md` — new `[2.9.66]` section with Fixed (ARITH-024,
  ARITH-101/102/103) and Changed (ARITH-009 reclass) entries.
- `pyproject.toml` — 2.9.65 → 2.9.66.

## Test Status

- `pytest tests/integration/test_character_advancement.py tests/integration/test_group_xp_npc_level_floor.py tests/integration/test_group_combat.py tests/test_combat_death.py` — **61 passed, 1 skipped** in 13.4s. (ARITH-024 area.)
- `pytest tests/integration/test_money_objects.py tests/integration/test_drop_command.py tests/integration/test_container_retrieval.py tests/integration/test_room_retrieval.py tests/integration/test_inv014_object_registry_membership.py` — **76 passed** in 2.5s. (ARITH-101/102/103 area.)
- Full integration suite not re-run this session. 2.9.64 baseline was
  2302/2302 + 3 documented skips in 84s.
- Pre-existing lint at `mud/handler.py:566/567` (F841 unused `where`,
  `vector`) and `mud/handler.py:960` (F401 unused `Object` import) is
  not mine and was present before this session.
- Pre-existing flake at
  `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`
  unchanged.

## Commits

| SHA | |
|-----|---|
| `8c7bce55` | `docs(parity): reclassify ARITH-009 to N/A; file ARITH-024 for real divergence` |
| `687aca2c` | `fix(parity): ARITH-024 — group_gain delivers zero-xp message and gain_exp unconditionally` |
| `c105ed0f` | `fix(parity): ARITH-101/102/103 — create_money weights match ROM raw division` |

(plus this session's handoff commit once written.)

## ARITHMETIC_BOUNDARY tally (running)

| State | Count | IDs |
|-------|-------|-----|
| ✅ FIXED (session-cumulative across 2.9.65 + 2.9.66) | 7 | ARITH-010, ARITH-015, ARITH-016, ARITH-024, ARITH-101, ARITH-102, ARITH-103 |
| ⛔ N/A (reclassified) | 2 | ARITH-009, ARITH-013 |
| ❌ MISSING — open | 37 | (45 triage − 7 FIXED − 2 N/A + 1 ARITH-024 then FIXED) |

## Outstanding / next agent

- **Next gaps to close** (priority order, refined):
  - **ARITH-011/012** — `max_hit` floor in berserk/flee hp%. Reachability
    probe: berserk doesn't gate on max_hit > 0, only on mana >= 50. A
    char with max_hit == 0 reaching this code is theoretically possible
    but requires a corrupt/uninit character. Same pattern as ARITH-013
    (post-gate dead code) — needs character-init reachability check to
    confirm. If reachable, fix is straightforward; if not, reclass to
    N/A.
  - **ARITH-105** (`mud/models/character.py:478`) — `get_curr_stat`
    floor of 0 vs ROM's URANGE(3, perm+mod, max). High blast radius
    (every stat-dependent calc). Needs broad integration test coverage.
  - **ARITH-209 spot-check** — pending (`mud/loaders/json_loader.py:357`
    comment claims ROM `max(1, arg4)` that may not exist).
- **UB-protection cluster policy** (ARITH-001/002/003/005/006/007/008/014, and 011/012 if reachable) still undecided. Likely `assert` + `docs/divergences/` note rather than direct ROM replication.
- **Pre-existing lint** in `mud/handler.py` (F841 + F401, unrelated) and
  `tests/integration/test_do_practice_command.py:255` (F841 unused
  `output`) ready to clean up in passing.
- **Worktree hygiene** — locked worktrees still present in `.claude/worktrees/`.

## GitNexus

Stop-and-reindex rule honoured throughout:
- Reindexed after `8c7bce55` (ARITH-009 reclass + ARITH-024 file).
- Reindexed after `687aca2c` (ARITH-024 fix).
- Reindexed after `c105ed0f` (ARITH-101/102/103 fix).

FTS DB remains read-only at the MCP-server layer (pre-existing upstream
issue, see CLAUDE.md "Known GitNexus Indexing Gap"). Node/edge graph
itself is current after each reindex.
