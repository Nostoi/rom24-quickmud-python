# Session Summary — 2026-06-10 — drink/eat condition lifecycle scenario + pcdata condition fix

## Scope

Continuation from v2.13.65 (FINDING-033 resolved). Session goal: implement the
`drink`/`eat`/`food` consumption diff-harness scenario identified as the top
candidate in the previous handoff. The scenario requires `__cond_hunger=<n>` (not
yet added) and proper condition meta-command wiring in both `diffmain.c` and
`pyreplay.py`.

## Outcomes

### `__cond_hunger=` meta-command — ✅ ADDED

- **C shim**: `src/diff_shim/diffmain.c` — added handler mirroring
  `__cond_full=` / `__cond_thirst=` pattern; sets
  `ch->pcdata->condition[COND_HUNGER] = atoi(line + 14)`.
- **Python**: `tools/diff_harness/pyreplay.py` — added handler writing to
  `char.pcdata.condition[int(Condition.HUNGER)]`.
- Completes the THIRST/FULL/HUNGER condition-injection trio.

### `pyreplay.py` condition meta-commands — ✅ FIXED (silent no-op bug)

- **Root cause**: `__cond_full=`, `__cond_thirst=`, `__cond_hunger=` were
  writing to a shadow `char.condition` attribute on the `Character` object.
  `do_drink` reads `ch.pcdata.condition`; the writes were silent no-ops for
  `do_drink` behavior. `drive_python_replay` initial setup also used
  `char.condition = [0, 48, 48, 48]` — same bug.
- **Fix**: all three meta-commands and the initial setup now write to
  `char.pcdata.condition`.
- **ROM C reference**: `src/act_obj.c` — both `do_drink` and `do_eat` read
  `ch->pcdata->condition[COND_*]`, not a separate character-level field.

### `do_eat` condition read path — ✅ FIXED (parity bug)

- **Root cause**: `consumption.py:do_eat` used `getattr(ch, "condition", None)`
  (character-level shadow attribute) for the fullness pre-check (EAT-003) and
  the hunger/full gain block. `do_drink` correctly used `ch.pcdata.condition`.
  The inconsistency was masked because `pyreplay.py` was setting the shadow
  attribute, accidentally making `do_eat` appear to work in some tests.
- **Fix**: both reads in `do_eat` now use
  `pcdata = getattr(ch, "pcdata", None); condition = getattr(pcdata, "condition", None)`,
  exactly mirroring `do_drink`'s pattern and ROM `ch->pcdata->condition`.
- **ROM C reference**: `src/act_obj.c:1310-1334` — `do_eat` reads
  `ch->pcdata->condition` in both the pre-check and the gain block.
- **Integration test update**: `test_eat_full_character_blocked` updated to set
  `pcdata.condition[1]` directly. `test_character` fixture in
  `tests/integration/test_consumables.py` resets conditions to `[0, 0, 0, 0]`
  so the PCData default (FULL=48) does not block every eat test after the fix.

### `drink_eat_condition_lifecycle` diff-harness scenario — ✅ CAPTURED

- **Scenario file**: `tools/diff_harness/scenarios/drink_eat_condition_lifecycle.json`
- **Steps**: `__cond_thirst=0`, `__cond_full=0`, `__cond_hunger=0`,
  `__oload=3135` (fountain), `drink`, `__oload=3011` (bread), `get bread`,
  `eat bread`
- **C golden**: `tests/data/golden/diff/drink_eat_condition_lifecycle.golden.json`
- **Key ROM semantics confirmed by golden**:
  - `do_drink` (ITEM_FOUNTAIN): `amount = liq_table[water].liq_affect[4] * 3 = 48`;
    thirst gain = `48 * 10 / 10 = 48`; fires "Your thirst is quenched." when
    `condition[COND_THIRST] > 40` (`src/act_obj.c:1256`).
  - `do_eat` (ITEM_FOOD): "You are no longer hungry." fires when prior hunger
    was 0 AND new hunger > 0 (`src/act_obj.c:1331`) — a 0→positive **edge
    trigger**, not a `> 40` threshold like thirst. Setting hunger to 30 instead
    of 0 silently misses the message.
- **C golden output** (steps with messages):
  - step 5 `drink`: `['You drink water from a fountain.', 'Your thirst is quenched.']`
  - step 7 `get bread`: `['You get a bread.']`
  - step 8 `eat bread`: `['You eat a bread.', 'You are no longer hungry.']`
- Python output matches C golden exactly after the pcdata fixes.

## Files Modified

- `src/diff_shim/diffmain.c` — added `__cond_hunger=` handler
- `tools/diff_harness/pyreplay.py` — added `__cond_hunger=` handler; fixed all
  condition writes to use `char.pcdata.condition`
- `mud/commands/consumption.py` — fixed `do_eat` to read `ch.pcdata.condition`
  (EAT-003 pre-check and hunger/full gain block)
- `tests/integration/test_consumables.py` — updated `test_eat_full_character_blocked`
  to set `pcdata.condition`; reset conditions to `[0, 0, 0, 0]` in fixture
- `tools/diff_harness/scenarios/drink_eat_condition_lifecycle.json` — new scenario
- `tests/data/golden/diff/drink_eat_condition_lifecycle.golden.json` — new C golden
- `CHANGELOG.md` — added [2.13.66] Added/Fixed entries
- `pyproject.toml` — 2.13.65 → 2.13.66

## Test Status

- Diff harness: **46 passed** (27 scenarios: 19 smoke + 27 unit was previously
  26 scenarios, 44 tests; now 27 scenarios, 46 tests)
- Full suite: **5508 passed, 4 skipped** (was 5507 passed, 4 skipped)

## Next Steps

Cross-file invariants remains the active pass. All known open findings are resolved.
Concrete candidates:

1. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule.

2. **Further diff-harness coverage** — condition decay over time (`char_update`
   hunger/thirst tick-down), poison-food lifecycle, or `do_buy`/`do_sell` shop
   condition paths not yet covered by a scenario.

3. **`gain_condition` Python implementation audit** — the fix revealed that Python
   `do_eat` used inline `min(48, ...)` arithmetic instead of calling `gain_condition`.
   The C golden exercise confirmed the output matches, but a direct audit of
   `gain_condition` in `mud/utils/update.py` against `src/update.c:367` would
   close any remaining parity questions on tick-based condition decay.
