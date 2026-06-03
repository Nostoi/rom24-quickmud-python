# Session Summary — 2026-06-02 — MOVE-005 exit-trigger ordering (mob-trigger cross-file probe)

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

## Out-of-scope finding filed durably — MOVE-006 (❌ OPEN)

While reading the full `move_char` body for MOVE-005: ROM `move_char` has **no
carry-weight/carry-number movement gate anywhere** — movement is gated only on
move points (`if (ch->move < move) "You are too exhausted."`), terrain, boats,
and flags. The Python `"You are too encumbered to move."` early-return
(`get_carry_weight > can_carry_w`) is a **non-ROM invention**. Filed as MOVE-006
in `ACT_MOVE_C_AUDIT.md` (pending verification of whether any ROM derivative
added it; if not, remove for parity). Not fixed this session (out-of-scope rule).

## Files Modified

- `mud/world/movement.py` — `move_character`: `mp_exit_trigger` block relocated
  to the top (after `idx` lookup), before encumbrance + exit-existence gates;
  MOVE-005 comment citing ROM.
- `tests/integration/test_move005_exit_trigger_ordering.py` — new (2 RED→GREEN).
- `docs/parity/ACT_MOVE_C_AUDIT.md` — MOVE-005 row (FIXED) + MOVE-006 row (OPEN);
  corrected line-by-line items 2 & 3 (ordering note on the previously bare
  ✅ PARITY).
- `CHANGELOG.md` — Fixed entry under `[Unreleased]`.
- `pyproject.toml` — 2.12.80 → 2.12.81.

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
- _(this summary + SESSION_STATUS refresh)_ — docs(session).

## Next Steps

Mob-trigger ordering probe is largely exhausted (FIGHT/HPCNT/ACT/KILL/DEATH
enforced; EXIT closed; BRIBE/GIVE read clean). Candidate next passes:

1. **MOVE-006** — verify/remove the non-ROM encumbrance movement gate (small,
   self-contained; has an OPEN audit row ready).
2. **Highest-ceiling (multi-day):** `diff_harness` Hypothesis widening
   (`tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md`) — the only
   enumeration-independent path to *unknown* divergences.
3. **Housekeeping:** INV tracker consolidation (27 rows, past the ~20 soft cap).

> **Push note:** `origin/master` is at `6b2fbd2b` (2.12.80). This session's
> commits (`8681630c` + the docs follow-up, 2.12.81) are **unpushed**.
> CHANGELOG/version reflect 2.12.81.
