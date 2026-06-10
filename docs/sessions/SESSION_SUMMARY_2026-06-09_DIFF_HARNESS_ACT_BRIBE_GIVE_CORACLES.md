# Session Summary — 2026-06-09 — Diff-harness C-oracle for TRIG_ACT, TRIG_BRIBE, TRIG_GIVE

## Scope

Continuing from v2.13.54. The "Next Steps" from the EXALL/GREET/GRALL session listed TRIG_SPEECH,
TRIG_ACT, TRIG_BRIBE, and TRIG_GIVE as the remaining deterministic Class 11 dispatch paths
without C-oracle scenarios. TRIG_SPEECH already had a scenario (`mob_speech_trigger.json`)
committed in an earlier session, so this session covered the three remaining paths: ACT, BRIBE,
and GIVE. No Python engine code was changed — all three dispatch paths were already correctly
implemented. The work was authoring scenario JSON files, capturing C-oracle goldens from the
`src/diffshim` binary, and verifying Python/C agreement.

One complication arose for the GIVE scenario: mob vnum 3000 (the wizard) is a shop keeper in
the ROM `.are` file and C rejected the item give with "Sorry, you'll have to sell that." — the
shop-keeper check fires before `mp_give_trigger`. The fix was straightforward: use mob 3007
(the sailor), which is not a shop keeper, as the recipient. This substitution also revealed
a latent parity gap (Python's `_has_shop` returns False for the wizard because the midgaard
JSON area file has no `shops` section, while the ROM C area file does define wizard as a
shop keeper). That gap is pre-existing and distinct from the GIVE trigger coverage; it is
not filed here as it affects shop interaction, not mobprog dispatch.

## Outcomes

### `mob_act_trigger` scenario — ✅ ADDED (diff-harness C-oracle)

- **Scenario**: `tools/diff_harness/scenarios/mob_act_trigger.json`
- **Golden**: `tests/data/golden/diff/mob_act_trigger.golden.json` (9 steps, C binary)
- **ROM C refs**:
  - `src/comm.c:2385` — inside `act()`, every NPC recipient with `HAS_TRIGGER(to, TRIG_ACT)`
    receives `mp_act_trigger(buf, to, ch, arg1, arg2, TRIG_ACT)`.
  - `src/mob_prog.c:1183-1197` — `mp_act_trigger`: iterates mprogs, `strstr(argument,
    trig_phrase)` to match, then calls `program_flow`.
- **Design**: mob 3000 (wizard) in room 3001, prog `act:stands up:say ACT trigger fired!`.
  PC does `sit` (no match — "sits down" ≠ "stands up"), then `stand` → `do_stand` emits
  `act("$n stands up.", ch, NULL, NULL, TO_ROOM)` → wizard receives "Tester stands up." →
  trig_phrase "stands up" matches → wizard says "ACT trigger fired!".
- **C oracle step 8 output**: `["\rYou stand up.", "\rThe wizard says 'ACT trigger fired!'"]`
- **Tests**: `test_python_matches_c_golden[mob_act_trigger]` — PASSED.

### `mob_bribe_trigger` scenario — ✅ ADDED (diff-harness C-oracle)

- **Scenario**: `tools/diff_harness/scenarios/mob_bribe_trigger.json`
- **Golden**: `tests/data/golden/diff/mob_bribe_trigger.golden.json` (9 steps, C binary)
- **ROM C refs**:
  - `src/act_obj.c:710-735` — after money transfer from PC to mob, calls
    `mp_bribe_trigger(victim, ch, silver ? amount : amount*100)`.
  - `src/mob_prog.c:1198-1206` — `mp_bribe_trigger`: fires when `amount >= atoi(trig_phrase)`.
- **Design**: mob 3000 (wizard) in room 3001, prog `bribe:100:say BRIBE trigger fired!`.
  PC's silver set to 200 via `__silver=200`. `give 150 silver wizard` → 150 >= 100 threshold →
  wizard says "BRIBE trigger fired!". Note: money transfer happens before the trigger fires,
  so the wizard's silver balance is already updated when the prog executes.
- **C oracle step 8 output**: `["\rYou give the wizard 150 silver.", "\rThe wizard says 'BRIBE trigger fired!'"]`
- **Tests**: `test_python_matches_c_golden[mob_bribe_trigger]` — PASSED.

### `mob_give_trigger` scenario — ✅ ADDED (diff-harness C-oracle)

- **Scenario**: `tools/diff_harness/scenarios/mob_give_trigger.json`
- **Golden**: `tests/data/golden/diff/mob_give_trigger.golden.json` (10 steps, C binary)
- **ROM C refs**:
  - `src/act_obj.c:842` — after object transfer from PC to mob, calls `mp_give_trigger(victim, ch, obj)`.
  - `src/mob_prog.c:1207-1242` — `mp_give_trigger`: matches by vnum if `is_number(p)`, else
    by object name keyword.
- **Design**: mob 3007 (sailor, non-shopkeeper) in room 3001, prog `give:3028:say GIVE trigger fired!`.
  Object 3028 ("a wooden staff") loaded in room via `__oload=3028`. PC does `get staff`, then
  `give staff sailor` → vnum 3028 matches trig_phrase "3028" → sailor says "GIVE trigger fired!".
- **C oracle step 9 output**: `["\rYou give a wooden staff to the sailor.", "\rThe sailor says 'GIVE trigger fired!'"]`
- **Tests**: `test_python_matches_c_golden[mob_give_trigger]` — PASSED.

## Files Modified

- `tools/diff_harness/scenarios/mob_act_trigger.json` — new scenario (9 steps)
- `tools/diff_harness/scenarios/mob_bribe_trigger.json` — new scenario (9 steps)
- `tools/diff_harness/scenarios/mob_give_trigger.json` — new scenario (10 steps)
- `tests/data/golden/diff/mob_act_trigger.golden.json` — C-oracle golden (9 steps)
- `tests/data/golden/diff/mob_bribe_trigger.golden.json` — C-oracle golden (9 steps)
- `tests/data/golden/diff/mob_give_trigger.golden.json` — C-oracle golden (10 steps)
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — item 6 updated with ACT/BRIBE/GIVE C-oracle status
- `CHANGELOG.md` — added [2.13.55] entry
- `pyproject.toml` — 2.13.54 → 2.13.55

## Test Status

- `pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py` — 31 passed, 1 skipped
- Full suite: **5,484 passed, 5 skipped** (all 3 new scenarios pass on first run)

## Outstanding Observations

- **Latent parity gap: wizard shop status.** Python's `_has_shop` returns False for mob 3000
  (wizard) because the midgaard JSON area file has no `shops` section, while ROM C's midgaard.are
  defines wizard as a shop keeper. Python's `do_give` would accept object gives to the wizard
  where C rejects them with "Sorry, you'll have to sell that." This is not filed as a new gap
  here — it pre-exists and falls under the shop/buy/sell domain — but it should be reviewed
  against the shop scenario coverage (`shop_buy_weapon`, `shop_sell_weapon`).

## Next Steps

Class 11 remaining work:

1. **RNG-locked paths** (`TRIG_RANDOM`, `TRIG_DELAY`) — deferred until a reproducible seed
   sequence is proven via a grounded probe. These require careful RNG alignment between C and
   Python to get deterministic C oracle output.
2. **Remaining deterministic dispatch paths** — TRIG_HITPNT (`hpcnt`), TRIG_FIGHT (`fight`),
   TRIG_DEATH, TRIG_KILL, TRIG_SURR already have OLC MEdit runtime probes but no diff-harness
   C-oracle scenarios. These can be authored next if Class 11 C-oracle completeness is the goal.
3. **Next divergence class** — consult `docs/parity/DIVERGENCE_CLASS_ROSTER.md` for the next
   unverified surface outside Class 11. Candidates: async message delivery ordering, affect-tick
   contracts, position-transition invariants.
