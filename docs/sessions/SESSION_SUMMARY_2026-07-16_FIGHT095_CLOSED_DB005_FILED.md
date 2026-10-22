# Session Summary — 2026-07-16 — FIGHT-095 closed (check_assist char_list domain) + DB-005 filed

## Scope

User-commissioned closure of **FIGHT-095** via `/rom-gap-closer` (the one open
actionable gap, previously de-risked and specced same-date). Executed the full
spec: extend the diff-harness with the missing primitives → author the
cross-room C-oracle scenario → RED → fix → converge. The closure's shared-RNG
draw-count forensics turned into a deep debugging arc that surfaced **two
collateral fixes** (FIGHT-096/097, prerequisites for golden convergence) and
**three durable filings**, headlined by **DB-005** — a HIGH reset-ordering
divergence in the boot engine found by exhaustive draw accounting against the
live C oracle.

## Outcomes

### FIGHT-095 — ✅ FIXED (2.14.322, commit `79d90e64`)

- **Python**: `mud/combat/assist.py` — inner reservoir now walks
  `_char_list_walk_from_room_head(ch)`: the reversed `character_registry` slice
  from the room-head's index (room head first → oldest), the INV-045/GROUP-006
  fix pattern, with a room-people fallback for unregistered synthetic fixtures.
- **ROM C**: `src/fight.c:161` — seeds at the room people head, follows the
  GLOBAL `char_list` (`->next`), so the domain is the room head plus every char
  created before it, world-wide. Faithful consequences now replicated: an
  assisting mob can reservoir-pick a same-group char in ANOTHER room (then whiff
  via `one_hit`'s room guard), and a same-room member created after the room
  head is unreachable.
- **C-oracle validation**: new differential scenario
  `check_assist_cross_room.json` converges with a freshly-captured ROM golden;
  an 8-seed `__rng_probe` alignment sweep (gate-skip / miss / dodge / parry /
  cross-room-pick variants) is byte-identical.
- **Tests**: `test_fight095_check_assist_char_list_domain.py` (3, red→green) +
  `test_differential_smoke.py[check_assist_cross_room]` (98th differential test).

### Collateral fixes (prerequisites for convergence, one commit each)

- **FIGHT-096 — ✅ FIXED (2.14.320, `41cf0c77`)**: the assist emote now renders
  via `act_format` (NPC short_descr, line-start cap, TO_CHAR self-line),
  mirroring `do_emote`. Surfaced by the first C capture (`The drunk` vs
  `the drunk`). 2 tests, mutation-relevant red→green.
- **FIGHT-097 — ✅ FIXED (2.14.321, `733a460b`)**: `attack_round` now carries
  ROM `one_hit`'s opening guards (self/None/dead/**cross-room** → return before
  any RNG draw). Load-bearing for the cross-room whiff. 3 tests incl. the
  zero-RNG-consumption assertion.

### DB-005 — ⚠️ FILED (OPEN, HIGH) — reset processing order diverges

- ROM `reset_area` iterates rooms in **ascending vnum order** (each room owns
  its reset list); Python applies resets in **.are file order**, so global
  M-reset limits bind in a different sequence. Shipped-data proof: `valley.are`
  mob 7803 — ROM spawns 3 (room 7853's limit-1 reset is skipped because 7848
  spawns first), Python spawns 4. Verified live via the new `__mob_census`
  directive. Boot **creation order** also diverges for multi-instance protos —
  a WORLD-level INV-045 exposure (cross-engine char_list pairings differ).
- Found by draw-count forensics: a 2-3 raw-draw stream desync traced through
  probe alignment → sneak-roll census diff → one extra sentry → the reset. The
  scenario neutralizes the contaminated population via observer DETECT_HIDDEN
  (orthogonal to the FIGHT-095 contract; golden survives the eventual DB-005 fix).
- Route: `/rom-gap-closer DB-005` — reset-engine change, world-wide blast
  radius, expects test/golden fallout triage. Filed in `DB_C_AUDIT.md`.

### Also filed

- **GL-050 (OPEN)** — `aggr_update` victim selection diverged with 2 PCs in the
  room (C mauled Tester, Python mauled Ally; repro preserved). Needs probe.
- **HANDLER-009 (OPEN, test-only)** — `MobInstance.move_to_room` appends to
  `room.people` (ROM head-inserts); production paths unaffected.
- **FIGHT-098 (OPEN)** — `mob_hit`'s OFF_AREA_ATTACK sweep is the sibling
  global-walk quirk; fix pattern now proven by FIGHT-095.

### Harness infrastructure (in the FIGHT-095 commit)

Six new directives, C shim + pyreplay with identical semantics, all documented
in `tools/diff_harness/README.md`: `__char_goto`, `__mob_off_flags`,
`__mob_add_affect`, `__rng_probe` (stream-alignment discriminator),
`__sneak_census`, `__mob_census` (population forensics).

## Files Modified

- `mud/combat/assist.py` — reservoir domain + `_emote` render + walk helper.
- `mud/combat/engine.py` — `attack_round` one_hit guards.
- `src/diff_shim/diffmain.c`, `tools/diff_harness/pyreplay.py`, `README.md` —
  six directives.
- `tools/diff_harness/scenarios/check_assist_cross_room.json` +
  `tests/data/golden/diff/check_assist_cross_room.golden.json` — new scenario.
- Tests: `test_fight095_*` (3), `test_fight096_*` (2), `test_fight097_*` (3).
- Docs: FIGHT_C_AUDIT (095✅/096✅/097✅/098 filed), DB_C_AUDIT (DB-005),
  UPDATE_C_AUDIT (GL-050), HANDLER_C_AUDIT (HANDLER-009),
  CROSS_FILE_INVARIANTS_TRACKER (INV-045 conformed + DB-005 caveat),
  DIVERGENCE_CLASS_ROSTER, CHANGELOG.
- `pyproject.toml` — 2.14.319 → 2.14.322 (three patch bumps).

## Test Status

- Differential harness: **98/98** (65 scenarios — +1 new) convergent.
- Assist suites 29/29; combat/fight area 334/334.
- Full suite: **6218 passed, 4 skipped, 0 failed** (487s, clean complete run;
  +9 = the new tests). Note: one run crashed mid-flight with a TWO-worker xdist
  death + scheduler `KeyError: gw11` (reported a truncated "6162 passed" with
  exit 0 — trust only complete runs; count UP against the expected total, not
  just zero-down on failures).

## Policy note

Commit-locally-only (no push, no PyPI). Session commits: `41cf0c77` (096),
`733a460b` (097), `79d90e64` (095 + filings). Operator reviews and pushes.

## Next Steps

- **DB-005** is the standout next task (HIGH, world-population + boot-order
  parity; exact repro + fix direction recorded; expect test-fallout triage).
- FIGHT-098 (sibling walk, pattern proven), GL-050 (aggr probe), HANDLER-009
  (trivial), then carry-overs (FIGHT-094, DESC-001, OLC lookup, IS_BUILDER,
  stray SQLite files).
