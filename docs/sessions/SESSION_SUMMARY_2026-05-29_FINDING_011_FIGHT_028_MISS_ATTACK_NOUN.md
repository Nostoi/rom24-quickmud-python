# Session Summary — 2026-05-29 — FINDING-011 closed (FIGHT-028 combat miss line keeps the attack noun)

## Scope

Continued the differential-harness-driven combat parity work, picking up from the
prior session's handoff: FINDING-010 had been resolved as FIGHT-027 (unarmed-NPC
damage dice), advancing the `combat_melee_rounds` differential's first divergence to
**step 7** — a miss-line rendering gap filed as **FIGHT-028 / FINDING-011** but not
yet closed. This session closed FIGHT-028 on `master`, then verified and self-cleaned
FINDING-011 on the `diff-harness` branch, taking the differential to **zero known
divergences**.

## Outcomes

### `FIGHT-028` — ✅ FIXED (master 2.11.16, `9b2fd868`) — closes FINDING-011

- **Python**: `mud/combat/messages.py:dam_message`
- **ROM C**: `src/fight.c:2157-2213` (`dam_message` template selection)
- **Gap**: `dam_message` had a `if int(percent) <= 0 and not immune:` early-return
  that forced the **no-noun** `TYPE_HIT` template for *any* miss — and for any
  low-damage hit that rounded to percent 0 — regardless of `dt`. So an NPC with a
  resolved attack type (e.g. the drunk #3064, `dt = TYPE_HIT + 13` "beating") that
  *missed* rendered `"The drunk misses you."` where ROM renders `"The drunk's beating
  misses you."` — even though the same mob's *hit* path correctly rendered the noun.
- **Root cause**: ROM `src/fight.c:2157` chooses the message template **purely on
  `dt == TYPE_HIT` vs not**; `dam == 0` only swaps `vs/vp` to "miss"/"misses" via
  `_severity_terms`. The Python early-return conflated the damage value with the
  template branch. **Fix**: deleted the block so the no-noun output is keyed solely on
  `attack is None` (i.e. `dt == TYPE_HIT`); `_severity_terms` already returns the
  "miss"/"misses" verbs for `damage <= 0`, and the existing noun branch handles the
  resolved-`dt` case. One deletion, no new branches.
- **Advisor-flagged breadth**: the guard was `percent <= 0`, not `damage == 0`, so the
  deletion also (correctly) fixes **low-damage hits that round to percent 0** with a
  resolved noun (`c_div(1*100, 200) == 0` → "scratch" tier). This is equally
  ROM-faithful. The change touches every miss-or-tiny-hit with `dt != TYPE_HIT` —
  weapons, NPC `dam_type`, and spell handlers (which pass a string `dt`, always
  resolving a noun).
- **Tests**: `tests/integration/test_fight_028_miss_attack_noun.py` (3 — resolved-noun
  miss renders the noun template; low-damage hit rounding to percent 0 keeps the noun;
  bare `TYPE_HIT` miss stays noun-less as the control). Failing-test-first: all 3
  noun assertions failed for the right reason before the fix; the `TYPE_HIT` control
  passed throughout.
- **Re-baselined 5 stale unit assertions** that asserted the noun-less miss form ROM
  never produces for `dt != TYPE_HIT` (each attacker has a resolved `dt` — a `kick`
  skill noun, or `dam_type=BASH` → attack-table noun "slice", so ROM renders
  `"Your kick/slice misses ..."`). Per AGENTS.md, a test contradicting ROM is the
  test's bug. Each got a ROM-cited comment:
  `test_combat.py::test_kick_command_failure` & `::test_ac_influences_hit_chance`,
  `test_combat_thac0_engine.py::test_thac0_path_hit_and_miss` &
  `::test_weapon_skill_influences_thac0`, `test_skills.py::test_kick_failure`.
- **Impact**: `gitnexus_impact(dam_message, upstream)` = HIGH (35 symbols, central
  combat renderer) but only one direct caller (`apply_damage`); `gitnexus_detect_changes`
  = LOW risk, scope exactly the touched symbols. Full suite confirmed no fallout.

### `FINDING-011` — ✅ RESOLVED (diff-harness `4094aded`) — differential converges end-to-end

- Merged master (FIGHT-028) into the `diff-harness` worktree, then re-ran the
  differential. `combat_melee_rounds` now produces a **clean diff with no xfail**
  (`report is None` → genuine convergence, not toleration).
- Removed `combat_melee_rounds` from `KNOWN_DIVERGENCES` in
  `tests/test_differential_smoke.py` (the dict is now empty — self-cleaning per the
  harness convention) and re-ran with the whitelist removed: **2 passed**
  (`combat_melee_rounds` + `movement_get_drop`), proving the convergence is real.
- Marked FINDING-011 ✅ RESOLVED in `tools/diff_harness/FINDINGS.md`.
- **Zero known divergences remain** across the differential harness.

## Files Modified

### master (`9b2fd868`)
- `mud/combat/messages.py` — deleted the `percent <= 0` early-return in `dam_message`
- `tests/integration/test_fight_028_miss_attack_noun.py` — new regression (3 tests)
- `tests/test_combat.py`, `tests/test_combat_thac0_engine.py`, `tests/test_skills.py` —
  re-baselined 5 stale noun-less miss assertions with ROM citations
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-028 row 🔴 OPEN → ✅ FIXED (2.11.16)
- `CHANGELOG.md` — `[2.11.16]` Fixed + Changed entries
- `pyproject.toml` — 2.11.15 → 2.11.16

### diff-harness (`4094aded`)
- `tests/test_differential_smoke.py` — `KNOWN_DIVERGENCES` emptied (FINDING-011 removed)
- `tools/diff_harness/FINDINGS.md` — FINDING-011 ✅ RESOLVED

## Test Status

- `pytest -n0 tests/integration/test_fight_028_miss_attack_noun.py` — 3/3 passing.
- The 5 re-baselined assertions pass serially (7/7 with the new file).
- Full suite (master `9b2fd868`): **4950 passed, 4 skipped** (~143s) — clean.
- Differential smoke (diff-harness, FINDING-011 de-whitelisted): **2 passed**
  (`combat_melee_rounds` + `movement_get_drop`).
- `ruff check` on touched files clean. GitNexus main-repo reindex completed (41,869 nodes).

## Outstanding

- **`test_combat_death.py` xdist ordering flake** (pre-existing; surfaced while
  validating FIGHT-028). These unit death tests in `tests/` lack the integration
  autouse `seed_mm(12345)`, so their RNG-dependent outcomes flake under parallel
  worker scheduling — the *failing set varies* run-to-run (`test_raw_kill_awards_group_xp_and_creates_corpse`
  + `test_player_death_dismisses_pet` one run, `test_autosacrifice_extracts_corpse`
  another) and **all pass in isolation** (`pytest -n0`). A string-only change cannot
  cause a non-deterministic failure set, so this is not FIGHT-028. The file is already
  in CLAUDE.md's GitNexus known-failing list. Root fix: seed RNG in these death tests
  (or move them under the integration autouse seed). Not filed as a parity gap — it's
  a test-isolation issue, not a ROM divergence.
- **`ACT-CAP-001`** (in `FIGHT_C_AUDIT.md`) — non-combat act() capitalization at
  `broadcast_room`/`act_format` (wider re-baseline surface).
- **`SHOP-PET-001`** — bought-pet `dam_type` bypasses `from_prototype` attack-index
  resolution (drunk-only differential can't exercise it).
- NPC `do_X` per-command RNG-draw fidelity for flagged mobs.

## Next Steps

The differential harness now converges on all current scenarios with zero known
divergences — the per-scenario divergence chase that drove FINDING-007 through -011
is exhausted for the existing scenarios. Next session should either (a) **add a new
differential scenario** exercising an un-probed path (spell combat, multi-mob rooms,
group fights) to surface the next divergence, or (b) pick up one of the Outstanding
follow-ups (`ACT-CAP-001` is the most self-contained). Per AGENTS.md, with the
per-file audit tracker exhausted, cross-file invariants / new-scenario probing is the
active mode.
