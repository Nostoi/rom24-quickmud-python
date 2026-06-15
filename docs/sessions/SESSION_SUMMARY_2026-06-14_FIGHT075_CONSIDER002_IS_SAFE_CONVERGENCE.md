# Session Summary — 2026-06-14 — do_bash `$M` render + is_safe convergence (FIGHT-075 / CONSIDER-002 / CAST-012 / FIGHT-076)

## Scope

Picked up from the FIGHT-068/072/073 entry-gate session. The `fight.c`
offensive-skill entry-gate **ordering/message** sweep was exhausted except for
one spin-off (FIGHT-075). Closed it, then moved to the next-higher lever named
in the status doc — **INV-050** (converging the silent-bool `is_safe` callers
onto the faithful message-mirror `_kill_safety_message`) — and converged the
**second** (`do_consider`, CONSIDER-002), **third** (`do_cast`
`TAR_CHAR_OFFENSIVE`, CAST-012), and **fourth** (`check_assist`, FIGHT-076)
callers. One gap = one test = one commit (do_bash was the first caller,
converged last session under FIGHT-070). Also ROM-corrected one standing
pre-existing red test (do_kill charm gate) surfaced by the assist fallout run.

## Outcomes

### `FIGHT-075` — ✅ FIXED (2.14.108)

- **Python**: `mud/commands/combat.py:do_bash` (~combat.py:446)
- **ROM C**: `src/fight.c:2394`
- **Gap**: `do_bash`'s position-gate message was the literal "You'll have to let
  **them** get back up first." where ROM renders
  `act("You'll have to let $M get back up first.", ch, NULL, victim, TO_CHAR)`
  — `$M` = victim objective pronoun (him/her/it). Wrong pronoun render.
- **Fix**: `act_format("You'll have to let $M get back up first.",
  recipient=char, actor=char, arg2=victim)`. Same act()-render class as
  FIGHT-073/TRIP-001/FIGHT-064.
- **Tests**: 1 — `tests/integration/test_fight075_bash_position_pronoun_message.py`
  (male sitting victim → "him", not "them"). Verified red before, green after.

### `CONSIDER-002` — ✅ FIXED (2.14.109, INV-050 second caller)

- **Python**: `mud/commands/consider.py:do_consider` (~consider.py:43)
- **ROM C**: `src/act_info.c:2490-2493` + `src/fight.c:1018-1124`
- **Gap**: ROM `do_consider` runs `if (is_safe(ch,victim)) {
  send_to_char("Don't even think about it."); return; }`, and ROM `is_safe`
  writes its **own** rejection line via `send_to_char`/`act` *before* returning
  TRUE (e.g. "The shopkeeper wouldn't like that.", "I don't think Mota would
  approve."). So a blocked `consider` shows **two** lines. Python routed through
  the silent bool `combat.safety.is_safe` (writes no message) and printed only
  "Don't even think about it." — dropping ROM's context line.
- **Fix**: converged the gate onto the faithful mirror
  `combat._kill_safety_message` (the do_bash FIGHT-070 pattern). A non-None
  return == ROM `is_safe` returning TRUE; emit `f"{safety_message}\nDon't even
  think about it."`. Swapped the `from mud.combat.safety import is_safe` import
  for `from mud.commands.combat import _kill_safety_message` (no circular import
  — combat.py does not import consider.py).
- **Tests**: 1 — `tests/integration/test_consider002_safe_target_context_message.py`
  (healer victim → "...Mota would approve." + "Don't even think about it.").
  Verified red before, green after. All 18 do_consider tests pass (the pre-existing
  15 + CONSIDER-001's 2 + this one).

### `CAST-012` — ✅ FIXED (2.14.110, INV-050 third caller)

- **Python**: `mud/commands/combat.py:do_cast` (~combat.py:1016)
- **ROM C**: `src/magic.c:398-402` + `src/fight.c:1018-1124`
- **Gap**: ROM `do_cast`'s `TAR_CHAR_OFFENSIVE` gate runs
  `if (is_safe(ch,victim) && victim != ch) { send_to_char("Not on that
  target."); return; }`, and ROM `is_safe` writes its own rejection line before
  returning TRUE — two lines. CAST-007 wired the gate through the **silent bool**
  `combat.safety.is_safe`, surfacing only "Not on that target." and inheriting
  the bool's bidirectional over/under-block.
- **Fix**: converged the `TAR_CHAR_OFFENSIVE` ("victim") branch onto
  `_kill_safety_message` → `f"{safety_message}\nNot on that target."`. The
  `TAR_OBJ_CHAR_OFF` branch uses `is_safe_spell`, which is **silent in ROM**
  (`src/fight.c:1126-1218`) — correctly left as a bare override. Removed the
  now-unused `is_safe` import.
- **Block-set correction fallout (advisor-predicted)**: converging to the
  faithful mirror also corrects *which* casts block. Two CAST-007 tests asserted
  the silent-bool **under-block** — KILLER-flag set / charm stripped when casting
  at a **non-clan PC victim**, which ROM `is_safe` blocks at `!is_clan(victim)`
  *before* `check_killer` runs (`src/fight.c:1112`). Per AGENTS.md (a test
  contradicting ROM is the bug), both were ROM-corrected to a **clan victim
  within 8 levels** — the only PC-victim case ROM lets through to `check_killer`.
  A third test (`..._blocked_in_safe_room`) was passing for the wrong reason (PC
  victim blocked by the clan ladder, not ROOM_SAFE which ROM only checks for NPC
  victims); switched its victim to an NPC so it genuinely exercises ROOM_SAFE.
- **Tests**: 1 new (`TestCastOffensiveIsSafeContextMessage`) + 3 ROM-corrected.
  Full `test_do_cast_pk_gates.py` 18/18; verified red before, green after.

### `FIGHT-076` — ✅ FIXED (2.14.111, INV-050 fourth caller)

- **Python**: `mud/combat/assist.py:check_assist` (~assist.py:84)
- **ROM C**: `src/fight.c:131` + `src/fight.c:1018-1124`
- **Gap**: ROM `check_assist` gates the PC/charmed auto-assist on
  `is_same_group(ch,rch) && !is_safe(rch, victim)`. ROM `is_safe(rch, victim)`
  writes its own rejection line to **rch** (the autoassister) before returning
  TRUE. Python routed through the **silent bool**, which (a) wrote no message and
  (b) lacks the PC-vs-PC clan ladder — so a **non-clan PC group member wrongly
  auto-assisted in PvP**, silently.
- **Fix**: converged onto `_kill_safety_message(rch, victim)` — `None` → rch
  assists; a non-None string → rch is blocked and sees the line via the module's
  `_send_to_char`. Function-local import avoids an engine→command cycle. Removed
  the now-unused module-level `is_safe` import (two `test_fight060` tests
  monkeypatched it defensively though the NPC-assist branch never calls it —
  vestigial lines removed). Charmed-mob `rch` `send_to_char` no-ops (NPC, no
  descriptor), so only PC autoassisters observe the line.
- **Tests**: 1 new
  (`test_combat_assist.py::TestPlayerAutoAssist::test_autoassist_blocked_by_is_safe_clan_ladder`);
  red before, green after. Full assist/group slice 93 passed, 1 skipped.

### Pre-existing failure ROM-corrected (separate commit, NOT caused this session)

- **`test_combat.py::test_kill_blocks_charmed_player_attacking_master`** — a
  standing red test (failing since before this session's start commit
  `1b641732`, confirmed by bisect). It asserted the do_kill "beloved master"
  charm gate fires for a charmed PC attacking a **PC** master, but ROM do_kill
  (`src/fight.c:2793`) runs `is_safe` **before** the charm gate (`:2803`), and
  `is_safe` blocks a non-clan PC attacking any PC at "Join a clan if you want to
  kill players." The code was already ROM-correct (the faithful
  `_kill_safety_message` has had the PC clan ladder since FIGHT-074). Per AGENTS.md
  (a test contradicting ROM is the bug), ROM-corrected the test to an **NPC
  master** (mirroring the FIGHT-064 sibling), which passes is_safe so the charm
  gate is the observable result. Committed separately as `test(parity)`.

## Files Modified

- `mud/commands/combat.py` — `do_bash` position-gate message → `act_format` `$M`;
  `do_cast` `TAR_CHAR_OFFENSIVE` gate → `_kill_safety_message`; removed unused
  `is_safe` import.
- `mud/commands/consider.py` — `do_consider` safety gate → `_kill_safety_message`.
- `tests/integration/test_do_cast_pk_gates.py` — new context-line test class + 3
  ROM-corrected tests (clan victim / NPC ROOM_SAFE victim); `ActFlag` import.
- `docs/parity/MAGIC_C_AUDIT.md` — added CAST-012 ✅ FIXED row.
- `tests/integration/test_fight075_bash_position_pronoun_message.py` — new (1 test).
- `tests/integration/test_consider002_safe_target_context_message.py` — new (1 test).
- `docs/parity/FIGHT_C_AUDIT.md` — flipped FIGHT-075 → ✅ FIXED.
- `docs/parity/ACT_INFO_C_AUDIT.md` — added CONSIDER-002 ✅ FIXED to the do_consider row.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-050: removed consider +
  do_cast from "still open", added both to "Touched by", added the two new
  enforcement tests, refreshed status (do_bash + do_consider + do_cast converged;
  ~5 callers remain).
- `docs/parity/MAGIC_C_AUDIT.md` — added CAST-012 ✅ FIXED row.
- `mud/combat/assist.py` — `check_assist` PC autoassist gate → `_kill_safety_message`;
  removed unused `is_safe` import.
- `tests/test_combat_assist.py` — new clan-ladder block test.
- `tests/integration/test_fight060_check_assist_elif_chain.py` — removed vestigial
  `is_safe` monkeypatches (NPC-assist branch never calls it).
- `tests/test_combat.py` — ROM-corrected the stale do_kill charm-gate test (NPC master).
- `docs/parity/FIGHT_C_AUDIT.md` — added FIGHT-076 ✅ FIXED row.
- `CHANGELOG.md` — added 2.14.108 / 2.14.109 / 2.14.110 / 2.14.111 sections.
- `pyproject.toml` — 2.14.107 → 2.14.111.

## Test Status

- `pytest -n0 test_fight075_…` / `test_consider002_…` / `…IsSafeContextMessage` — 3/3 (each red before its fix).
- `pytest tests/integration/test_do_consider_command.py` — 17/17 (15 existing + CONSIDER-001×2, all still green after convergence).
- `pytest tests/integration/test_do_cast_pk_gates.py` — 18/18 (new context-line test + 3 ROM-corrected block-set tests).
- `pytest tests/integration/ -k "cast or spell or magic or safe or pk"` — 454 passed.
- `pytest tests/integration/ -k "consider or safe or kill or murder"` — 152 passed, 1 skipped.
- Cast unit files (`test_skill_combat_rom_parity` + 3 others) — 167 passed.
- `pytest -k "assist or group or check_assist"` — 93 passed, 1 skipped (FIGHT-076).
- `pytest tests/test_combat.py tests/test_combat_assist.py` — 50 passed (incl. the ROM-corrected do_kill test).
- Diff-harness smoke (`test_differential_smoke` + `test_diff_harness_unit`) — 67 passed (check_assist is on the combat-tick path).
- `python3 test_all_commands.py` — 1 pre-existing attribute error (confirmed present in stashed baseline; not introduced this session).
- `ruff check .` — clean. Pre-commit hooks all passed.
- GitNexus `impact` on `do_bash` / `do_consider` / `do_cast` — LOW risk, 0 affected processes. `detect_changes` scope confined to the three functions + docs. Index reindexed after each commit.

## Next Steps

- **INV-050 remaining callers** (the active lever): converge the rest of the
  silent-bool `is_safe` callers onto `_kill_safety_message` —
  `spec_funs.py:1341,1382`, `commands/thief_skills.py:132`, and
  `combat/engine.py:671-674` (apply_damage re-check — FIGHT-002, **intentionally**
  silent; confirm against `src/fight.c:725-733` — likely leave as-is). Each needs
  its ROM C call-site read first. **Watch for block-set fallout** like CAST-012 /
  FIGHT-076: converging corrects *which* targets block, not just the message, so
  existing tests asserting the silent-bool's over/under-block must be ROM-corrected
  (cite ROM C — the assist run also surfaced a *pre-existing* do_kill test
  asserting the same divergence). ⚠️ PARTIAL in `CROSS_FILE_INVARIANTS_TRACKER.md`.
  Ultimate goal: collapse all callers onto the mirror and retire the bool (or make
  it a thin wrapper) — eliminating its bidirectional over/under-block.
- Beyond INV-050, per `docs/parity/DIVERGENCE_CLASS_ROSTER.md` the higher-yield
  open lever remains the **Hypothesis state-machine → diff_harness widening**
  (Class 11 / Phase C), enumeration-independent (guardrail 3).
