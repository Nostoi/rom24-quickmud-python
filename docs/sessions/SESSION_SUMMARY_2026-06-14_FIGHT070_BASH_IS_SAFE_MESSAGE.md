# Session Summary — 2026-06-14 — fight.c do_bash is_safe message-surfacing (FIGHT-070, INV-050)

## Scope

Continued the cross-file / category-error / borrowed-gate divergence sweep in
the `fight.c` offensive-skill **entry gates**, picking up directly from FIGHT-074
(the kill/dirt/trip charm-order trio). FIGHT-070 was the highest-leverage open
row: `do_bash`'s entry gate called the **silent** bool
`mud/combat/safety.py:is_safe` and `return ""`, so the skill was correctly gated
(FIGHT-067) but the player saw **nothing** — where ROM's `is_safe`
(`src/fight.c:1018-1124`) writes a *specific* reason line via `send_to_char`/`act`
**before** returning TRUE, and `do_bash` (`src/fight.c:2405-2406`) relies on that
side-effect (`if (is_safe(ch,victim)) return;`).

Method: read ROM `is_safe` (1018-1124) and `do_bash` (2380-2419) top-to-bottom;
confirmed Python had **split** ROM's single function into two divergent objects —
a silent bool (`safety.py:is_safe`) and a faithful message-mirror
(`combat.py:_kill_safety_message`, made a pure is_safe() mirror by FIGHT-074).
Wrote one failing test (verified red), routed `do_bash` onto the faithful mirror,
then re-ran the full bash surface — which surfaced one pre-existing test riding
the silent bool's *under-blocking* (fixed in the test, per AGENTS.md).

## Outcomes

### `FIGHT-070` — ✅ FIXED (v2.14.104)

- **Python**: `mud/commands/combat.py:do_bash` (entry gate, ~combat.py:463)
- **ROM C**: `src/fight.c:1018-1124` (is_safe) + `src/fight.c:2405-2406` (do_bash gate)
- **Gap**: `do_bash` called the silent bool `mud/combat/safety.py:is_safe` and
  `return ""` on a block, so bashing (e.g.) an NPC in a ROOM_SAFE room aborted the
  skill but printed nothing. ROM's is_safe emits a context line — "Not in this
  room." (ROOM_SAFE, `:1034`), "The shopkeeper wouldn't like that." (`:1040`),
  "But $N looks so cute and cuddly…" (pet, `:1061`), the clan-PK ladder lines —
  before returning TRUE, and do_bash returns on that side-effect.
- **Root cause (split-helper shape)**: ROM's `is_safe()` fuses a *decision* (bool)
  with a *side-effect* (the message). The Python port split it into a silent bool
  (`safety.py:is_safe`) and a message-returning mirror (`_kill_safety_message`).
  `do_bash` was wired to the silent half, dropping the side-effect. The silent
  bool is additionally **bidirectionally divergent** from ROM is_safe — it
  over-blocks (`is_ghost`, `ActFlag.GAIN` — neither in ROM is_safe; checks
  ROOM_SAFE for ALL victims where ROM checks it only for NPC victims/NPC
  attackers) and under-blocks (MISSING the immortal bypass, the
  victim-fighting-back bypass, and the ENTIRE PC-vs-PC clan PK ladder).
- **Fix (2.14.104)**: routed `do_bash`'s entry gate through
  `_kill_safety_message` — the faithful ROM is_safe() mirror — instead of the
  silent bool. The mirror emits ROM's reason string AND corrects which cases
  block. `do_bash` is the **first** offensive-verb gate converged onto the
  faithful mirror; the kill-steal block and charm gate after it are unchanged.
- **Tests**: 1 new — `tests/integration/test_fight070_bash_is_safe_message.py`
  (bashing an NPC in a ROOM_SAFE room → `do_bash` returns "Not in this room.").
  Verified **red** (`'' != 'Not in this room.'`) before the fix, green after.
  One pre-existing test repaired (see below).

### `INV-050` — FILED (⚠️ PARTIAL)

- **Tracker**: `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`
- **Name**: IS-SAFE-BOOL-BIDIRECTIONAL-DIVERGENCE.
- **Contract**: ROM has ONE `is_safe(ch, victim)` (decision + message fused). The
  Python port split it into a silent bool (`safety.py:is_safe`, bidirectionally
  divergent from ROM) and a faithful message-mirror
  (`combat.py:_kill_safety_message`). Convergence plan: route every offensive-verb
  entry gate onto the message-mirror; ultimately retire the bool or make it a thin
  wrapper.
- **Status**: ⚠️ PARTIAL — `do_bash` converged (2.14.104). The silent bool still
  serves ~8 other callers (`spec_funs.py:1341,1382`, `combat/assist.py:84`,
  `combat/engine.py:671-674` apply_damage re-check, `commands/consider.py:43`,
  `commands/thief_skills.py:132`, `combat.py:do_cast` ~1003) with its divergence.
  Full convergence is the remaining scope.

### Pre-existing test repaired

- `tests/test_skill_combat_rom_parity.py::TestBashRomParity::test_bash_pc_dodge_penalty_applied`
  set up two **non-clan PCs** and expected `do_bash` to proceed — it was riding
  the silent bool's *under-blocking* (no PC-vs-PC clan ladder). Under the faithful
  mirror those two PCs correctly trip ROM's "Join a clan if you want to kill
  players." gate (`src/fight.c:1096-1120`). The test's *intent* is the dodge
  penalty math (it needs both combatants to be PCs for STR/DEX flooring), so its
  setup now gives both `clan = 1` (level diff 0 ≤ 8) to clear ROM's clan gate.
  Per AGENTS.md: a test asserting behavior that contradicts ROM C is a test bug.

## Files Modified

- `mud/commands/combat.py` — `do_bash` entry gate routed through
  `_kill_safety_message` (was the silent bool `is_safe` → `return ""`).
- `tests/integration/test_fight070_bash_is_safe_message.py` — new (1 test).
- `tests/test_skill_combat_rom_parity.py` — `test_bash_pc_dodge_penalty_applied`
  setup gives both combatants `clan = 1` to clear ROM's PC-vs-PC clan gate.
- `docs/parity/FIGHT_C_AUDIT.md` — flipped FIGHT-070 → ✅ FIXED.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — added INV-050 (⚠️ PARTIAL).
- `CHANGELOG.md` — added the 2.14.104 (FIGHT-070) section.
- `pyproject.toml` — 2.14.103 → 2.14.104.

## Test Status

- `pytest -n0 tests/integration/test_fight070_bash_is_safe_message.py
  tests/integration/test_fight067_bash_safe_room_entry_gate.py` — 2/2.
- `pytest -k bash` — 34 passed (the dodge-penalty repair landed here).
- `pytest tests/integration/ -k "bash or fight or dirt or trip or kill"` —
  295 passed, 1 skipped.
- `ruff check .` — clean. Pre-commit hooks (ruff, ruff-format, equipment-key,
  char.inventory) all passed (ruff-format restyled the new test once).
- GitNexus `detect_changes` (scope: all) — confined to `do_bash` + the two test
  files + the four doc sections, 0 affected processes, LOW risk. Reindex kicked
  off post-push (index was stale at 4f7d3d8).

## Outstanding (open fight.c rows — for the next agent)

- **`INV-050`** — converge the remaining ~8 silent-bool `is_safe` callers onto the
  faithful message-mirror (or retire the bool). do_bash is done; the bigger scope
  (spec_funs, assist, apply_damage re-check, consider, thief_skills, do_cast)
  remains. The apply_damage re-check (`combat/engine.py:671-674`) is the
  subtle one — it's the FIGHT-002 silent-suppression port and is *intended* to be
  silent mid-combat, so converging it needs care (ROM's damage()/is_safe at
  `src/fight.c:725-733` re-checks silently — confirm before changing).
- **`FIGHT-068`** — do_bash `victim==ch`/position order swap: Python checks
  `victim==ch` (combat.py:443) BEFORE position (446); ROM checks position FIRST
  (`src/fight.c:2392` before `:2399`). MINOR ordering.
- **`FIGHT-072` / `FIGHT-073`** — do_dirt `victim==ch`-before-BLIND order swap +
  BLIND `$E` pronoun message ("They're already blinded." vs ROM
  `act("$E's already been blinded.")`). MINOR, act()-render class.

## Next Steps

The split-helper convergence is now started for the offensive-verb family
(do_bash first). Natural continuations: extend INV-050 convergence to the other
offensive verbs' gates (do_dirt/do_trip already route the is_safe-message half
through `_kill_safety_message`; the bare-bool callers are the remaining work),
then the MINOR ordering pair FIGHT-068 / FIGHT-072 / FIGHT-073. Beyond the
fight.c offensive-skill family, per `docs/parity/DIVERGENCE_CLASS_ROSTER.md` the
higher-yield open lever remains the **Hypothesis state-machine → diff_harness
widening** (Class 11 / Phase C), enumeration-independent (guardrail 3).
