# Session Summary — 2026-06-19 — ARITH-210 + WIZ-053 (position-transition divergence probe)

## Scope

Loop session: "close the next gap via `/rom-gap-closer`, repeat until 5 gaps,
then handoff." Picked up from the ARITH-208 handoff. The documented-gap surface
turned out to be nearly drained, so after closing the one remaining documented
gap (ARITH-210) the session shifted to **probe-then-scope** on the named
divergence-class candidates (position transitions, affect ticks, group/follower
chain). One real divergence surfaced and was closed (WIZ-053). Per advisor
guidance, the session stopped at the **honest number of real gaps (2)** rather
than manufacturing marginal commits to hit an arbitrary target of 5 — 9 probes
across 8 subsystems otherwise confirmed parity.

## Outcomes

### `ARITH-210` — ✅ FIXED

- **Python**: `mud/spawning/templates.py:449` (`from_prototype`)
- **ROM C**: `src/db.c:2077` (`create_mobile` — `mob->hit = mob->max_hit`)
- **Gap**: ARITH-210 — mob spawn `current_hp` floored the `max_hit == 0` case to
  `max(proto.hit[1] + proto.hit[2], 1)` (the dice *size*), where ROM spawns
  `hit == 0` raw.
- **Fix**: `current_hp = max_hit`. Negative `max_hit` already propagated (truthy);
  the `mana = max_mana` sibling was already raw (no half-fix). Reachability probe
  satisfied: a 0-hp spawn flows through `update_pos` exactly as ROM (NPC `hit < 1`
  → `POS_DEAD`), no Python-only crash — `current_hp`/`hit` is a numerator
  everywhere. **Drains the ARITHMETIC_BOUNDARY class (0 open ❌).**
- **Tests**: 2 in `tests/test_arith_210_current_hp_no_floor.py` (zero → 0;
  positive unaffected). Green.

### `WIZ-053` — ✅ FIXED (surfaced via probe)

- **Python**: `mud/commands/imm_load.py:_restore_char`
- **ROM C**: `src/act_wiz.c:2808/2840/2861` (`update_pos`), `src/fight.c:update_pos`
- **Gap**: WIZ-053 — `do_restore` re-evaluated position with
  `if position < STANDING: position = STANDING`, over-promoting positions 4–7. ROM
  calls `update_pos(victim)`, which (with `hit > 0`) promotes to STANDING **only
  if `position <= POS_STUNNED`** — leaving RESTING/SITTING/SLEEPING/FIGHTING
  victims in place. A restored sleeping/resting player was wrongly stood up.
- **Fix**: call `update_pos(char)` — exact ROM mirror, covers all three restore
  branches via the shared `_restore_char` helper. Surfaced during the `update_pos`
  call-site audit (the position-transition divergence probe).
- **Tests**: 2 in `tests/integration/test_act_wiz_command_parity.py`
  (`test_restore_preserves_resting_position`, `test_restore_promotes_stunned_position`).
  Green. ACT_WIZ_C now has no outstanding gaps.

## Probe log (parity confirmed — no gap, recorded so the next agent need not re-probe)

The position-transition / affect-tick / group-follower sweep confirmed the
following are already ROM-faithful:

- **`char_update` per-tick `update_pos`** — guarded by `position == STUNNED`,
  matches ROM `src/update.c:719` (INV-019 already locks it).
- **Heal spells** (`cure_light`/`serious`/`critical`, `heal`) — all call
  `update_pos` after refilling HP, matching ROM `magic.c:1632/1675/1716/3116`.
- **`do_rest` furniture mechanics** (`mud/commands/position.py`) — REST_ON/IN/AT,
  `count_users` capacity, position-specific messages all mirror ROM `act_move.c`.
- **Affect tick** (`mud/affects/engine.py`) — 1/5 level-fade RNG ordering (GL-026),
  permanent-affect skip, `msg_off` last-of-type-group emission all faithful
  (INV-015/018). The `effects`-dict-only fallback path skipping the level-fade
  roll is unreachable for real chars (apply always mirrors into `affected`).
- **Follower chain** (`add_follower`/`stop_follower`/`die_follower`,
  `mud/characters/follow.py`) — every ROM `act_comm.c:1591-1680` contract matches,
  including the subtle `leader = fch` self-assignment (FOLLOW-003/004, INV-045/046).
- **Follower-move auto-stand** (`mud/world/movement.py:89`) — charmed-only stand +
  `position == STANDING` follow gate match ROM `act_move.c:213-217`.
- **`do_quit`** (`mud/commands/session.py:55`) — `FIGHTING` / `< STUNNED` guards
  match ROM `act_comm.c`.
- **`obj_update` decay messages** (`mud/game_loop.py:_object_decay_message`) — full
  per-item-type message table + container-float spill variant match ROM
  `update.c:913+`.
- **`saves_spell` / `saves_dispel`** (`mud/affects/saves.py`) — formula + `c_div`
  signed-math usage match ROM `magic.c` exactly (the `9*save/10` fMana line is
  c_div'd, and is masked by the trailing `URANGE(5,save,95)` regardless).

## Files Modified

- `mud/spawning/templates.py` — ARITH-210: `current_hp = max_hit` (drop zero floor).
- `mud/commands/imm_load.py` — WIZ-053: `_restore_char` calls `update_pos`.
- `tests/test_arith_210_current_hp_no_floor.py` — new (2 tests).
- `tests/integration/test_act_wiz_command_parity.py` — +2 WIZ-053 tests.
- `docs/parity/audits/ARITHMETIC_BOUNDARY.md` — ARITH-210 row → ✅ FIXED; class tally → 0 open.
- `docs/parity/ACT_WIZ_C_AUDIT.md` — WIZ-053 row → ✅ FIXED.
- `CHANGELOG.md` — WIZ-053 + ARITH-210 Fixed entries.
- `pyproject.toml` — 2.14.173 → 2.14.175.

## Test Status

- `tests/test_arith_210_current_hp_no_floor.py` — 2/2.
- `tests/integration/test_act_wiz_command_parity.py` (restore) — 7/7; full file + `test_fighting_state.py` — 140/140.
- Full suite: **5899 passed, 4 skipped** (`pytest`, 10m31s).

## Outstanding (for the next agent)

1. **The documented per-file + ARITH gap surface is drained.** The remaining
   known parity work is two **wide-blast-radius differential findings** that
   explicitly "need scoping with the user" — NOT loop-appropriate:
   - **FINDING-001** (`tools/diff_harness/FINDINGS.md`) — the `.are`→JSON converter
     field-shifts mob HP/mana/damage dice; **62/65 midgaard mobs** have wrong HP.
     Fix = regenerate every `data/areas/*.json` + add a regression. Blocks
     `combat_melee_rounds`.
   - **FINDING-006** (look.py half) — room-occupant rendering should use
     `show_char_to_char_0` (NPC `long_descr` when in `default_pos`); changes
     room-look for ALL NPCs. (The `MobInstance.long_descr` half is already done —
     `templates.py:452` copies it; FINDINGS.md part-2 text is stale on that point.)
2. **BOARD audit doc-rot (hygiene, not a parity gap).** `docs/parity/BOARD_C_AUDIT.md`
   function-table rows (lines ~30–48) show stale ❌/⚠️ statuses for gaps the
   gap-table (lines ~147–160) records as ✅ FIXED (BOARD-001/004/008 all FIXED;
   the "BOARD-018" function-table label is really BOARD-013, FIXED). Reconcile the
   two tables so a future agent doesn't re-open closed work.
3. **SESSION_STATUS stale-status note:** the prior status listed ARITH-114 as open;
   it was FIXED in 2.14.165 (audit row 50). Corrected this session.

## Next Steps

The probe-then-scope sweep on the obvious combat/position/affect candidates is
exhausted. Next session should either (a) scope FINDING-001 with the user (it is
the single highest-impact remaining parity bug — every JSON-loaded mob has wrong
stats), or (b) probe genuinely less-traveled subsystems not covered this session
(OLC save round-trips, shop/healer economics, weather/time, reset edge cases,
mob-program triggers) for fresh divergences. Run `/rom-divergence-sweep` for the
completeness lens.
