# Session Summary — 2026-06-19 — HEALER-005/006 + divergence-sweep probe

## Scope

Loop session ("close the next gap via /rom-gap-closer, repeat for 10, then
handoff"). The documented per-file gap surface was already drained (prior
sessions), so this ran in **probe-then-scope mode**: read a less-traveled ROM C
contract → read the Python equivalent → write a failing test for any divergence
→ close it. Two genuine gaps surfaced in `healer.c` (a file previously marked
✅ AUDITED), both closed. Two stale "deferred to P2" doc rows were reconciled.
Weather/time and drink probes confirmed parity (no gap). Stopped at the honest
number of real gaps (2) rather than padding toward the loop's ceiling of 10 —
the advisor-endorsed posture, consistent with the prior loop session's stop at 2.

## Outcomes

### `HEALER-005` — ✅ FIXED

- **Python**: `mud/commands/healer.py:230-234`
- **ROM C**: `src/healer.c:171-176`
- **Gap**: insufficient-funds refusal returned the bare line `"You do not have
  enough gold for my services."`; ROM emits `act("$N says '...'", ch, NULL, mob,
  TO_CHAR)` → `"<Healer> says '...'"`, first-letter-capitalized by `act_new`
  (INV-029). Internally inconsistent too — the no-arg and bad-service branches
  already carried the `<healer> says` wrapper.
- **Fix**: wrapped via `capitalize_act_line(f"{name} says '...'")`. Updated the
  stale `tests/test_healer.py` assertion that pinned the non-ROM bare string.
- **Tests**: `tests/integration/test_healer_command_parity.py::test_heal_insufficient_funds_uses_act_says_wrapper` + corrected `tests/test_healer.py::test_healer_denies_when_insufficient_gold`.

### `HEALER-006` — ✅ FIXED

- **Python**: `mud/commands/healer.py:_match_service` / new `_MATCH_ORDER`
- **ROM C**: `src/healer.c:147,156`
- **Gap**: ROM's if/else checks `mana`/`energize` (line 147) **before**
  `refresh`/`moves` (line 156), but the price list **prints** refresh before
  mana (lines 77-78). Prefix matching makes the order observable: `heal m` is a
  prefix of both `"mana"` and `"moves"` → ROM resolves it to **mana** (1000
  silver), Python wrongly did **refresh** (500 silver). Python used one
  `_SERVICES` tuple (display order) for both display and matching.
- **Fix**: added an explicit `_MATCH_ORDER` tuple in ROM if/else order, consumed
  by `_match_service` via a `_SERVICES_BY_KEY` map — decoupled from display order.
- **Tests**: `tests/integration/test_healer_command_parity.py::test_heal_m_matches_mana_before_refresh`.

### Doc reconciliation (not gaps — stale-status hygiene)

- **Position Commands furniture support** (`ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`):
  the "39% — missing furniture support / deferred to P2" row was stale.
  Confirmed `mud/commands/position.py` has full furniture support
  (`_resolve_furniture` + `value[2]` position-bitfield gating). Flipped ⚠️ → ✅.
- **Pet persistence** (`fwrite_pet`/`fread_pet`, same tracker): "❌ Not
  Implemented — deferred to P2" was stale. Confirmed `_serialize_pet` →
  `db_char.pet_state` save and `_deserialize_pet` load
  (`mud/models/character.py:1376-1381`), round-trip tested. Flipped ❌ → ✅.
  (Both rows were the "deferred to P2" pattern AGENTS.md forbids — both turned
  out to be already-done work mislabeled.)

### Probes confirming PARITY (don't re-probe)

- **`weather_update`** (`src/update.c:522-654` ⇄ `mud/game_loop.py:weather_tick`):
  pressure math, RNG draw order (`diff*dice(1,4) + dice(2,6) - dice(2,6)`), and
  all four sky-state transitions are faithful. ROM uses double-`if` for CLOUDY /
  RAINING where Python uses `elif`, but the pressure thresholds are mutually
  exclusive, so transitions AND `number_bits(2)` draw counts are identical.
- **time / sunlight** (`advance_hour` ⇄ ROM hour-switch): hour→day→month→year
  rollover and all four sunlight messages match; ROM's unconditional day/month
  checks equal Python's nested ones because `day` only reaches 35 right after
  increment.
- **`do_drink`** (`src/act_obj.c:1161-1280` ⇄ `mud/commands/consumption.py`):
  already well-audited (DRINK-001..011), uses `c_div` for signed `liq_affect`
  math, correct fountain/drink-con dispatch, immortal bypass, drunk pre-check.

## Files Modified

- `mud/commands/healer.py` — HEALER-005 (act wrapper) + HEALER-006 (`_MATCH_ORDER`).
- `tests/integration/test_healer_command_parity.py` — 2 new parity tests.
- `tests/test_healer.py` — corrected stale bare-string assertion (HEALER-005).
- `docs/parity/HEALER_C_AUDIT.md` — added + flipped HEALER-005/006 to ✅; status back to AUDITED (6 gaps).
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — reconciled 2 stale P2 rows.
- `CHANGELOG.md` — Fixed entries for HEALER-005/006.
- `pyproject.toml` — 2.14.175 → 2.14.177.

## Test Status

- `pytest tests/test_healer.py tests/test_healer_parity.py tests/test_healer_rom_parity.py tests/integration/test_healer_command_parity.py` — 25/25 passing.
- Full suite: **5901 passed, 4 skipped** (321s parallel).
- `ruff check .` clean.

## Next Steps

The documented per-file + ARITH gap surface remains drained; the cross-file /
divergence-sweep pass is the active mode. Probe-then-scope yielded 2 gaps in
`healer.c`; the well-trodden surfaces probed (weather/time, drink) are faithful.

1. **Continue probe-then-scope on less-traveled subsystems not yet covered** —
   OLC save round-trips, shop `do_buy` haggle/credit edges, reset edge cases,
   mob-program trigger dispatch, bank/deposit, `do_practice`/`do_gain`. Use
   `/rom-divergence-sweep` for the completeness lens.
2. **FINDING-001** (`tools/diff_harness/FINDINGS.md`) — highest-impact open bug
   (`.are`→JSON converter field-shifts mob HP for 62/65 midgaard mobs). WIDE
   blast radius — **scope with the user**, not an unattended loop.
3. **Doc-hygiene:** `docs/parity/BOARD_C_AUDIT.md` function-table rows (~30-48)
   still carry stale ❌/⚠️ for gaps the gap-table records as ✅ FIXED — reconcile.
