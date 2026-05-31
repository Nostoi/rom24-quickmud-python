# Session Summary — 2026-05-28 — SPAWN-001 mob-spawn RNG draw-order (FINDING-007)

## Scope

Continuation of the combat differential-harness thread
(`SESSION_SUMMARY_2026-05-28_DB2_007_MOB_DICE_AND_COMBAT_HARNESS_V1_WIP.md`). The
prior session left combat v1 WIP **gated on FINDING-007**: the `combat_melee_rounds`
scenario xfailed because the drunk #3064 spawned at HP **33** in Python vs **31** in
ROM C from the same seed (777) — a mob-spawn RNG draw-order divergence. This session
closed FINDING-007 on `master` via the gap-closer flow, merged to `diff-harness`, and
re-ran the differential. The spawn HP now matches; the gate advanced one step deeper
to a new combat-output divergence, filed as FINDING-008.

## Outcomes

### `SPAWN-001` / FINDING-007 — ✅ FIXED (master, 2.11.3, commit `47f8fd75`)

- **Python**: `mud/spawning/templates.py::MobInstance.from_prototype`
- **ROM C**: `src/db.c:2047-2113` (`create_mobile`)
- **Gap**: `from_prototype` drew the spawn RNG stream in nearly the reverse of ROM's
  order — random sex first, then random damtype, HP/mana, with gold **last**. ROM
  `create_mobile` draws **gold/wealth → HP dice → mana dice → random damtype
  (`dam_type == 0`) → random sex (`sex == EITHER`)**. Because ROM's gold draw
  precedes the `2d6` HP roll and Python's did not, every seed-dependent mob landed at
  a different RNG stream position than ROM (drunk #3064: HP 31 vs 33). Latent for the
  project's life because the unit suite uses synthetic mobs with explicit HP.
- **Fix**: reordered the four RNG-consuming draws in `from_prototype` to mirror ROM
  exactly. The random-sex resolution was moved from its early parse site to the bottom
  of the method (drawn last). Uses the real `rng_mm` primitives, which short-circuit
  `number_range` (when `to <= from`) and `dice` (when `size <= 1`) **without**
  consuming the stream — so the draw *count* stays data-dependent and correct (the
  drunk's 2nd gold draw and its `1d1` mana are no-ops).
- **Significance**: the `create_mobile` row in `DB_C_AUDIT.md` was certified on
  stat-**copy** parity; the RNG **ordering** contract was never checked. Audit
  corrected (new `SPAWN-001` row).
- **Tests**: `tests/integration/test_spawn_001_rng_draw_order.py` (1) — replays ROM's
  draw order with the real primitives + a post-spawn stream-position **sentinel** that
  locks total draw count and order end-to-end (incl. the damtype-before-sex tail that
  no field assertion can reach). Failed pre-fix (`max_hit 50` vs ROM-order `51`),
  passes post-fix. Full suite **4926 passed, 4 skipped, 0 failed** — zero seeded-test
  fallout.

### Loop closure + FINDING-008 filed (diff-harness, commit `d8052e27`)

Merged `master` (SPAWN-001) into `diff-harness` and re-ran `test_differential_smoke`.
`diff_traces` reports only the **first** divergence, and it advanced from the
`__mload` spawn step (HP 33 vs 31) to **step 4 `kill drunk`** — proving steps 1–3
(including the spawn HP snapshot) now match the C golden byte-for-byte. **FINDING-007
is resolved.**

The step-4 divergence is new and distinct, filed as **FINDING-008** (combat
first-attack outcome / message rendering):

```
step 4 (command='kill drunk') · output ·
  C  = ['You miss the drunk.']
  py = ['{2You scratch the drunk.{x', '{2You scratch the drunk.{x']
```

Three sub-issues, each needing triage to classify before its own gap-closer:
1. **hit/miss + damage-tier outcome** differs (C miss, py scratch) — likely a real
   combat RNG draw-order / THAC0 / damage-tier divergence in `multi_hit`/`one_hit`;
2. **color codes** not normalized (`{2…{x`) — likely harness compare-fairness;
3. **double-delivery** (py emits the line twice) — triage against the SINGLE-DELIVERY
   invariant.

`KNOWN_DIVERGENCES["combat_melee_rounds"]` reason updated from FINDING-007 to
FINDING-008; the scenario stays gated (xfail) until FINDING-008 is triaged.

## Files Modified

- **master** (commit `47f8fd75`): `mud/spawning/templates.py` (reorder draws);
  `tests/integration/test_spawn_001_rng_draw_order.py` (new);
  `docs/parity/DB_C_AUDIT.md` (new `SPAWN-001` ✅ FIXED row); `CHANGELOG.md` (2.11.3);
  `pyproject.toml` (2.11.2 → 2.11.3).
- **diff-harness** (commit `d8052e27`, atop merge `e50c85e2`):
  `tools/diff_harness/FINDINGS.md` (FINDING-007 → RESOLVED, FINDING-008 filed);
  `tests/test_differential_smoke.py` (KNOWN_DIVERGENCES reason → FINDING-008).

## Test Status

- `tests/integration/test_spawn_001_rng_draw_order.py` — 1/1 passing.
- Full suite (master, post-fix): **4926 passed, 4 skipped, 0 failed**.
- `tests/test_differential_smoke.py` (diff-harness): `movement_get_drop` PASS,
  `combat_melee_rounds` XFAIL (FINDING-008).

## Outstanding

- **`master` is 1 commit ahead of `origin/master` (UNPUSHED)** at 2.11.3 (`47f8fd75`).
  The canonical "current" pointer lives on **`diff-harness`** (this summary); master's
  own `SESSION_STATUS.md` predates DB2-007 and is stale — do not treat it as current.
- **Pre-existing lint landmine for the master push:** `ruff check .` reports **10
  pre-existing errors** in `mud/spawning/templates.py` (`apply_spell_effect`
  function-local import sorting, I001) — present on master before this session, NOT
  introduced by SPAWN-001 (verified via stash). This session ran `ruff check` on the
  two changed files only, not repo-wide. Whoever pushes master must settle these (they
  are `--fix`-able) or confirm CI tolerates them.
- **FINDING-008** — combat first-attack outcome/message divergence at `kill drunk`.
  Three sub-issues to triage (combat hit/miss = likely real parity; color-code
  normalization; double-delivery vs SINGLE-DELIVERY invariant). Gates combat v1.
- **diff-harness worktree GitNexus index is stale** (`9be478a`). The main-repo index
  was reindexed this session (`npx gitnexus analyze --skip-agents-md`, exit 0); the
  worktree is a separate indexed repo — reindex it before relying on its
  `gitnexus_impact` next session.

## Next Steps

1. **Push `master`** (2.11.3, SPAWN-001) once the pre-existing ruff errors are settled.
2. **Triage FINDING-008** — start with sub-issue 1 (combat hit/miss): read ROM
   `src/fight.c` `multi_hit`/`one_hit` attack-roll order vs `mud/combat/engine.py`,
   write a failing test, fix on master as the next gap-closer. Then resolve the
   color-code normalization and double-delivery (harness/invariant) so the
   `combat_melee_rounds` xfail clears and combat v1 can land.
3. **Merge `diff-harness` → master** once combat v1 is green (per the multi-session
   harness plan).
