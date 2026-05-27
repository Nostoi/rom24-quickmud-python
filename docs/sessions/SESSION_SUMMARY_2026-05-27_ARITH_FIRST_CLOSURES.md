# Session Summary — 2026-05-27 — First ARITH gap closures (2.9.65)

## Scope

Continued immediately after 2.9.64's Class 2 ARITHMETIC_BOUNDARY triage.
Goal: start closing gap candidates from `docs/parity/audits/ARITHMETIC_BOUNDARY.md`.
Also hardened the CLAUDE.md GitNexus-stale guidance into a strong
stop-and-reindex rule because the last few sessions noted "index stale"
without acting on it, and downstream `gitnexus_impact` answers degraded.

## Outcomes

### Process / docs

#### CLAUDE.md stop-and-reindex rule — committed (`b5b228f6`)

- Upgraded the prior soft guidance ("if stale, run `npx gitnexus
  analyze`") to a NON-NEGOTIABLE STOP-AND-REINDEX directive: any
  "index stale" / "FTS index ensure failed" signal triggers an
  immediate `npx gitnexus analyze --skip-agents-md` run before the
  next non-trivial tool call. Exception only when the reindex itself
  fails.
- Honoured the rule throughout this session — reindexed after each
  parity commit even though FTS DB remains read-only at the MCP
  layer.

### Gap closures

#### `ARITH-010` — ✅ FIXED (`3fff0065`)

- **Python**: `mud/commands/advancement.py:174`
- **ROM C**: `src/act_info.c:2772-2774`
- **Gap**: `do_practice` floored skill increment to 1 via
  `max(1, gain_rate // max(1, rating))`. ROM divides raw — when
  `int_app[INT].learn / rating` rounds to 0 (low-INT character
  practising a high-rating skill), ROM leaves `learned[sn]` unchanged
  but still decrements `ch->practice`.
- **Fix**: Replaced with `c_div(gain_rate, rating)` (no floor). The
  `rating > 0` precondition at `combat.py:162-163` mirrors ROM
  `act_info.c:2752-2755` and guarantees no div-by-zero.
- **Tests**: 1 new — `tests/integration/test_do_practice_command.py::test_practice_low_int_high_rating_skill_yields_zero_increment` (sets INT-learn=3, rating=10, verifies practice decrements but skill stays at 50%).

#### `ARITH-013` — ⛔ N/A (reclassified, `646dc8dd`)

- **Python**: `mud/commands/combat.py:779`
- **ROM C**: `src/magic.c:347-352` (inline `do_cast` mana formula)
- **Re-analysis**: Both the `char_level + 2 == required_level` branch
  (mana_cost = 50) and the `max(1, divisor)` floor branch are
  unreachable because the pre-flight gate at `combat.py:765-770`
  rejects `char_level < required_level` identically to ROM
  `magic.c:329-335`. After the gate, divisor ≥ 2 always. The
  standalone ROM helper `mana_cost()` at `magic.c:287-292` (which
  returns 1000 in the equivalent branch) is declared in `merc.h` but
  never called from any `.c` file.
- **Tally adjustment**: 56 ✅ MATCH / 44 ❌ MISSING / 115 N/A (was 45 ❌).

#### `ARITH-015` — ✅ FIXED (`928aa517`)

- **Python**: `mud/skills/handlers.py:1445`
- **ROM C**: `src/fight.c:2333`
- **Gap**: `berserk` had `base = max(1, c_div(level, 8))` then
  `number_fuzzy(base)`. ROM passes `ch->level / 8` raw to
  `number_fuzzy`. The function's own UMAX (`src/db.c:3496`) means the
  divergence is a **25% output-distribution shift**, not a clamp to
  zero — pre-fix gave duration 2 in roll=3 cases for low-level (0–7)
  callers; ROM deterministically gives 1.
- **Fix**: Replaced with `rng_mm.number_fuzzy(c_div(level, 8))`.
- **Tests**: 1 new — `tests/integration/test_berserk_duration.py::test_berserk_passes_raw_level_div_8_to_number_fuzzy` (spies on `number_fuzzy` argument).
- **Audit note correction**: ARITH-015's original triage claim
  ("0-duration berserk for levels 1–7") was wrong — number_fuzzy's
  inner UMAX makes 0-duration impossible. Audit doc corrected.

#### `ARITH-016` — ✅ FIXED (`03b7a5e2`)

- **Python**: `mud/skills/handlers.py:2121`
- **ROM C**: `src/magic.c:1383`
- **Gap**: Same shape as ARITH-015 — `charm_person` had
  `max(1, c_div(level, 4))` then `number_fuzzy(...)`. ROM passes
  raw `level / 4`. 25% output-distribution shift for levels 0–3.
- **Fix**: Replaced with `rng_mm.number_fuzzy(c_div(level, 4))`.
- **Tests**: 1 new — `tests/integration/test_charm_person_duration.py::test_charm_person_passes_raw_level_div_4_to_number_fuzzy`.
- **Audit note correction**: same as ARITH-015 — original "0-duration
  charm" claim corrected.

## Files Modified

- `CLAUDE.md` — strong stop-and-reindex rule.
- `mud/commands/advancement.py` — ARITH-010 fix + `c_div` import.
- `mud/skills/handlers.py` — ARITH-015 (`berserk` line 1445) and
  ARITH-016 (`charm_person` line 2121) fixes.
- `tests/integration/test_do_practice_command.py` — 1 new test.
- `tests/integration/test_berserk_duration.py` — new, 1 test.
- `tests/integration/test_charm_person_duration.py` — new, 1 test.
- `docs/parity/audits/ARITHMETIC_BOUNDARY.md` — rows flipped:
  ARITH-010 ✅ FIXED, ARITH-013 ⛔ N/A, ARITH-015 ✅ FIXED,
  ARITH-016 ✅ FIXED. Status header reflects updated tally.
- `CHANGELOG.md` — new `[2.9.65]` section.
- `pyproject.toml` — 2.9.64 → 2.9.65.

## Test Status

- `pytest tests/integration/test_do_practice_command.py` — 17/17.
- `pytest tests/integration/test_berserk_duration.py` — 1/1.
- `pytest tests/integration/test_charm_person_duration.py` — 1/1.
- `pytest tests/integration/test_skills_integration.py tests/integration/test_spell_casting.py` — 41/41 + 1 documented skip.
- Full integration suite not re-run this session — 2.9.64 baseline
  was 2302/2302 + 3 documented skips in 84s.
- Pre-existing lint warning at `test_do_practice_command.py:255`
  (unused `output` variable in `test_practice_success_at_adept`) is
  unrelated to my edits and was present before this session.
- Pre-existing flake at `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs` unchanged.

## Commits

| SHA | |
|-----|---|
| `b5b228f6` | `docs: STRONG stop-and-reindex rule when gitnexus index is reported stale` |
| `3fff0065` | `fix(parity): ARITH-010 — do_practice no longer floors skill increment to 1` |
| `646dc8dd` | `docs(parity): reclassify ARITH-013 to N/A (dead-code post-gate)` |
| `03b7a5e2` | `fix(parity): ARITH-016 — charm_person passes raw level/4 to number_fuzzy` |
| `928aa517` | `fix(parity): ARITH-015 — berserk passes raw level/8 to number_fuzzy` |

## Outstanding / next agent

- **ARITHMETIC_BOUNDARY effective candidate count**: 56 ✅ MATCH /
  **42 ❌ MISSING** / 115 N/A (was 45 ❌; -1 N/A reclass, -2 FIXED
  this session; +1 more N/A confirmation pending in row 66).
- **Next gaps to close** (priority order):
  - ARITH-009 (`mud/groups/xp.py:257`) — negative XP swallow.
  - ARITH-105 (`mud/models/character.py:478`) — `get_curr_stat`
    floor of 0 vs ROM's 3. High blast radius.
  - ARITH-101/102/103 (`mud/handler.py:995/1003/1011`) — coin-weight
    inflation for small stacks.
  - ARITH-011/012 — `max_hit` floor in berserk/flee hp%. Suspect
    they may be dead-code post-gate similar to ARITH-013 — needs the
    same reachability check.
- **UB-protection cluster policy** (ARITH-001/002/003/005/006/007/008/011/012/014) still undecided. Likely `assert` + `docs/divergences/` note rather than direct ROM replication.
- **ARITH-209 spot-check** still pending.
- **Pre-existing lint** at `test_do_practice_command.py:255` ready
  to clean up in passing (single-line ruff F841).

## GitNexus

Stop-and-reindex rule honoured throughout the session:
- Reindexed after `b5b228f6` (CLAUDE.md commit + push).
- Reindexed after `3fff0065` (ARITH-010).
- Reindexed after `646dc8dd` (ARITH-013 reclass).
- Reindexed after `03b7a5e2` (ARITH-016).
- Reindex after `928aa517` (ARITH-015) running at handoff time.

FTS DB remains read-only at the MCP-server layer (pre-existing
upstream issue, see CLAUDE.md "Known GitNexus Indexing Gap"). The
node/edge graph itself is current after each reindex — only the
full-text search side is dark.
