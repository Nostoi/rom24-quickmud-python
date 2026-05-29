# Session Status — 2026-05-29 — FINDING-010 closed (FIGHT-027 unarmed-NPC damage dice)

## Current State

- **Active mode**: differential-harness-driven combat parity verification. The
  `combat_melee_rounds` scenario now **converges on steps 1–6** on both engines;
  the first divergence has advanced to **step 7** (FINDING-011 / FIGHT-028).
- **Last completed** (this session):
  - **`FIGHT-027`** ✅ (master 2.11.15, `bbdebbc1`) — unarmed-NPC damage now rolls
    the mob damage dice `dice(damage[DICE_NUMBER], damage[DICE_TYPE])` instead of
    falling through to the PC-unarmed `number_range` (which collapsed to a
    degenerate constant 3 for the drunk #3064 and dropped an RNG draw). **Closes
    FINDING-010.**
  - **`FIGHT-028` / FINDING-011** 🔴 FILED (not closed) — combat miss line drops the
    attack noun: ROM `"The drunk's beating misses you."` vs py `"The drunk misses
    you."` (`dam_message` miss path, `src/fight.c:2171-2211`). Surfaced at step 7 the
    moment FIGHT-027 advanced convergence.
  - Differential update committed on `diff-harness` (`843e519d`): FINDING-010
    resolved, FINDING-011 filed, `KNOWN_DIVERGENCES` repointed.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-29_FINDING_010_FIGHT_027_NPC_DAMAGE_DICE.md](SESSION_SUMMARY_2026-05-29_FINDING_010_FIGHT_027_NPC_DAMAGE_DICE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.15 |
| Tests | 4947 passed, 4 skipped (full suite, parallel) |
| ROM C files audited | 43 / 43 (per-file pass complete; differential + cross-file invariants active) |
| Active focus | `fight.c` combat-tick (FINDING-010 closed; FINDING-011 open) |

## Next Intended Task

Pick up **FINDING-011 / FIGHT-028** (combat miss line drops the attack noun). Trace
the Python miss path (`apply_damage` with `dam == 0` → `mud/combat/messages.py:dam_message`)
and route the miss line through the attack-noun template keyed on `dt`, matching ROM
`dam_message` (`src/fight.c:2171-2211`, `"$n's %s misses you"` for `dt != TYPE_HIT`)
and Python's own *hit* path (which already renders the noun). One gap-closer; re-run
`pytest tests/test_differential_smoke.py -k combat_melee` (diff-harness branch) to
confirm convergence advances past step 7.

Outstanding follow-ups (in `docs/parity/FIGHT_C_AUDIT.md`): `ACT-CAP-001` (non-combat
act() capitalization at `broadcast_room`/`act_format`), `SHOP-PET-001` (pet `dam_type`
bypasses `from_prototype` resolution), and NPC `do_X` per-command RNG-draw fidelity
for flagged mobs.
