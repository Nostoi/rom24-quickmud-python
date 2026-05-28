# Session Status — 2026-05-28 — SPAWN-001 (FINDING-007) fixed; combat gate → FINDING-008

## Current State

- **Active mode**: differential-harness-driven parity verification. The combat slice
  (`combat_melee_rounds`) is being built and keeps surfacing real Python parity bugs.
- **Headline this session — `SPAWN-001` / FINDING-007 (shipped to `master`, 2.11.3,
  commit `47f8fd75`):** `MobInstance.from_prototype` drew the spawn RNG stream in
  nearly the reverse of ROM `create_mobile`'s order (sex → damtype → HP/mana → gold),
  so every seed-dependent mob landed at a different RNG position than ROM (drunk #3064
  HP 33 vs 31). Reordered to ROM's **gold → HP → mana → damtype → sex**. Full suite
  4926/0; zero fallout.
- **Combat v1 is still WIP — gate advanced one step deeper.** With the spawn HP now
  aligned, the `combat_melee_rounds` first divergence moved from the `__mload` spawn
  step to **step 4 `kill drunk`** (C `You miss the drunk.` vs py `{2You scratch the
  drunk.{x` ×2). Filed as **FINDING-008** (combat hit/miss outcome, color-code
  normalization, double-delivery). FINDING-007 is **resolved**; FINDING-008 now gates.

## Branch state (READ THIS — work spans two branches)

| Branch | SHA | Contents |
|--------|-----|----------|
| local `master` | `47f8fd75` (v2.11.3) | SPAWN-001 fix + test + audit/changelog. **1 commit AHEAD of `origin/master` — UNPUSHED.** |
| `origin/master` | `1857b5f8` (v2.11.2) | DB2-007 (last pushed state). |
| `diff-harness` (active, local only) | `d8052e27` | Everything on master **plus** the differential harness (movement PASS, combat XFAIL on FINDING-008), FINDINGS, design/plan. **Resume here.** Canonical "current" pointer. |

`diff-harness` is strictly ahead of `master`. **master's own `SESSION_STATUS.md` is
stale** (predates DB2-007) — this file (on `diff-harness`) is canonical.

## Pointer to latest summary

[SESSION_SUMMARY_2026-05-28_SPAWN_001_RNG_DRAW_ORDER.md](SESSION_SUMMARY_2026-05-28_SPAWN_001_RNG_DRAW_ORDER.md)
(predecessor: [SESSION_SUMMARY_2026-05-28_DB2_007_MOB_DICE_AND_COMBAT_HARNESS_V1_WIP.md](SESSION_SUMMARY_2026-05-28_DB2_007_MOB_DICE_AND_COMBAT_HARNESS_V1_WIP.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version (local master) | **2.11.3** (unpushed; `origin/master` at 2.11.2) |
| Full suite | **4926 passed, 4 skipped, 0 failed** (post-SPAWN-001) |
| ROM C files audited | 40 / 43 ✅ (3 N/A). `DB_C_AUDIT.md` `create_mobile` row corrected — `SPAWN-001` RNG draw-order gap closed. |
| Differential harness | `movement_get_drop` PASS; `combat_melee_rounds` XFAIL (FINDING-008). Has caught 8 issues (FINDING-001→008); 001–007 resolved. |
| Open findings | FINDING-008 (combat first-attack outcome/message at `kill`) — gates combat v1. |

## Next Intended Task

1. **Push `master`** (2.11.3, SPAWN-001) — but first settle the **10 pre-existing
   `ruff` errors** in `mud/spawning/templates.py` (`apply_spell_effect` local-import
   I001; NOT introduced this session — verified via stash; `--fix`-able) or confirm CI
   tolerates them. This session ran `ruff check` on changed files only, not repo-wide.
2. **Triage FINDING-008** (gates combat v1), starting with the combat hit/miss
   sub-issue: read ROM `src/fight.c` `multi_hit`/`one_hit` attack-roll draw order vs
   `mud/combat/engine.py`, failing test → fix on master as the next gap-closer. Then
   resolve color-code normalization + double-delivery (harness/invariant) so the
   `combat_melee_rounds` xfail clears.
3. **Merge `diff-harness` → master** once combat v1 is green.
4. **GitNexus** — main-repo index reindexed this session (exit 0). The **diff-harness
   worktree** index is stale (`9be478a`, separate indexed repo) — reindex before
   relying on its `gitnexus_impact`.
5. **INV-025 non-combat narration sweep** — still open from earlier.
