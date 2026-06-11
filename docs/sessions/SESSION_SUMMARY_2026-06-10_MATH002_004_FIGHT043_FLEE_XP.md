# Session Summary — 2026-06-10 — MATH-002/003/004 c_div hygiene + FIGHT-043 do_flee XP loss

## Scope

Continuation from v2.13.85 (INV-043 nuke-pets stop-fighting). Active pass: cross-file
invariants. Session picked up three probe candidates from the previous handoff and resolved
all three: INV-015 affect-expiry ordering confirmed already enforced; do_flee / do_recall
stop-fighting ordering confirmed non-divergent; MATH-002/003/004 hygiene items fixed. Then
surfaced FIGHT-043 (the entire ROM XP-penalty block missing from `do_flee`) and closed it.

**Affect expiry → `affect_remove` → `affect_check` ordering probe** — INV-015 already
covers the full `affect_remove` chain with two mutation-verified enforcement tests. The
bitvector re-set logic in `affect_check` is exercised by INV-015's `test_single_affect_removal`
and `test_dual_affect_removal` scenarios. No gap; no new INV row needed.

**`do_flee` / `do_recall` stop-fighting ordering probe** — ROM `src/fight.c:3022-3095`
calls `stop_fighting(ch, TRUE)` before `char_from_room`. `stop_fighting` walks
`character_registry` (not `room.people`), so the fighting-pointer sweeps happen before the
character is moved out of the room. Python `do_flee` and `do_recall` both call
`stop_fighting` before the room move. The ordering is non-observable under the cross-INV
lens (no room-state dependency in the sweep). No gap; no INV row warranted.

**MATH-002/003/004** — `docs/parity/audits/MATH_AND_RNG.md` had three ⚠️ OPEN LOW-severity
hygiene rows: `//` operator usage in parity-sensitive paths where operands are non-negative
by construction. Fixed by mechanical `c_div` substitution at 11 sites across
`mud/combat/engine.py` (weapon-flag dispatch and vampiric heal) and `mud/skills/handlers.py`
(enchant_armor/enchant_weapon fizzle thresholds). No observable behavioral change.

**FIGHT-043** — During the do_flee probe, discovered that Python's `do_flee` was missing
the entire XP-penalty block present at ROM `src/fight.c:3010-3019`. On successful flee, ROM:
emits "You flee from combat!"; then for thieves (`ch_class == 2`) runs a sneak check
(`number_percent() < 3 * (level / 2)`) and emits "You snuck away safely." with no XP
deduction; all others emit "You lost 10 exp." and call `gain_exp(ch, -10)`. Python emitted
the flee message but skipped the entire penalty block. Filed as FIGHT-043 and fixed.

## Outcomes

### MATH-002 — ✅ FIXED (2.13.86)

- **Python**: `mud/combat/engine.py` — `dam // 2` in vampiric weapon-flag heal
- **ROM C**: `src/fight.c` weapon flag VAMPIRIC: heal half of damage
- **Fix**: `dam // 2` → `c_div(dam, 2)` (hygiene; `dam` non-negative by construction)
- **Tests**: no behavioral change; closed row in `docs/parity/audits/MATH_AND_RNG.md`

### MATH-003 — ✅ FIXED (2.13.86)

- **Python**: `mud/combat/engine.py:process_weapon_special_attacks` — `weapon_level // {2,4,5,6}` at 7 sites (vampiric × 1, flaming × 2, frost × 2, shocking × 2)
- **ROM C**: `src/fight.c` weapon flag handlers
- **Fix**: all 7 `weapon_level //` sites → `c_div(weapon_level, N)` (hygiene; `weapon_level = obj.level >= 0`)
- **Tests**: no behavioral change; closed row in `docs/parity/audits/MATH_AND_RNG.md`

### MATH-004 — ✅ FIXED (2.13.86)

- **Python**: `mud/skills/handlers.py` — `fail // {5,3,2}` at 4 sites in
  `enchant_armor` and `enchant_weapon` fizzle branches
- **ROM C**: `src/magic.c` enchant_armor / enchant_weapon fizzle thresholds
- **Fix**: all 4 `fail //` sites → `c_div(fail, N)` (hygiene; `fail` is `percentage ∈ [0,100]`)
- **Tests**: no behavioral change; closed row in `docs/parity/audits/MATH_AND_RNG.md`

### FIGHT-043 `do_flee` missing XP loss block — ✅ FIXED (2.13.87)

- **Python**: `mud/commands/combat.py:do_flee` — XP-penalty block entirely absent
- **ROM C**: `src/fight.c:3010-3019` — `!IS_NPC(ch)` gate, thief sneak check, `gain_exp(ch, -10)`
- **Gap**: on successful flee, a PC always escaped with full XP; thief sneak bonus never ran
- **Fix**: added XP block after `messages.append("You flee from combat!")` — `is_npc` guard,
  `ch_class == 2` thief check, `rng_mm.number_percent() < 3 * c_div(char.level, 2)` sneak
  roll, `gain_exp(char, -10)` deduction (via `from mud.advancement import gain_exp`)
- **Tests**: `tests/integration/test_fight043_flee_xp_loss.py` — **5/5 passing**:
  - `test_non_thief_flee_loses_10_exp` — warrior flees → exp 5000 → 4990, "You lost 10 exp."
  - `test_non_thief_flee_emits_flee_message` — "You flee from combat!" in result
  - `test_thief_sneak_no_xp_loss` — thief sneak success (roll 1 < 15) → exp 5000 unchanged, "You snuck away safely."
  - `test_thief_sneak_fail_loses_xp` — thief sneak fail (roll 99 ≥ 15) → exp 5000 → 4990
  - `test_npc_flee_no_xp_loss` — NPC flee does not touch exp
  - Both mutation-sensitive tests verified RED before fix, GREEN after

Note: `pc.exp` set to 5000 in XP-deduction tests (not 1000) because `gain_exp`'s floor is
`exp_per_level(char)` — for test chars without `pcdata.points`, this defaults to
`BASE_XP_PER_LEVEL = 1000`, so `max(1000, 990) = 1000` is a silent no-op. Setting exp
above the floor ensures the deduction actually lands.

### Affect expiry → affect_remove → affect_check ordering — ✅ CONFIRMED CLEAN

- INV-015 (`AFFECT-EXPIRY-ORDERING`) already covers the full `affect_remove` chain with
  two mutation-verified enforcement tests. No new row warranted.

### do_flee / do_recall stop-fighting ordering — ✅ CONFIRMED NON-DIVERGENT

- Both Python `do_flee` and `do_recall` call `stop_fighting` before `char_from_room`.
  `stop_fighting` walks `character_registry`, not `room.people`, so the ordering is
  non-observable. No gap; no INV row warranted.

## Files Modified

- `mud/combat/engine.py` — MATH-003: 7 `weapon_level //` sites + 1 `dam //` site → `c_div`
- `mud/skills/handlers.py` — MATH-004: 4 `fail //` sites → `c_div`
- `mud/commands/combat.py` — FIGHT-043: added XP-penalty block to `do_flee`; added
  `from mud.advancement import gain_exp` import
- `tests/integration/test_fight043_flee_xp_loss.py` — new file, 5 enforcement tests
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-043 row added (✅ FIXED 2.13.87)
- `docs/parity/audits/MATH_AND_RNG.md` — MATH-002/003/004 rows updated (✅ FIXED 2.13.86);
  summary table: 0 HIGH, 0 LOW open items
- `CHANGELOG.md` — `[2.13.87]` and `[2.13.86]` Fixed entries
- `pyproject.toml` — 2.13.85 → 2.13.86 → 2.13.87

## Test Status

- `pytest tests/integration/test_fight043_flee_xp_loss.py -v` — **5/5 passing**
- Full integration suite: **2892 passed, 3 skipped** (31.7s)

## Next Steps

Cross-file invariants remains the active pass. Next free INV ID: **INV-044**.

Previous three probe candidates are fully resolved. Suggested next candidates:

1. **`stop_fighting` called-from survey** — `stop_fighting` is a high-traffic combat
   primitive. A brief grep of callers not yet covered by an INV row (e.g., spell discharge
   paths, skill-interrupt paths, log-out paths) may surface ordering gaps similar to INV-043.

2. **`do_flee` / `do_recall` position-state coherence after move** — the stop-fighting
   ordering is confirmed clean; the next edge is whether `char.position` is correctly
   reset to STANDING after a successful flee/recall (ROM `src/act_move.c:do_recall`
   sets `ch->position = POS_STANDING` explicitly). A quick probe of the Python
   `do_flee` / `do_recall` position reset would close this area.

3. **`check_killer` call sites** — FIGHT-030 (rescue) closed the `do_rescue` gap.
   Verify no other combat-entry or PK paths are missing `check_killer` calls (e.g.,
   `do_murder`, `do_kill` guards for the "not_same_group NPC" edge).
