# Session Summary — 2026-06-20 — Differential harness: death lifecycle → FIGHT-078

## Scope

Continued the differential-harness widening directive (the only enumeration-
*independent* ROM⇄Python oracle now the per-file audit tracker is drained). Picked
up from the prior session's handoff, which named **death lifecycle** (corpse →
loot → sacrifice) and **advancement** (gain/practice/train) as the two remaining
zero-scenario surfaces.

A pre-build probe pass (with the advisor) reshaped the plan:

- **Advancement is lower-yield than the handoff implied.** `advancement.py`
  (`do_practice`/`do_train`) and `do_gain` are heavily audited (TRAIN-001..006,
  PRACTICE-001, GAIN-001..003). The default diff-harness char also has **no
  skills** (`make_test_char` skips `group_add`) — `practice <skill>` would need
  new shim plumbing. (Correcting two stale beliefs: midgaard guildmasters are
  ACT_PRACTICE-only, but **train trainers do exist** — midgaard 3007 (the sailor)
  is ACT_TRAIN, and **gain trainers** are newthalos 9500-9503 (ACT_GAIN, lowercase
  `b`); both are `__mload`-able with zero plumbing, recorded for a future session.)
- **Death lifecycle was both higher-yield and low-friction.** `__instant_kill`
  already routes through the full Python death path (`apply_damage` → `raw_kill`
  → `make_corpse`), and `sacrifice` is RNG-free (`UMAX(1, level*3)`).

Authored **`death_corpse_loot_sacrifice`** — and it caught a real engine bug on
the first capture.

## Outcomes

### `FIGHT-078` — ✅ FIXED — NPC corpse drops phantom silver (silver-but-no-gold)

- **Python**: `mud/combat/death.py:make_corpse` (~`:446`)
- **ROM C**: `src/fight.c:1473`
- **Gap**: NPC `make_corpse` minted a money object whenever `gold > 0 or silver > 0`;
  ROM gates the NPC corpse's money on **`ch->gold > 0` alone** — a mob carrying
  silver but zero gold mints **no** money object and the silver is lost on
  extraction. So a silver-only NPC corpse held a lootable phantom `"N silver coins"`
  object ROM never creates (observable via `look in corpse` / `get all corpse`).
- **Fix**: NPC case now gates on `gold > 0`
  (`money_gate = gold > 0 if is_npc else (gold > 0 or silver > 0)`); PC case keeps
  its current full-coin gate pending FIGHT-079.
- **Surfaced by**: the `death_corpse_loot_sacrifice` differential scenario (step 10
  `look in corpse`: C held only the lantern, Python held lantern + 17 silver coins).
  Recorded as FINDING-038.
- **Tests**: `tests/integration/test_fight078_npc_corpse_money_gate.py` (2 —
  silver-only NPC drops no money; gold-bearing NPC keeps full money: regression
  guard for the `gold>0` path) + the differential replay. Test 1 verified red
  before fix (phantom coins), green after.
- **Impact**: LOW (`make_corpse` ← `raw_kill` only; 0 execution flows). MINOR
  severity (loot inflation; phantom silver was lootable).

### `FIGHT-079` — ⏸ DEFERRED (filed) — PC corpse full-coins instead of ROM half-coins

- **ROM C**: `src/fight.c:1483-1495` — a non-clan PC corpse drops **half** the
  coins (`gold/2`, `silver/2`, gated on `> 1`) and the player **keeps the other
  half**; clan PCs drop nothing.
- **Python**: `make_corpse` drops the **full** gold+silver on `> 0` and zeroes
  both for PCs — a dying PC loses all carried coins (ROM keeps half), clan
  membership ignored for money.
- **Why deferred** (AGENTS.md "HIGH-blast-radius → file, don't fix"): player
  coin-loss-on-death is balance-relevant + player-facing, the PC path has **zero**
  existing test coverage (every `make_corpse` test uses `is_npc=True`), and it is
  **not** exercised by any differential scenario (the harness can only kill mobs,
  not inspect the driver PC's own corpse mid-run). Close as its own
  `/rom-gap-closer` commit once a verification path exists.

## Files Modified

- `mud/combat/death.py` — NPC/PC-split money gate in `make_corpse` (FIGHT-078).
- `tests/integration/test_fight078_npc_corpse_money_gate.py` — new, 2 tests.
- `tools/diff_harness/scenarios/death_corpse_loot_sacrifice.json` — new scenario.
- `tests/data/golden/diff/death_corpse_loot_sacrifice.golden.json` — C golden.
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-078 (✅ FIXED) + FIGHT-079 (⏸ DEFERRED) rows.
- `tools/diff_harness/FINDINGS.md` — FINDING-038 (✅ RESOLVED).
- `CHANGELOG.md` — Added (scenario) + Fixed (FIGHT-078) entries.
- `pyproject.toml` — 2.14.202 → 2.14.203.

## Test Status

- `tests/integration/test_fight078_npc_corpse_money_gate.py` — 2/2 passing.
- Differential smoke (all 46 scenarios) + `test_combat_death.py` — 98/98 passing.
- Full suite: 6010 passing, 4 skipped (171s).
- `ruff check .` clean.

## Next Steps

Keep widening the differential harness (guardrail #3: the only enumeration-
independent oracle). Concrete, now-deplumbed targets:

- **Advancement — train/gain (zero plumbing confirmed this session).** `__mload`
  midgaard 3007 (ACT_TRAIN) for `train str/hp/mana` + no-arg session display;
  `__mload` newthalos 9500-9503 (ACT_GAIN) for `gain convert`/`gain points`/`gain
  list`. All deterministic counter math, no RNG. Differential CONFIRM more likely
  than catch (heavily audited) but locks the surface. `practice` still needs a
  partial-skill shim meta (`make_test_char` skips `group_add`) — defer or add a
  `__learn_pct=` meta.
- **FIGHT-079** — PC corpse half-coin gate, once a PC-corpse verification path
  exists (harness can't inspect the driver's own corpse; needs a unit/integration
  test that kills a *PC* victim and checks its corpse money). Own gap-closer commit.
- **Death lifecycle, deeper** — auto-loot / auto-gold (PLR_AUTOLOOT/AUTOGOLD)
  needs a player-flag-set meta; current `death_corpse_loot_sacrifice` covers the
  manual corpse→get→sacrifice path only.

Method reminders (unchanged): bracket spawns with `__seed`; set mob wealth
explicitly post-spawn (`__mob_gold`/`__mob_silver`) — boot-rolled wealth is NOT
bit-matched C⇄Python; capture per-scenario (`--scenario`), never `--all`; a
divergence is a FINDING (FINDINGS.md → gap-closer/INV), never overwrite the golden.

---

## Addendum — advancement surface (train / gain) → GAIN-005

Continued the same session into the handoff's named next target (advancement).
Confirmed the trainers are `__mload`-able with zero plumbing and authored two
scenarios. First fixed a harness-setup asymmetry: `pyreplay.py` now mirrors
`make_test_char`'s new-player session counts (`train=3`, `practice=5`;
diffmain.c:500-501) — Python `create_test_character` left both 0 (invisible until
a train/practice/gain command prints the count). train/practice are **not**
snapshotted, so the 46 existing goldens were unaffected (verified).

### `train_stats_sessions` — ✅ clean negative (no engine change)

- `__mload` sailor (midgaard 3007, ACT_TRAIN) → `train` (no-arg session display +
  "You can train: ...") → `train str` / `train hp` / `train mana` → out-of-sessions
  refusal → `train` again. Converges clean — advancement is heavily audited.

### `GAIN-005` — ✅ FIXED — `do_gain` trainer lines render "The trainer", not the name

- **Python**: `mud/commands/remaining_rom.py:_gain_trainer_name`
- **ROM C**: `src/skills.c:70,137-143,181-244` (`act("$N ...")` → `PERS(mob)` →
  `mob->short_descr`)
- **Gap**: `_gain_trainer_name` read `short_descr or "The trainer"`; a spawned
  `MobInstance` leaves `.short_descr` None and carries the display string in `.name`
  (`templates.py:447`), so **every** live ACT_GAIN trainer printed the placeholder
  "The trainer says/tells you ...". The GAIN-004 act-cap tests missed it by setting
  `short_descr` explicitly on a `Character`.
- **Fix**: established `short_descr or name` idiom (cf. `make_corpse`), then
  `capitalize_act_line`.
- **Surfaced by**: the `gain_convert_points` scenario (`__mload` newthalos
  guildmaster 9500, ACT_GAIN; `gain` / `convert` / `points` / `list`). Step 3 `gain`:
  C "The guildmaster says 'Pardon me?'" vs Python "The trainer ...". Recorded as
  FINDING-039. The full `gain list` table (GAIN-003) was already correct.
- **Tests**: `tests/integration/test_do_gain_act_gain_bit.py::test_gain_trainer_name_falls_back_to_name_when_short_descr_unset`
  (red→green, verified by reverting) + the differential replay.
- **Impact**: LOW (`_gain_trainer_name` ← `do_gain` only).

### Files (addendum)

- `mud/commands/remaining_rom.py` — `_gain_trainer_name` `short_descr or name` (GAIN-005).
- `tests/integration/test_do_gain_act_gain_bit.py` — new GAIN-005 regression test.
- `tools/diff_harness/pyreplay.py` — train/practice setup mirror.
- `tools/diff_harness/scenarios/{train_stats_sessions,gain_convert_points}.json` + goldens.
- `docs/parity/SKILLS_C_DO_GAIN_AUDIT.md` — GAIN-005 row (✅ FIXED).
- `tools/diff_harness/FINDINGS.md` — FINDING-039.
- `CHANGELOG.md`, `pyproject.toml` 2.14.203 → 2.14.204.

Commits: `a5ccd377` (train scenario + setup mirror), `d78c0ff0` (GAIN-005).
48 scenarios, all converge; `KNOWN_DIVERGENCES` empty.
