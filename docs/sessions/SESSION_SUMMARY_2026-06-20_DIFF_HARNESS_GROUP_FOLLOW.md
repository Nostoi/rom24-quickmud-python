# Session Summary — 2026-06-20 — Differential harness: group/follow + GROUP-006

## What landed

Continued the differential-harness widening pass (the only enumeration-
*independent* parity oracle now that the per-file audit tracker is drained).
Authored the **`group_follow_cycle`** scenario on the previously zero-coverage
group/follow surface. Unlike the prior session's three clean negatives, this one
**surfaced a real engine divergence** (FINDING-037 → GROUP-006) plus two
harness-setup parity gaps, all fixed this session.

### Engine fix — GROUP-006 (FINDING-037), the first observable INV-045 re-open

- **Bug:** `do_group`'s no-arg roster listed members **oldest-first**. ROM
  head-inserts every char into `char_list` (`src/db.c:2256`, `src/nanny.c`), so
  `do_group` (`src/act_comm.c:1787`) walks it **newest-first** → the roster is
  reverse-creation order. Python iterated `character_registry` forward
  (append-order), so a charmed mob (created after the PC) listed *below* the PC.
- **Why it slipped through:** GROUP-003 explicitly **deferred** the ordering
  ("Order was not the reported divergence"). INV-045 catalogued `do_group` as a
  "lower-stakes forward walk … acceptable residual; re-open … if observable to a
  scenario/golden." The scenario made it observable — the documented trigger.
- **Fix:** `mud/commands/group_commands.py:do_group` → `reversed(character_registry)`.
- **Guards:** `tests/integration/test_group_006_listing_order.py` (C-binary-
  independent; verified red→green by temporarily reverting the fix) +
  `group_follow_cycle` differential replay.

### Two harness-setup parity fixes (not engine bugs)

Both surfaced while isolating the order divergence; mirror the C shim's
`make_test_char` / meta-command contracts in `tools/diff_harness/pyreplay.py`:

1. **PC exp init** — `make_test_char` (diffmain.c:496) sets
   `ch->exp = exp_per_level(ch, points)` = 1000 for the default human mage;
   `create_test_character` left it 0, invisible until a `group`/`score` line
   prints `%5d xp`. pyreplay now mirrors it via `exp_per_level(char)`.
2. **`__charm_mob` output leak** — Python's handler calls `add_follower(mob, char)`
   which delivers "X now follows you." to the master (real game behavior). The C
   shim's `__charm_mob` `continue;`s *without* `emit_output`, so that buffered
   line is discarded. pyreplay now `char.messages.clear()`s after the charm to
   keep the meta output-silent on both sides.

Also discovered (and worked around with an `__seed` bracket, the standard
technique) that **world-boot RNG consumption is not bit-matched** between the C
and Python engines — the sailor's spawn-wealth roll was off-by-one until a
`__seed=4321` reset before `__mload` (mirroring `mob_give_trigger`). This is the
known reason every RNG scenario reseeds; not a new finding.

## Scenario shape (`group_follow_cycle`)

`__seed=4321` → `__mload=3007` (sailor) → `look` → `group` (single member) →
`follow sailor` (master set) → `group sailor` ("following someone else") →
`follow Tester` (stop_follower) → `__charm_mob=24` (sailor joins group) →
`group` (**two members — the order finding**) → `group sailor` (charm-protect).

## Status

- Version **2.14.201 → 2.14.202**.
- **45** committed differential scenarios, all converge; `KNOWN_DIVERGENCES` empty.
- Impact (`do_group`): LOW, 0 affected processes (only `do_info` calls it).
- Files: `mud/commands/group_commands.py`, `tools/diff_harness/pyreplay.py`,
  `tools/diff_harness/scenarios/group_follow_cycle.json`,
  `tests/data/golden/diff/group_follow_cycle.golden.json`,
  `tests/integration/test_group_006_listing_order.py`,
  `tests/test_differential_smoke.py` (count comment), plus docs (FINDINGS-037,
  ACT_COMM GROUP-006 row, INV-045 site inventory, CHANGELOG).

## Next session — continue widening the harness

Still grep-verified as zero-scenario surfaces:

- **Character advancement** — `practice` / `train` / `gain` (gain is the
  cleanest deterministic slice: XP/level math, train/practice counters).
- **Death lifecycle** — `corpse` → auto-loot / auto-gold → `sacrifice`
  (`mob_death_trigger` fires the trigger, not the corpse/loot mechanics).

Method reminder, reinforced this session: even a "deterministic" scenario can
trip RNG/setup asymmetries (boot-RNG, unset exp, meta-output leaks) — bracket
spawns with `__seed`, mirror `make_test_char` defaults in pyreplay, and keep
meta-commands output-silent. A divergence is a **FINDING** (FINDINGS.md →
gap-closer / INV), never overwrite the golden. Build/regen needs the shim
(`cd src && make -f Makefile.diffshim diffshim`; built). Capture per-scenario
(`--scenario <name>`), never `--all`.

Secondary (do not lead): `test_all_commands.py` `tap` alias false-positive (low).
