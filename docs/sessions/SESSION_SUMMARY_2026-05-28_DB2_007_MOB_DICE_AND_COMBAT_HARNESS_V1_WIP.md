# Session Summary — 2026-05-28 — DB2-007 mob-dice fix + combat differential harness v1 (WIP)

## Scope

Picked up from `SESSION_SUMMARY_2026-05-28_HARNESS_SOUNDNESS_AND_MOVE_LOOK_FIXES.md`
(harness made sound; MOVE-003/LOOK-004 landed). This session: closed the last
harness-soundness item (FINDING-005), then started the **combat/RNG differential
scenario** (brainstorm → spec → plan → subagent-driven execution). Building it
surfaced a **game-wide mob-stat data bug (DB2-007)** which became the session's
headline fix, plus a second spawn-RNG-order bug (FINDING-007) that gates combat v1.

The combat harness paid off exactly as intended: before v1 was even finished, the
act of building it found two real Python parity bugs that the existing 4900-test
suite never caught (it uses synthetic mobs, not JSON-loaded ones).

## Outcomes

### FINDING-005 — harness input-source asymmetry — ✅ RESOLVED (2.11.1)
- C reads the repaired `.are` overlay, Python reads `data/areas/*.json`. Probe proved
  identical vnum-set coverage → structurally benign; locked with
  `tests/test_diff_harness_data_parity.py` (reconstructs the repaired `.are` in-Python,
  byte-identical to the Makefile overlay awk). Commit `7f8515ba`.
- ⚠️ Its guard checks vnum *coverage*, not field *values* — FINDING-006 later showed the
  values diverged. The guard should be extended to compare mob dice (tracked in FINDINGS).

### DB2-007 / FINDING-006 — mob HP/mana/damage dice mislabeled game-wide — ✅ FIXED (master 2.11.2)
- **Root cause:** `mud/loaders/mob_loader.py:load_mobiles` read a phantom scalar `ac`
  token at stat-line index [2]. ROM new-format is `level hitroll <hp> <mana> <dam> damtype`
  with AC on the *next* line (`src/db2.c:273-276`) — no scalar AC there. The phantom token
  shifted every dice field by one and **dropped the real HP dice**. Every JSON-loaded mob
  spawned with wrong HP/mana/damage (Hassan #3001: 100 HP vs ROM 1000; drunk #3064: 100 vs `2d6+22`≈31).
- **Fix:** read dice from [2]/[3]/[4]/[5]; vestigial OLC-only `MobIndex.ac` defaults to `"1d1+0"`.
- **Data:** all 52 area JSONs regenerated (45 changed) via `convert_are_to_json.py`.
- **Tests:** `tests/test_mob_dice_parity.py` (TDD red→green); full suite **4925 passed / 0 failed** after regen (zero fallout — the bug was fully latent).
- **Tracker:** `docs/parity/DB2_C_AUDIT.md` DB2-007 (Phase 2 had marked this line ✅ — corrected; a textbook per-file-audit miss).
- **Commit:** master `1857b5f8` (FF-pushed); merged into `diff-harness`.

### Combat differential scenario v1 — 🔄 WIP (gated on FINDING-007)
- **Task 1 (done):** shim meta-commands `__seed` / `__mload` / `__tick` in `src/diff_shim/diffmain.c` (commit `1916ddc`). Verified `violence_update` does not gate `multi_hit` on `wait` (`src/fight.c:79`).
- **Task 2 (done):** `CharSnap` extended with `eff_hitroll`/`eff_damroll`/`eff_ac`; harness PC reconciled to the C shim's `make_test_char` (perm_stat `[13,16,13,13,13]`, mage, no gear). Both engines: hitroll 0, damroll 0, AC [100×4]. Commit `53c1b527`.
- **Task 3 + scoping fix (done, WIP commit `fc7880e8`):** `combat_melee_rounds.json` (PC vs drunk #3064 in mob-free room 3008, 4 ticks); replay loop dispatches the meta-commands (`seed_mm` / `spawn_mob`+`add_character` / `violence_tick(do_combat=True)`). Scoped the shim's `find_char_by_key` to the **watched rooms** so a keyword resolves to the `__mload`'d instance, not a boot-spawned one elsewhere (global-first-match diverged from Python's explicit instance).
- **Captured the C golden; the differential runs** and isolated the one remaining divergence to FINDING-007.

### FINDING-007 — mob spawn RNG draw-order diverges — 🔴 OPEN (next task)
- ROM `create_mobile` (`src/db.c:2047-2091`) draws **gold → HP → mana → (random damtype if 0)**; Python `from_prototype` (`mud/spawning/templates.py:364-394`) draws **(random damtype) → HP → mana → gold**. Gold is drawn last in Python but first in ROM → drunk #3064 spawns at HP **31** (C) vs **33** (Python) from the same seed. Affects every seed-dependent mob spawn.
- Confirmed `seed_mm(n)` ≡ ROM `init_mm()` at `current_time=n` (Python `_init_state` matches `src/db.c:3573` exactly), so the cause is purely draw-order, not seeding.
- **Fix shape:** reorder `from_prototype`'s draws to match `create_mobile` (gold first, then HP, then mana, then dam_type==0 roll last) — a master gap-closer; possible seeded-test fallout. Gated as `KNOWN_DIVERGENCES["combat_melee_rounds"]` (xfail) until it lands.

## Files Modified

- **master (2.11.2, `1857b5f8`):** `mud/loaders/mob_loader.py`, `data/areas/*.json` (45), `tests/test_mob_dice_parity.py`, `docs/parity/DB2_C_AUDIT.md`, `CHANGELOG.md`, `pyproject.toml`.
- **diff-harness (`fc7880e8`):** `src/diff_shim/diffmain.c` (meta-commands + scoped lookup + eff-stat snapshot emit), `tools/diff_harness/{schema,compare,pysnap}.py`, `tools/diff_harness/scenarios/combat_melee_rounds.json`, `tests/test_differential_smoke.py`, `tests/data/golden/diff/*.golden.json`, `tools/diff_harness/FINDINGS.md` (FINDING-005/006/007).
- **Design/plan:** `docs/superpowers/specs/2026-05-28-combat-rng-differential-scenario-design.md`, `docs/superpowers/plans/2026-05-28-combat-rng-differential-scenario-v1.md`.

## Test Status

- `tests/test_differential_smoke.py`: `movement_get_drop` PASS, `combat_melee_rounds` XFAIL (FINDING-007).
- `tests/test_mob_dice_parity.py`, `tests/test_diff_harness_data_parity.py`: PASS.
- Full suite (post-DB2-007, on master): **4925 passed, 4 skipped, 0 failed**.

## Next Steps

1. **Fix FINDING-007 on master** (reorder `from_prototype` RNG draws to match `create_mobile`: gold → HP → mana → dam_type-0 roll). Failing-test-first (assert a seeded `spawn_mob` matches the ROM draw order), then triage any seeded-test fallout. Merge to `diff-harness`, re-run — the `combat_melee_rounds` xfail auto-clears if the diff goes clean.
2. **Finish combat v1 (plan Tasks 4-6):** any further divergences (combat-round to-hit/damage, message wording) → FINDINGS + master gap-closer; then CHANGELOG/version, clear xfail.
3. Extend the harness guard (`test_diff_harness_data_parity.py`) to compare mob dice values, not just vnum coverage (per FINDING-006 note).
4. Latent observation to verify when combat rounds run: mob `[1]` field is ROM `hitroll` but Python `MobIndex` names it `thac0` (`DB2_C_AUDIT.md` line 44) — confirm combat uses it correctly or file a follow-up.
