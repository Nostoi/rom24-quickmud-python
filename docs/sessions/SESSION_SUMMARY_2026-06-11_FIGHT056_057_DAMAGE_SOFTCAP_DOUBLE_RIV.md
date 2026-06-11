# Session Summary — 2026-06-11 — FIGHT-056/057 damage soft-cap + double-RIV

## Scope

Continuation from v2.14.1 (FIGHT-055 closed). Active pass: cross-file invariants.
Session picked up from SESSION_STATUS.md which listed three probes under INV-044:
`group_gain` NPC-level-contribution floor, `apply_damage` death-message broadcast, and
`damage` zero-dam WEAPON_NONE path. All three probes were clean. During investigation,
two structural gaps in the `damage()` pipeline were discovered and confirmed empirically:
(1) the ROM soft-cap at `src/fight.c:717-720` was entirely absent from Python's `apply_damage`;
(2) RIV (resistance/immunity/vulnerability) was applied twice for weapon attacks — once in
`attack_round` and once again inside `apply_damage`. Both filed as FIGHT-056 and FIGHT-057
respectively and closed in the same session.

## Outcomes

### Probe: `group_gain` NPC-level-contribution floor — ✅ NO GAP

- **ROM C**: `src/fight.c:1751` — `total_levels += gch->level / 2` for NPCs
- **Python**: `mud/groups/xp.py:group_gain` — `total_levels += level // 2` for NPC members
- **Finding**: `level // 2` is bit-for-bit identical to C `gch->level / 2` for non-negative
  levels. The `total_levels <= 0` fallback (Python line 115-116) triggers under different
  conditions than ROM's `members == 0` fallback, but is functionally equivalent — both floor
  the divisor to ≥ 1.

### Probe: `apply_damage` death-message broadcast — ✅ NO GAP

- **ROM C**: `src/fight.c:859-861` — `act("{R$n is DEAD!!{x", victim, …, TO_ROOM)` then
  `send_to_char("{RYou have been KILLED!!{x\n\r\n\r", victim)`
- **Python**: `mud/combat/engine.py:_position_change_message` (line ~899) — broadcasts
  `"{R{name} is DEAD!!{x"` to room, returns `"{RYou have been KILLED!!{x\n"` to victim
- **Finding**: Correct TO_ROOM/TO_CHAR ordering, correct color codes `{R...{x`, correct
  "is DEAD!!" wording. No divergence.

### Probe: `damage` zero-dam WEAPON_NONE path — ✅ NO GAP

- **ROM C**: `src/fight.c:821-822` — `if (dam == 0) return FALSE;` (returns before
  `update_pos` when dam is zero)
- **Python**: `mud/combat/engine.py:apply_damage` line 730 — `if damage <= 0: … return`
  (early returns before `update_pos` call at line 746)
- **Finding**: Python correctly early-returns before `update_pos` for zero-damage. No divergence.

### FIGHT-056 `apply_damage` missing damage soft-cap — ✅ FIXED (2.14.2)

- **Python**: `mud/combat/engine.py:apply_damage`
- **ROM C**: `src/fight.c:717-720`
- **Gap**: ROM's `damage()` applies two sequential soft-caps before any other modifier:
  `if (dam > 35) dam = (dam-35)/2+35; if (dam > 80) dam = (dam-80)/2+80;`
  Python's `apply_damage` had neither cap — 200 raw damage landed as 200 instead of ROM's
  98; 50 raw landed as 50 instead of 42. Affects ALL callers (weapons, spells, kicks,
  mob programs).
- **Fix**: Added cap block at the top of `apply_damage`, immediately after the `DEAD`
  position guard and before `is_safe`. Used `c_div` for ROM-faithful integer truncation:
  `if damage > 35: damage = c_div(damage - 35, 2) + 35; if damage > 80: damage = c_div(damage - 80, 2) + 80`
- **Impact analysis**: `apply_damage` — CRITICAL risk (41 transitive impacts across 6 modules);
  change is a pure addition (no removal), affecting all callers uniformly.
- **Tests**: `tests/integration/test_fight056_damage_soft_cap.py` — **4/4 passing**
  - `test_fight056_damage_below_35_unchanged` — dam=35 passes through unchanged
  - `test_fight056_first_cap_applied_above_35` — dam=50 → 42 (first cap only)
  - `test_fight056_both_caps_applied_above_80` — dam=200 → 117 → 98 (both caps)
  - `test_fight056_boundary_exactly_80_no_second_cap` — dam=125 → 80 (not > 80, no second cap)
  All 4 verified red before fix, green after.

### FIGHT-057 double-RIV in `attack_round` — ✅ FIXED (2.14.3)

- **Python**: `mud/combat/engine.py:attack_round` (lines 615-623 removed)
- **ROM C**: `src/fight.c:804-816`
- **Gap**: ROM's `damage()` calls `check_immune` exactly once. Python split the pipeline:
  `attack_round` pre-applied RIV (lines 615-623: IS_IMMUNE/IS_RESISTANT/IS_VULNERABLE),
  then passed the scaled damage to `apply_damage` which applied RIV again (lines 707-723).
  An IS_RESISTANT victim took `(1-1/3)^2 ≈ 44%` of raw damage instead of ROM's `1-1/3 ≈ 67%`.
  Confirmed empirically: 50 raw → 23 actual vs expected 33 (ratio 0.460 vs expected 0.667).
  IS_VULNERABLE was similarly double-applied: `(1+1/2)^2 = 2.25×` instead of `1.5×`.
- **Fix**: Removed the RIV block from `attack_round` (the pre-application at former lines
  615-623) and dropped `immune=immune` from the `apply_damage` call — `apply_damage` already
  handles RIV correctly via the single check at lines 707-723.
- **Impact analysis**: `attack_round` — CRITICAL risk (13 transitive impacts); change removes
  a duplicate transformation, not a new one.
- **Tests**: `tests/integration/test_fight057_double_riv.py` — **2/2 passing**
  - `test_fight057_resistant_damage_reduced_once_not_twice` — BASH-resistant victim gets
    `dam - dam/3` not `(dam - dam/3) - (dam - dam/3)/3`
  - `test_fight057_vulnerable_damage_increased_once_not_twice` — BASH-vulnerable victim gets
    `dam + dam/2` not `(dam + dam/2) + (dam + dam/2)/2`
  Both verified red before fix, green after.

## Files Modified

- `mud/combat/engine.py` — FIGHT-056: added soft-cap block at top of `apply_damage`; FIGHT-057:
  removed duplicate RIV block from `attack_round`, dropped `immune=immune` kwarg
- `tests/integration/test_fight056_damage_soft_cap.py` — new file, 4 tests
- `tests/integration/test_fight057_double_riv.py` — new file, 2 tests
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-056 and FIGHT-057 filed and flipped ✅ FIXED
- `CHANGELOG.md` — `[2.14.2]` Fixed entry for FIGHT-056; `[2.14.3]` Fixed entry for FIGHT-057
- `pyproject.toml` — 2.14.1 → 2.14.2 (FIGHT-056) → 2.14.3 (FIGHT-057)

## Test Status

- `pytest tests/integration/test_fight056_damage_soft_cap.py` — **4/4 passing**
- `pytest tests/integration/test_fight057_double_riv.py` — **2/2 passing**
- Integration suite: **2936/2939 passing, 3 skipped** (run 2026-06-11, post-FIGHT-057 commit)
- Full suite: in progress at session end (last known full run 5597/5601 from prior session)

## Outstanding / Noted-but-not-closed

- **FIGHT-058 (candidate): Spells bypass `apply_damage_reduction`** — Discovered while
  investigating the double-RIV gap. Spell handlers (fireball, flamestrike, earthquake,
  energy_drain, etc.) in `mud/skills/handlers.py` call `apply_damage` directly, bypassing
  `apply_damage_reduction` (drunk/sanctuary/protect_evil/protect_good). In ROM, ALL damage
  through `damage()` gets these reductions. The correct fix would move `apply_damage_reduction`
  INTO `apply_damage` (so all callers benefit), which is the ROM-faithful architecture. This
  is a HIGH-severity gap but was scoped out of this session to preserve the one-gap-per-commit
  discipline. The gap is undocumented — file as FIGHT-058 in the next session.

## Next Steps

Cross-file invariants pass continues. Next free INV ID: **INV-044** (still free).

1. **FIGHT-058 (pending, file and close)** — Move `apply_damage_reduction` (drunk/sanctuary/
   protect_evil/protect_good) into `apply_damage` so spell callers get the same reductions
   as weapon attacks. ROM's `damage()` applies these at lines 775-785 (AFTER is_safe and
   set_fighting setup, BEFORE parry/dodge/shield and RIV). Current Python architecture
   applies them only from `attack_round`, leaving all direct `apply_damage` callers (spells,
   kicks, mob-program damage) unprotected. This is a `damage()` pipeline completion fix.

2. **Cross-file invariants** — After FIGHT-058 closes, resume INV-044 probes on any remaining
   candidate areas not yet probed (mob script triggers, group/follower chain, position
   transitions under multi-attack).
