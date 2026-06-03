# Session Summary — 2026-06-02 — MOVE-005 exit-trigger ordering + MOVE-006 encumbrance-gate removal (mob-trigger cross-file probe)

## Scope

Picked up from SESSION_STATUS (2.12.80, class 6 fully closed). With the
divergence-class roster's pointer-identity class done and no INV-034 follow-up,
the active mode is **cross-file invariants via probe-then-scope**, and the
standing candidate was **mob-trigger ordering** (bribe/exit/fight/kill/hpcnt).
This session ran that probe and closed the one divergence it surfaced.

## Probe results (mob-trigger ordering)

- **FIGHT / HPCNT** — already enforced (INV-026 VIOLENCE-TRIGGER-DISPATCH-SCOPE).
- **ACT** — already enforced (INV-025 MOBPROG-ACT-TRIGGER-DISPATCH).
- **KILL / DEATH** — already implemented in the combat engine
  (`mp_kill_trigger`/`mp_death_trigger` before `raw_kill`, FIGHT references).
- **EXIT** — **divergence found** → closed as MOVE-005 (below).
- **BRIBE / GIVE** — verified at the **call-site ordering** dimension (the one
  that caught EXIT, not just the trigger fns). ROM `src/act_obj.c:do_give`:
  object path = `obj_from_char`→`obj_to_char`→act trio (MOBtrigger off)→
  `mp_give_trigger` (lines 830–842); coins path = gold/silver transfer→act trio→
  `mp_bribe_trigger(silver ? amount : amount*100)`→changer (lines 718–735).
  `mud/commands/give.py` matches both: `add_object`→messages→`mp_give_trigger`,
  and money deduct/add→messages→`mp_bribe_trigger`→`_handle_changer_exchange`.
  No ordering divergence.
  (A latent edge in `mp_exit_trigger`: a non-numeric/empty `trig_phrase` is
  treated as match-any in Python but `atoi`→0 = north in ROM — noted, not filed;
  exit trig phrases are numeric in practice. Re-derive if it ever matters.)

## Outcome — MOVE-005 (✅ FIXED, 2.12.81)

- **ROM**: `src/act_move.c:move_char` fires `mp_exit_trigger(ch, door)` as the
  **first** action after the door-bounds check (lines 78–82) — before the
  exit-existence/`can_see_room` check (85–91), the movement-cost gate (122–126),
  and any other gate. The exit trigger keys on the attempted direction alone
  (`dir == atoi(prg->trig_phrase)`), independent of map topology or the mover's
  state.
- **Gap**: `mud/world/movement.py:move_character` invoked `mp_exit_trigger` only
  *after* the (non-ROM) encumbrance gate AND after the `exit is None` early
  return. So a PC walking into a wall, or while over-encumbered, never fired the
  room's TRIG_EXIT program — e.g. a guard mob scripted to react to an attempt to
  leave through a non-exit stayed silent.
- **Why the per-file audit missed it**: `ACT_MOVE_C_AUDIT.md`'s line-by-line
  table marked item 2 (exit trigger) ✅ PARITY by verifying the trigger is
  *called* — never its *order*. This is the exact cross-file blind spot
  AGENTS.md's cross-file-invariants section warns about (function-presence ≠
  call-order). Audit rows corrected (items 2 & 3, plus the new MOVE-005 gap row).
- **Fix**: relocate the `if not char.is_npc: mp_exit_trigger(char, idx)` block to
  immediately after `idx = dir_map[dir_key]`, before the encumbrance and
  exit-existence checks. Pure statement reorder; signature/return contract
  unchanged.
- **Test (RED-first)**: `tests/integration/test_move005_exit_trigger_ordering.py`
  — two cases, both failing before the fix: (a) no-exit direction, (b)
  over-encumbered PC. Each spies `mp_exit_trigger` and asserts it is reached
  (and aborts the move) despite the would-be-earlier gate.

## Outcome 2 — MOVE-006 (✅ FIXED, 2.12.82, same session)

Filed mid-MOVE-005 as out-of-scope, then closed in the same session after user
confirmation (the removal changes player-facing behavior + touches a
parity-claiming test file, so I surfaced it via `AskUserQuestion` before
deleting).

- **ROM**: `move_char` has **no carry-weight/carry-number movement gate
  anywhere** (verified across all of `src/`) — movement is gated only on move
  points (`if (ch->move < move) "You are too exhausted."`, lines 122–126),
  terrain, boats, and flags. ROM enforces carry limits at **pickup/transfer**
  time instead (`do_get` `act_obj.c:105-115`, `do_give` `:811-820`, get/wear
  `:2313-2321` → "you can't carry that much weight."), so a PC can never
  *become* overweight enough to need a movement gate.
- **Gap**: Python `move_character` had a `"You are too encumbered to move."`
  early-return (`get_carry_weight > can_carry_w or carry_number > can_carry_n`)
  — a non-ROM invention with **no ROM basis**. **5 tests asserted the
  `"too encumbered"` block with no ROM citation at all** (the nearby
  `# ROM act_move.c:204` comments are *correct* — they annotate the separate
  arrival/"Destination"-seen assertions; line 204 is `act("$n has arrived.")`).
  My first draft of this summary wrongly called :204 a "misattribution
  justifying the gate" — corrected here after an advisor recall check (the gate
  was simply uncited).
- **Fix**: removed the early-return; **kept** all carry-cap machinery
  (`can_carry_w`/`can_carry_n`/`get_carry_weight` + the `do_get` pickup gates —
  those *are* ROM-correct). Corrected the 5 test sites to assert ROM behavior
  (overweight PC moves): `test_world.py` (renamed
  `..._cannot_move`→`..._can_still_move`), `test_encumbrance.py`
  (3 movement tests → 2 inverted + 1 `wait_state` test deleted),
  `test_architectural_parity.py` (kept the pickup-block assertion, inverted the
  movement portion), and reframed the MOVE-005 `..._when_encumbered` test
  (`get_carry_weight` monkeypatch was now inert).
- **RED-first test**: `tests/integration/test_move006_no_encumbrance_movement_gate.py`
  — overweight PC + huge coin burden both move to dest (2 tests, failed before).
- **Net test delta**: +2 (new file) − 1 (deleted `test_overweight_move_sets_wait_state`) = +1.

## Files Modified

**MOVE-005:**
- `mud/world/movement.py` — `move_character`: `mp_exit_trigger` block relocated
  to the top (after `idx` lookup), before encumbrance + exit-existence gates.
- `tests/integration/test_move005_exit_trigger_ordering.py` — new (2 RED→GREEN;
  the `..._encumbered` case later reframed for MOVE-006).
- `docs/parity/ACT_MOVE_C_AUDIT.md` — MOVE-005 row (FIXED); corrected
  line-by-line items 2 & 3.

**MOVE-006 (same session):**
- `mud/world/movement.py` — removed the `"You are too encumbered to move."`
  early-return; added a MOVE-006 comment citing ROM.
- `tests/integration/test_move006_no_encumbrance_movement_gate.py` — new (2 RED→GREEN).
- `tests/test_world.py`, `tests/test_encumbrance.py`,
  `tests/integration/test_architectural_parity.py` — 5 assertions corrected to
  ROM behavior (1 wait-state test deleted).
- `docs/parity/ACT_MOVE_C_AUDIT.md` — MOVE-006 row → ✅ FIXED.

**Both:** `CHANGELOG.md` (2 Fixed entries), `pyproject.toml`
(2.12.80 → 2.12.81 → 2.12.82).

## Test Status

- `tests/integration/test_move005_exit_trigger_ordering.py` — 2/2 passing
  (2 failing before the fix).
- Full suite: **5363 passed, 4 skipped** in 221.81s — +2 vs the 2.12.80 baseline
  (5361) = the two new MOVE-005 tests; **zero regressions** (movement is a
  CRITICAL-blast-radius surface: 11 direct callers — all movement commands, AI
  wander, mob flee, spec_funs, agent adapter).
- `ruff check` on edited files: clean.
- `gitnexus_impact` on `move_character`: CRITICAL (11 direct callers) — but the
  change is a behavior-preserving statement reorder; `detect_changes` post-edit:
  LOW risk, 0 affected processes.

## Commits

- `8681630c` — `fix(parity): MOVE-005 — fire mob TRIG_EXIT before exit-existence/encumbrance gates (2.12.81)`
- `80cbf34d` — `docs(session): MOVE-005 exit-trigger ordering summary + SESSION_STATUS (2.12.81)` (pushed to origin)
- `0c890d57` — `fix(parity): MOVE-006 — remove non-ROM "too encumbered to move" movement gate (2.12.82)`
- _(this MOVE-006 summary + SESSION_STATUS refresh)_ — docs(session).

## Full-suite status (final)

**5364 passed, 4 skipped** (180.44s) after MOVE-006 — zero regressions on the
CRITICAL-blast-radius movement surface (11 direct callers). `ruff check` clean on
all edited lines (`test_encumbrance.py` carries 3 pre-existing import-sort errors
outside the edited region — not introduced here).

## Next Steps

Mob-trigger ordering probe is exhausted (FIGHT/HPCNT/ACT/KILL/DEATH enforced;
EXIT closed via MOVE-005; BRIBE/GIVE verified at call-site ordering). Candidate
next passes:

1. **Highest-ceiling (multi-day):** `diff_harness` Hypothesis widening
   (`tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md`) — the only
   enumeration-independent path to *unknown* divergences.
2. **New cross-INV probe area** — position-transition edges, affect ticks, or
   mob random/delay (`TRIG_RANDOM`/`TRIG_DELAY` in `update.c`) ordering.
3. **Housekeeping:** INV tracker consolidation (27 rows, past the ~20 soft cap).

> **Push note:** `origin/master` is at `80cbf34d` (2.12.81 — MOVE-005 pushed).
> The MOVE-006 commit `0c890d57` (2.12.82) + this docs follow-up are
> **unpushed**. CHANGELOG/version reflect 2.12.82.
