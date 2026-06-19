# Session Summary — 2026-06-19 — STEAL-015 (steal skill handler is_safe gate)

## Scope

Picked up from the completed INV-001 debt burndown (prior session, v2.14.128).
Per-file audit tracker is exhausted; cross-file / divergence-class sweep is the
active mode. From the open follow-ups in `SESSION_STATUS.md`, closed the
highest-yield genuine parity bug: **STEAL-015** — the `steal` *skill handler*
had no `is_safe` gate, a dual-entry-point hazard left open when the `do_steal`
*command* was gated (STEAL-003).

## Outcomes

### `STEAL-015` — ✅ FIXED (genuine parity bug)

- **Python**: `mud/skills/handlers.py:steal` (~7761)
- **ROM C**: `src/act_obj.c:2191-2192` (`if (is_safe(ch, victim)) return;`) →
  faithful mirror at `src/fight.c:1018-1124`
- **Gap**: STEAL-015 — the `steal` skill function (registered in
  `data/skills.json`, reachable via the skill system independently of the
  `do_steal` command) had a placeholder `# safety check (simplified - no is_safe
  implemented yet)` and **no gate at all**. A steal routed through the skill path
  could rob shopkeepers/healers/pets/safe-room mobs and bypass the PC clan PK
  ladder.
- **Fix**: converged the handler onto `combat._kill_safety_message` (the same
  faithful `is_safe` mirror `do_steal` uses, INV-050 surface) immediately after
  the self-steal check and before the kill-stealing check — exactly mirroring
  ROM `do_steal`'s L2191→L2194 order. A non-None return ends the steal with the
  is_safe context line surfaced in the result dict's `message`.
- **Block-set handled**: the parity tests call the handler directly and had
  setups that dodged the (previously absent) gate. Re-setup faithfully:
  NPC-victim tests given rooms (else the mirror returns "They aren't here." for a
  None room); PC-vs-PC tests (`test_steal_level_difference_too_high`,
  `test_steal_pc_to_pc_sets_thief_flag`) made clansmen within the PK ladder so
  `is_safe` *passes through* to each test's named ROM mechanic rather than
  short-circuiting it. `test_steal_level_difference_too_high` additionally
  asserts the rejection is NOT the is_safe line — guarding against a
  green-for-the-wrong-reason regression (it only asserted `success is False`,
  which a silent is_safe block would have satisfied).
- **Tests**: `tests/test_skill_steal_rom_parity.py` — 12/12 passing, incl. new
  `test_steal_from_safe_healer_blocked_via_skill_handler` (fail-firsted: healer
  was robbed `success=True` before the fix).
- **Commit**: `034910eb`, v2.14.129

## Files Modified

- `mud/skills/handlers.py` — `steal`: added is_safe gate via
  `combat._kill_safety_message` (with STEAL-015 why-comment)
- `tests/test_skill_steal_rom_parity.py` — new healer test; re-setup the
  existing block-set (rooms + clan) to preserve each test's named ROM mechanic
- `docs/parity/ACT_OBJ_C_AUDIT.md` — STEAL-015 row 🔄 OPEN → ✅ FIXED
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-050: STEAL-015 inline
  note updated + `handlers.py:steal` added to the "Touched by" trail
- `CHANGELOG.md` — Fixed entry (STEAL-015)
- `pyproject.toml` — 2.14.128 → 2.14.129

## Test Status

- `pytest tests/test_skill_steal_rom_parity.py tests/integration/test_steal_command.py
  tests/test_skills.py tests/test_spec_funs.py tests/test_combat_assist.py
  tests/integration/test_do_cast_pk_gates.py` — **121 passing**
- `ruff check` — clean
- `gitnexus_detect_changes` — low risk, scope = `steal` + test file + docs only
- Full suite not re-run this session (area suites green; change is localized to
  one handler + its dedicated test file)

## Next Steps

Remaining open follow-ups (from prior handoff, unchanged):
- **DELETE-002** — `do_delete` wiznet self-deletion broadcast
  (`mud/commands/player_config.py`, `src/act_comm.c:62`/`92`), documented in
  `ACT_COMM_C_AUDIT.md`.
- **INV-050 bool-retirement** — still GATED on the `is_safe_spell`-vs-ROM
  standalone audit (`src/fight.c:1126-1218`); player-facing message surfacing is
  now fully closed across bash/consider/cast/assist/steal *and* the steal skill
  path.
- `mud/entrypoint.py` dead code; the `do_yell` hand-rolled-XOR tidy-up.
- Higher-yield enumeration-independent lever per
  `docs/parity/DIVERGENCE_CLASS_ROSTER.md`: Hypothesis state-machine →
  diff_harness widening (Class 11 / Phase C).
