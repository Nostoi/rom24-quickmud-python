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

### `GAIN-002` — ✅ FIXED

- **Python**: `mud/commands/remaining_rom.py:240-258` (`do_gain` points branch)
- **ROM C**: `src/skills.c:149-172`
- **Gap**: `gain points` was backwards on three counts — it *raised* creation
  points by 1 (ROM lowers them; `exp_per_level` rises with points, so ROM trades
  2 trains to make leveling *easier*), skipped the `points <= 40` gate, and never
  recomputed `exp = exp_per_level(ch, points) * level`. Wrong message too.
- **Fix**: added the `<= 40` gate, flipped `+= 1` → `-= 1`, recompute exp via the
  existing `exp_per_level(char)`, message "...feel more at ease with your skills."
- **Tests**: `test_gain_points_spends_two_trains_to_lower_points_and_recalcs_exp`
  + `test_gain_points_refuses_when_points_at_or_below_40`.

### `GROUPS-001` — ✅ FIXED

- **Python**: `mud/commands/remaining_rom.py:282-300` (`do_groups` no-arg branch)
- **ROM C**: `src/skills.c` `do_groups`
- **Gap**: `do_groups` (no arg) **crashed** (`AttributeError: 'tuple' object has
  no attribute 'keys'`) for any player who knew a group — `pcdata.group_known` is
  a `tuple[str, ...]` of names but the branch treated it as a dict.
- **Fix**: iterate the name tuple directly. Empirically reproduced + regression in
  `tests/integration/test_do_groups_known_groups.py`.

### `do_gain` fully ported (GAIN-001/003/004 — all ✅ FIXED)

`do_gain` was substantially un-ported; `skills.c` is tracker-✅ only for the 37
skill **handlers**, not these trainer **commands**. After the infra-gate scope
(every primitive verified present — `get_group` ratings/skills, `skill_registry`
ratings + `Skill.type`, `pcdata.learned`/`group_known`), all three closed:
- **GAIN-001** (CRITICAL) — ✅ implemented `gain <skill>`/`gain <group>`: runtime
  recursive `_gn_add` (mark group known + grant component skills/sub-groups),
  group + skill branches with ROM's validation gates, spell guard via
  `Skill.type == "spell"`, deduct `train` (the trainer currency, distinct from
  the creation-session `add_group` which deducts creation points). Tests:
  `tests/integration/test_do_gain_act_gain_bit.py` (gain group + component
  skills, gain skill, gain-spell refused, insufficient-train, already-known).
- **GAIN-003** — ✅ `gain list` builds the two real 3-column price tables
  (unknown groups, then unknown non-spell skills with `rating[class] > 0`).
- **GAIN-004** — ✅ trainer lines ROM-capitalized via `_gain_trainer_name`
  (`capitalize_act_line`). One **bounded residual**: the no-arg `do_say`-to-room
  broadcast is returned to the caller only (changing it touches `do_gain`'s
  string-return contract).

### `WIZ-054` — ✅ FIXED

- **Python**: `mud/commands/remaining_rom.py:do_guild`
- **ROM C**: `src/act_wiz.c:238-246`
- **Gap**: `do_guild`'s non-independent (member) clan branch over-delivered the
  victim message. ROM builds the victim's "You are now a member of clan X."
  buffer but **never `send_to_char(buf, victim)`** in that branch — only the
  *independent* branch (`:236`) notifies the victim. So a member-clan assignee is
  silently assigned in ROM (a genuine quirk). The WIZ-023 port added the victim
  `_send_to_char` to both branches.
- **Fix**: dropped the victim delivery in the non-independent branch (admin/`ch`
  return line unchanged). Test:
  `tests/integration/test_act_wiz_command_parity.py::test_guild_member_clan_does_not_notify_victim`.
- **Note**: surfaced probing `remaining_rom.py` — the same under-audited
  catch-all file that hid GAIN-001 / GROUPS-001 (the session's richest vein).

### `MOBCMD-022` — ✅ FIXED

- **Python**: `mud/commands/remaining_rom.py:do_mob`
- **ROM C**: `src/mob_cmds.c:82-90`
- **Gap**: the live `mob` command (registered in the dispatcher; used by mob
  programs + MAX_LEVEL immortals) was a **stub** — it returned `"Mob command
  executed: <args>"` and never dispatched. ROM `do_mob` runs a security check
  then `mob_interpret(ch, argument)`; Python's `mob_interpret` already existed
  (`mud/mob_cmds.py:1389`).
- **Fix**: `do_mob` now calls `mob_interpret(char, args)` after the security gate
  and returns no text (the interpreter owns output/effects and is silent on
  empty/unknown, as ROM is). Test:
  `tests/test_mobprog_commands.py::test_do_mob_command_dispatches_to_mob_interpret`
  (`mob goto <vnum>` actually moves the controller).
- **Note**: fourth gap from `remaining_rom.py` this session.

### `FLAG-003` — ✅ FIXED (filed as a candidate, then closed at the maintainer's call)

- **Python**: `mud/commands/remaining_rom.py:do_flag`
- **ROM C**: `src/flags.c:248-250`
- **Gap**: ROM `do_flag` ends the success path `*flag = new; return;` and sends
  the invoker no confirmation. Python returned an invented `"Flag '<field>'
  updated on <name>."` (over-delivery, same class as WIZ-054 / MOBCMD-022).
- **Fix**: `do_flag` now returns `""` on success (the flag is still mutated).
  Test: `tests/integration/test_flag_command_parity.py::test_flag_success_is_silent_like_rom`.
- **Process note**: initially filed as a ⚠️ CANDIDATE rather than closed
  unilaterally, because `flag` is immortal-only debug tooling and a silent success
  is debatable UX — closed once the maintainer confirmed they want strict parity.

### `WIMPY-001` — ✅ FIXED (filed as a candidate, then closed at the maintainer's call)

- **Python**: `mud/commands/remaining_rom.py:do_wimpy`
- **ROM C**: `src/act_info.c:2811`
- **Gap**: ROM `do_wimpy` uses `wimpy = atoi(arg)` — non-numeric input → 0, NOT
  rejected. Python returned the invented "Wimpy must be a number." and left wimpy
  unchanged.
- **Investigation**: the strict "must be a number" pattern lives only in OLC
  builder commands (`build.py`, a Python-specific interface); direct ROM ports
  replicate atoi (`group_commands.py:do_split` cites "ROM uses atoi() which
  returns 0 for non-numeric input"). So `do_wimpy` is a genuine divergence, not a
  convention. The act_info row was "✅ 100% COMPLETE! (0 gaps)" — another false-100%.
- **Fix**: `do_wimpy` now mirrors atoi (non-numeric → 0 → "Wimpy set to 0 hit
  points."). The 2 existing tests that pinned the non-ROM rejection were corrected
  (AGENTS.md: a test contradicting ROM is a test bug). Tests:
  `tests/test_player_wimpy.py::TestWimpyEdgeCases::test_wimpy_non_numeric_sets_zero_like_rom_atoi`
  + `::test_wimpy_invalid_input_overwrites_to_zero_not_preserved`.

### FINDING-001 correction (stale handoff claim)

The handoff buffer flagged "FINDING-001 — `.are`→JSON converter field-shifts mob
HP for 62/65 midgaard mobs" as the highest-impact **open** bug. Re-verifying
against source: the HP field-shift bug is **FINDING-006**, **RESOLVED 2026-05-28**
(DB2-007, commit `1857b5f8`; phantom `ac` token, all area JSONs regenerated).
Empirically re-verified: drunk #3064 max_hit 31 (`2d6+22`), Hassan #3001 1000
(`1d1+999`), `tests/test_mob_dice_parity.py` 2/2. FINDING-001 is an unrelated,
also-resolved `look`/long_descr bug. Wrong ID + wrong status — corrected in
SESSION_STATUS and here so it isn't chased again.

### `board.c` Phase-1 table reconciliation

`BOARD_C_AUDIT.md` Phase-3 recorded BOARD-001..014 ✅ FIXED, but the Phase-1
function-inventory table + intro still showed ⚠️/❌ for those closed gaps, with
two wrong gap-ID citations (do_help fallback cited BOARD-013 → really BOARD-012;
personal_message cited phantom "BOARD-018" → really BOARD-013). Re-verified
(board suite 36/36, default boards seed, `make_note`/`personal_message` present)
and flipped the 8 stale rows.

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
2. ~~FINDING-001 mob-HP field-shift~~ — **STALE handoff claim, corrected
   2026-06-19.** The HP field-shift bug is **FINDING-006**, **RESOLVED 2026-05-28**
   (DB2-007, commit `1857b5f8`; regression `tests/test_mob_dice_parity.py`).
   Re-verified empirically this session (drunk #3064 max_hit 31, Hassan #3001
   1000, regression 2/2). Nothing to do. The prior handoff propagated a wrong ID
   and wrong status — a textbook AGENTS.md stale-✅ trap.
3. **Doc-hygiene:** `docs/parity/BOARD_C_AUDIT.md` function-table rows (~30-48)
   still carry stale ❌/⚠️ for gaps the gap-table records as ✅ FIXED — reconcile.
