# Session Summary — 2026-05-29 — FINDING-010 closed (FIGHT-027 unarmed-NPC damage dice)

## Scope

Continued the differential-harness-driven combat parity work. Picked up from the
prior session's handoff: FINDING-009 (the combat-tick `__tick`/`violence_update`
round) was fully resolved and the `combat_melee_rounds` differential's first
divergence had advanced to **step 6** (round-2 damage severity), filed as
FINDING-010 with the root cause unknown and a regression from FIGHT-021/022/023
not yet ruled out. This session ran the discriminating probe, root-caused
FINDING-010, closed it as **FIGHT-027** on `master`, and re-ran the differential
end-to-end.

## Outcomes

### `FIGHT-027` — ✅ FIXED (master 2.11.15, `bbdebbc1`) — closes FINDING-010

- **Python**: `mud/combat/engine.py:calculate_weapon_damage`
- **ROM C**: `src/fight.c:522-560` (`one_hit` NPC damage branch)
- **Gap**: `calculate_weapon_damage` had **no `IS_NPC` branch** — an unarmed mob
  fell through to the PC-unarmed formula `number_range(1 + 4*skill/100,
  2*level/3*skill/100)`. For the drunk #3064 (level 2, damage dice 1d6,
  skill_total ≈ 50) that collapsed to a degenerate `number_range(3, 0)` → ROM
  returns `from` = constant **3**, consuming **zero** `number_mm` draws. So the
  Python drunk dealt a constant 3 every hit (round 1 matched only because C
  happened to roll 3), where ROM rolls `dice(1, 6)` (range 1–6, **one** draw). The
  missing draw also desynced the shared combat RNG stream from round 2 on.
- **Fix**: unarmed NPC (`is_npc and wield is None`) now rolls
  `rng_mm.dice(damage[DICE_NUMBER], damage[DICE_TYPE])` from the `MobInstance.damage`
  tuple (the `[2]` bonus is applied later via damroll). ROM `convert_mobile`
  (`src/db.c`) upgrades every mob to `new_format` at load, so the dice path is the
  only live one — the `!new_format` `number_range(level/2, level*3/2)` sub-branch is
  dead code, and the Python proto `new_format` flag is unreliable (`False` even on
  the dice-carrying drunk), so the fix keys on the damage tuple, not the flag.
- **Probe**: instrumented the Python replay's per-step RNG draws + hp vs the C
  golden. Decisive evidence: C drunk damage varied **3 / 1 / miss / 5** across
  rounds while Python was a **constant 3**; the round-4 C hit of **5** is
  unreachable by `number_range(level/2, level*3/2)`=1–3, proving the new-format
  dice path. Every hitting round showed `number_range(3, 0)=3` (the degenerate
  PC formula).
- **Tests**: `tests/integration/test_fight_027_npc_unarmed_damage_dice.py` (2 —
  damage spans the dice range; consumes exactly one `number_mm` draw). Full suite
  **4947 passed, 4 skipped**; combat + integration suites green (2428 passed) with
  no blast-radius fallout despite the game-wide unarmed-mob damage change.
- **Verification**: the `combat_melee_rounds` differential now converges on **all
  of steps 1–6** (hp + severity verbs match end-to-end); step 5 stays matched (the
  added draw realigned the stream, as predicted).
- **Blast-radius scan**: `dice(n, 0)` / `dice(0, size)` return 0 (clamped to 1), so a
  mob with a 0-component damage dice would have been silently downgraded to flat-1.
  Scanned all **986 mob protos** through the spawner's `_parse_dice` — **zero** resolve
  to a 0 in `damage[0]`/`damage[1]`, so the dice path is safe game-wide (the QuickMUD
  loader populates valid dice for every mob, even those with `new_format=False`). No
  loader gap to file.

### `FIGHT-028` / FINDING-011 — 🔴 FILED (not closed) — combat miss line drops the attack noun

- Surfaced the moment FIGHT-027 advanced convergence past step 6. The differential's
  first divergence is now **step 7** (the drunk *misses*):
  ```
  C  = ["The drunk's beating misses you.", 'You scratch the drunk.']
  py = ["The drunk misses you.",            'You scratch the drunk.']
  ```
- **ROM**: `dam_message` (`src/fight.c:2171-2211`) for `dt != TYPE_HIT` renders
  `"{4$n's %s %s you%c{x"` with `attack = attack_table[dt - TYPE_HIT].noun` and
  `vp = "misses"` (for `dam == 0`). Only the bare `dt == TYPE_HIT` case renders the
  noun-less `"$n %s you"`. The drunk's `dt = TYPE_HIT + 13` ("beating"), so ROM uses
  the noun template — and Python's *hit* path already does too ("The drunk's beating
  hits you."). The **miss path** specifically routes through the noun-less template.
- Distinct root cause from FIGHT-027 (dam_message rendering, not damage calc). Filed
  as `FIGHT-028` (🔴 OPEN) in `docs/parity/FIGHT_C_AUDIT.md` and `FINDING-011` on the
  diff-harness branch. `combat_melee_rounds` stays xfail under FINDING-011.

## Files Modified

- `mud/combat/engine.py` — FIGHT-027 unarmed-NPC dice branch in `calculate_weapon_damage`
- `tests/integration/test_fight_027_npc_unarmed_damage_dice.py` — new regression (2 tests)
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-027 row ✅ FIXED; FIGHT-028 row 🔴 OPEN (FINDING-011)
- `CHANGELOG.md` — `[2.11.15]` Fixed entry
- `pyproject.toml` — 2.11.14 → 2.11.15
- (diff-harness branch `843e519d`) `tools/diff_harness/FINDINGS.md` — FINDING-010 ✅ RESOLVED, FINDING-011 filed; `tests/test_differential_smoke.py` — `KNOWN_DIVERGENCES` updated to FINDING-011

## Test Status

- `pytest tests/integration/test_fight_027_npc_unarmed_damage_dice.py` — 2/2 passing.
- Combat + integration suites (master): 2428 passed, 3 skipped.
- Full suite (master): **4947 passed, 4 skipped** (~102s).
- Differential smoke (diff-harness worktree, post-merge): `movement_get_drop` PASS;
  `combat_melee_rounds` xfail under FINDING-011 (steps 1–6 converge).
- `ruff check` on touched files clean.

## Next Steps

- **FINDING-011 / FIGHT-028** (combat miss line drops the attack noun): trace the
  Python miss path (`apply_damage` with `dam == 0` → `mud/combat/messages.py:dam_message`)
  and route it through the attack-noun template keyed on `dt` (matching ROM
  `src/fight.c:2171-2211` and Python's own hit path). One gap-closer; re-run the
  differential — convergence should advance past step 7.
- **Outstanding follow-ups** (in `docs/parity/FIGHT_C_AUDIT.md`): `ACT-CAP-001`
  (non-combat act() capitalization at `broadcast_room`/`act_format`), `SHOP-PET-001`
  (pet `dam_type` bypasses `from_prototype` resolution), and NPC `do_X` per-command
  RNG-draw fidelity for flagged mobs.
