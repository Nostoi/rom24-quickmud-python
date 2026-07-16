# Session Summary — 2026-07-16 — Extract-cleanup matrix divergence sweep (INV-020/047 pet+raw_kill legs, FIGHT-095)

## Scope

Continuation session in **cross-file-invariants / divergence-class probe** mode
(per-file audit tracker at 100%, documented backlog drained). Ran a multi-probe
divergence sweep, entered via `/rom-divergence-sweep`, focused on the
**split-extract-funnel** class — the highest-yield structural-divergence vein in
this port (ROM has one `extract_char`; the Python port split extraction across
call sites, so each cleanup step must be re-wired per leg or it silently
dangles). Built the **extract-cleanup matrix** (legs × steps) and hunted for
"cells the tracker prose claims but no test exercises." Also validated the
enumeration-independent differential harness and swept several adjacent lifecycle
surfaces. Net: **2 real gaps closed, 1 real finding filed, 5 clean probes.**

## Outcomes

### INV-020 (pet leg) — ✅ FIXED

- **Python**: `mud/combat/death.py:_nuke_pets`
- **ROM C**: `src/act_comm.c:1640-1654` (`nuke_pets` → `extract_char(pet, TRUE)`),
  `src/handler.c:2120-2122` (`die_follower`), `src/handler.c:2151-2157` (ref sweep)
- **Gap**: `_nuke_pets` inlined a *partial* pet-extraction (stop_follower + fade +
  object-drain + stop_fighting + registry removal) that omitted `die_follower(pet)`
  and `clear_extract_target_refs(pet)`. A doc-vs-code divergence *inside INV-020's
  own stated contract* (step (i) claims `nuke_pets → extract_char(pet, TRUE)`, the
  full chain). A character following the pet (`master == pet`) — or holding a
  `reply` at it — dangled at the extracted pet corpse when the owner died.
- **Fix**: `_nuke_pets` now runs `die_follower(pet)` + `clear_extract_target_refs(pet)`
  before `stop_fighting(pet)`, mirroring `extract_char(pet, TRUE)`.
- **Tests**: `tests/integration/test_inv020_nuke_pets_full_pet_extraction.py`
  (2 — die_follower leg + reply-sweep leg). Red before, green after. INV-020/047
  suites (22 tests) regression-clean.

### INV-047 (raw_kill leg) — ✅ FIXED

- **Python**: `mud/combat/death.py:raw_kill` (NPC leg)
- **ROM C**: `src/fight.c:1695-1723` (`raw_kill` → `extract_char(victim, IS_NPC)`),
  `src/handler.c:2151-2157` (char_list reply/mprog_target sweep, after the
  `if (!fPull) return` early-out at `:2136`)
- **Gap**: INV-047's `clear_extract_target_refs` was wired into the mob-purge,
  link-dead-quit, and socket legs — but **not** `raw_kill`, the primary
  combat-death funnel. A mob slain in combat while a character held a `reply` at
  it (a mob's `mob tell` sets the player's `reply`) — or an `mprog_target` —
  left a dangling reference at the extracted corpse. Found via the extract-cleanup
  matrix; same signature as the pet-leg gap.
- **Fix**: `raw_kill`'s NPC leg now runs `clear_extract_target_refs(victim)`, gated
  on `is_npc` to match ROM's fPull=TRUE (a PC death, fPull=FALSE, returns early and
  correctly skips the sweep — the PC stays live).
- **Tests**: `tests/integration/test_inv047_raw_kill_clears_refs.py` (2 — reply
  sweep + mprog_target quirk). Red before, green after. INV-047 suite (10 tests)
  clean; focused death/extract/combat regression (960 tests) clean.

### FIGHT-095 — ⚠️ FILED (OPEN, needs C-oracle validation before fixing)

- **Python**: `mud/combat/assist.py:164` (inner target-selection loop)
- **ROM C**: `src/fight.c:161` — `for (vch = ch->in_room->people; vch; vch = vch->next)`
- **Finding**: ROM's `check_assist` NPC-assist target-selection loop seeds from the
  room people-list *head* but follows the **global `char_list`** (`->next`), not
  `->next_in_room` (a 2.4b6 quirk — contrast the outer loop at `:111` and
  `group_gain` at `:1746/1764`, both room-scoped). Python iterates room-scoped
  `people_in_room`. Two facets: (1) target selection can pick/miss cross-room
  same-group members; (2) the `number_range(0, number)` reservoir draw count
  differs → shared combat MM RNG desync. FIGHT-053 fixed `number++`'s position in
  this loop but left the iteration *domain* room-scoped, so the domain quirk is
  genuinely un-addressed.
- **Why not fixed here**: a faithful fix changes RNG draw counts and must be
  validated against the live C oracle via a diff-harness scenario (AGENTS.md:
  subtle RNG quirk → file and probe, don't fix blind). Likely LOW severity.
- **Route**: `/rom-gap-closer FIGHT-095` after authoring a check_assist C-oracle
  scenario with a cross-room group member.

### Clean probes (convergent — recorded, no change)

1. **`obj_update` decay lifecycle** (class 10) — `src/update.c:913-1056` vs
   `mud/game_loop.py:obj_update`: shopkeeper `cost/5` recovery, pit-gate
   suppression (GL-018), WEAR_FLOAT `TO_ROOM` echo, all 5 spill branches, and the
   RNG-order-preserving unconditional `number_range(0,4)` affect-fade draw with
   reversed `object_registry` iteration (GL-040/045) all present + cited; 183
   decay/corpse tests green. Roster note added.
2. **Position transitions** — `update_pos` (`src/fight.c:1380`) + the `damage()`
   position-message switch (`:834-869`): faithful, correct ordering, `c_div`
   signed-math (ARITH-208). NPC-dies-at-0 / PC-stunned-at-0 asymmetry correct.
3. **Voluntary `do_quit` leg** — routes `_quit_requested` → `_disconnect_extract`
   → `_disconnect_extract_cleanup`, running the full extract chain, matching ROM
   `do_quit`'s `extract_char(ch, TRUE)`. Completes the extract-cleanup matrix.
4. **`char_update` affect decay** — `mud/affects/engine.py:tick_spell_effects` is
   a faithful twin of the object affect decay: unconditional `number_range(0,4)`
   draw (GL-026), emit-once gate, `msg_off` delivery, INV-015 `affect_remove`
   stat-unwind.
5. **`xp_compute` signed math** (Layer B) — `mud/groups/xp.py:xp_compute`: every
   signed-math site uses `c_div`, including the alignment `else` branch (line 189)
   where `gch_alignment * base_exp` can be negative (ARITH-005–008).

### Enumeration-independent verification (differential harness)

- Built the instrumented C binary (`make -C src -f Makefile.diffshim diffshim`,
  gcc — clean) and ran the full **Python-vs-committed-C-golden** replay:
  `tests/test_differential_smoke.py` + `tests/test_diff_harness_unit.py` = **97
  tests across 64 scenarios, zero divergence.** The only enumeration-independent
  parity check is clean on the covered surface.
- **Caveat (not a parity finding, recorded in the roster):** `capture --check`
  (C-oracle re-capture vs golden) reports CHANGED on ~20 RNG-adjacent scenarios
  (mob-trigger/shop/combat) while deterministic ones stay `ok` — a build/provenance
  discrepancy of the freshly-rebuilt C binary vs the committed goldens, NOT a
  Python↔ROM divergence (Python matches the committed C ground truth). Goldens were
  NOT overwritten (harness rule).

## Files Modified

- `mud/combat/death.py` — `_nuke_pets` runs full pet-extract cleanup; `raw_kill`
  NPC leg clears reply/mprog_target refs.
- `tests/integration/test_inv020_nuke_pets_full_pet_extraction.py` — new (2 tests).
- `tests/integration/test_inv047_raw_kill_clears_refs.py` — new (2 tests).
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-020 (pet leg) + INV-047
  (raw_kill leg) implementation/test cells updated.
- `docs/parity/FIGHT_C_AUDIT.md` — filed FIGHT-095 (OPEN).
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — class-10 obj_update clean-probe note;
  Layer-C differential-harness convergence + `--check` provenance caveat.
- `CHANGELOG.md` — 2 Fixed entries (pet leg, raw_kill leg).
- `pyproject.toml` — 2.14.315 → 2.14.317 (two patch bumps).

## Test Status

- `tests/integration/test_inv020_*` + `test_inv047_*` — 22/22 + 10/10 passing.
- Focused death/extract/combat regression — 960 passed, 2 skipped.
- Differential harness — 97/97 (64 scenarios) convergent.
- Full suite: **6208 passed, 4 skipped, 0 failed** (260s, clean parallel run).
  +4 vs prior session's 6204 (the 4 new regression tests). Note: a first parallel
  run hit the documented xdist `sessionfinish` teardown flake (a `gw5` worker-death
  artifact at 99%, AGENTS.md-known/harmless); the clean re-run confirmed 0 failures.

## Policy note

This session ran under a **commit-locally-only** directive (no push, no PyPI
publish) for the autonomous multi-iteration loop. The 5 commits are local on
`master`; the operator will review and push/publish manually.

## Next Steps

- **FIGHT-095** — author a `check_assist` diff-harness C-oracle scenario (cross-room
  group member) and close via `/rom-gap-closer FIGHT-095`, validating the RNG-draw-count
  facet against the live C oracle. This is the one open, actionable gap from this session.
- Continue the divergence-class sweep on un-probed surfaces if desired, but the
  split-extract-funnel vein (the reliable source of real gaps this session) is now
  exhausted on all enumerated legs × steps — expect further probes to be mostly
  clean, matching this session's obj_update / position / xp_compute results.
- Carry-over (unchanged from prior session): FIGHT-094 (OPEN — `check_killer`
  placement), DESC-001, OLC spell-name lookup, IS_BUILDER, and the stray
  `data/quickmud.db` (0 bytes) / `doc/game.db` (stale) cleanup pending confirmation.
