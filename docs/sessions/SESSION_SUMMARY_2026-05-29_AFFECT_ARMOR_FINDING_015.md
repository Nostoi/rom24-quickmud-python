# Session Summary — 2026-05-29 — affect_armor differential scenario (FINDING-015 / MAGIC-002) + pysnap affect-read fix

## Scope

Continued from the spell_combat handoff (differential harness at zero known
divergences across three scenarios; the `__learn` primitive makes spell scenarios
cheap; new-scenario probing is the active mode). The handoff's top recommendation
was a new scenario exercising an un-probed path — defensive/affect spells. This
session built that scenario (`affect_armor`), which required first fixing a harness
instrument gap, then surfaced and fixed a real parity divergence (FINDING-015).

The affect subsystem was genuinely un-probed: the snapshot's `affects`,
`affect_flags`, `eff_hitroll`, `eff_damroll`, and `eff_ac` fields never change
across the three prior scenarios (melee/magic-missile/movement). A self-buff
scenario is the first to move them.

## Outcomes

### Harness instrument — pysnap could not read affects (diff-harness, `d296b434`)

- **Gap**: `pysnap._affect_names` read `aff.spell_name`/`aff.name`, but the real
  affect model (`mud.models.character.AffectData`) carries the spell identity in
  `.type` — a lowercase ROM skill name in the SpellEffect-sync path
  (`character.py:_sync_spell_effect_to_affected`, e.g. `"armor"`) or an int SN via
  `affect_to_char`. So **every** `AffectData` was invisible to the snapshot and
  `affects` was silently always `[]` on the Python side. No prior golden exercised
  `affects`, so it had never mattered.
- **Fix**: `_affect_names` now reads `.type`; an int SN is mapped through
  `ROM_SKILL_NAMES_BY_INDEX` to match the C shim's `skill_table[paf->type].name`
  (lowercase). Locked by two Python-only unit tests in `test_diff_harness_unit.py`
  (the differential alone can't regression-protect this — no golden exercised it).
- **Deferred (not touched)**: the `affect_flags` case mismatch (C lowercase
  `affect_flags[]` vs Python `AffectFlag.<NAME>.name`). `armor` sets no bitvector,
  so no flag is exercised; defer that normalization to a flag-setting scenario
  (sanctuary/haste/detect-invis) where a real golden can prove it.

### `FINDING-015` / `MAGIC-002` — affect spells silent on success via `do_cast` — ✅ FIXED (armor) (master 2.11.20, `a3476e33`)

- **Python**: `mud/skills/handlers.py` (`armor`)
- **ROM C**: `src/magic.c:753-777` (`spell_armor`)
- **Gap**: ROM `spell_armor` sends `"You feel someone protecting you."` to the
  victim on success (and `act("$N is protected by your magic.")` to the caster for
  a cross-target cast); the already-affected branch is `"You are already armored."`
  (self) / `act("$N is already armored.")`. The Python `armor` handler applied the
  −20 AC affect but was **silent** on success, and since `do_cast` is silent on a
  successful cast (FINDING-013 — all output comes from the spell function), the line
  was dropped entirely. The already-affected branch also sent the non-ROM
  `"They are already protected."`
- **Surfaced by**: the new `affect_armor` differential scenario, step 3
  (`cast armor`): C `['You feel someone protecting you.']` vs py `[]`. After the
  pysnap fix, `affects == ['armor']`, `eff_ac == [80,80,80,80]` (−20), and
  `mana == 80` (100 − 20) all converged — the **only** diverging field was `output`,
  exactly as predicted.
- **Fix**: `armor` now mirrors ROM's messaging faithfully (TO_VICT success line,
  TO_CHAR caster line on cross-target, ROM already-armored messages).
- **Tests**: `tests/integration/test_magic_002_armor_message.py` (3 tests:
  self-cast success message, cross-target both-sides messaging, already-affected
  message) — failing-first, then green.
- **Class, not one-off**: `bless` (`handlers.py:1465`) and `shield`
  (`handlers.py:7094`) are likewise silent on success — every affect-only spell
  cast via `do_cast` is missing its ROM success line. The broader sweep is filed
  under `MAGIC-002` (still OPEN) as follow-up; this session fixes the `armor`
  instance the scenario exercises.

### `affect_armor` converges end-to-end (diff-harness, `3a5a5379`)

- New scenario `tools/diff_harness/scenarios/affect_armor.json` + committed golden:
  an L10 mage (`level=10` clears armor's `skill_level[mage]==7`; −20 AC is
  level-independent so the baseline stays clean) `__learn`s then self-casts `armor`.
- After merging the master armor fix into diff-harness, the replay converges; the
  `KNOWN_DIVERGENCES` entry self-cleared. **All four** scenarios
  (`movement_get_drop`, `combat_melee_rounds`, `spell_combat`, `affect_armor`) now
  converge end-to-end; `KNOWN_DIVERGENCES` is empty again.

## Files Modified

### master (1 commit, 2.11.19 → 2.11.20)
- `mud/skills/handlers.py` — `armor` delivers ROM `spell_armor` messaging
- `tests/integration/test_magic_002_armor_message.py` — 3 regression tests (new)
- `docs/parity/MAGIC_C_AUDIT.md` — MAGIC-002 row added; armor instance ✅ FIXED, bless/shield sweep OPEN
- `CHANGELOG.md`, `pyproject.toml` — 2.11.19 → 2.11.20

### diff-harness (2 commits + merge)
- `tools/diff_harness/pysnap.py` — `_affect_names` reads `AffectData.type` (+ `_sn_to_skill_name`)
- `tests/test_diff_harness_unit.py` — 2 unit tests for the affect read
- `tools/diff_harness/scenarios/affect_armor.json` + committed golden — new scenario
- `tests/test_differential_smoke.py` — `affect_armor` KNOWN_DIVERGENCES entry added then self-cleared
- `tools/diff_harness/FINDINGS.md` — FINDING-015 (RESOLVED for armor)

## Test Status

- `pytest tests/integration/test_magic_002_armor_message.py` — 3/3 passing.
- Wider net `pytest -k "spell or skill or armor or cast or magic"` — 1145 passed, 1 skipped.
- Differential (diff-harness `3a5a5379`): **12 passed, 0 xfail** — all four scenarios
  (`movement_get_drop`, `combat_melee_rounds`, `spell_combat`, `affect_armor`) converge
  end-to-end + 8 harness unit tests.
- Full suite (master `a3476e33`): **4957 passed, 4 skipped** (~98s; +3 vs the prior
  4954 from `test_magic_002_armor_message.py`).
- `ruff check` on touched files clean (pre-existing F841 debt in `handlers.py` at
  lines 672/1753/3488/3635/6268 left untouched — not introduced this session).

## Outstanding

- **`MAGIC-002` sweep (OPEN, `MAGIC_C_AUDIT.md`)** — `bless`, `shield`, and the
  other affect-only spells are still silent on success through `do_cast`. Each needs
  its ROM `spell_*` success message ported (one gap-closer per spell, or a batched
  audit if scoped together). `armor` is done; the rest are the cheap follow-up.
- **`affect_flags` case-normalization (harness, deferred)** — the comparator does
  not case-fold `affect_flags`; C emits lowercase (`"sanctuary"`), Python
  `AffectFlag.<NAME>.name` is uppercase. Fix this when adding the first flag-setting
  scenario (sanctuary/haste/detect-invis), where a real golden proves the fix.
- **`SHOP-PET-002`** (open, `FIGHT_C_AUDIT.md`) — pet purchase should
  `create_mobile(pIndexData)` (fresh re-roll), not clone the template. RNG-stream
  scope; breaks existing pet-shop gold assertions.
- **Python input-loop wait gate** (optional, `FINDINGS.md` FINDING-014) —
  async-architecture project, not a parity gap.
- **`test_combat_death.py` xdist flake** (carried) — seed RNG in the unit death tests.
- Stray uncommitted 1-line doc tweak to `.claude/skills/gitnexus/gitnexus-cli/SKILL.md`
  (present in both worktrees; unrelated to parity).

## Next Steps

The differential harness is back at **zero known divergences** across four scenarios.
The cheapest high-value next move is the **MAGIC-002 sweep** — port the ROM success
message for `bless`/`shield` and the other affect-only spells (the `affect_armor`
pattern + the `__learn` primitive make a per-spell scenario or a direct gap-closer
cheap, and each is a confirmed silent-on-success instance). Alternatively, add the
first **flag-setting** affect scenario (sanctuary/haste) — it surfaces the deferred
`affect_flags` case-normalization and probes the `affect_flags` snapshot field, still
un-exercised. Or pick up `SHOP-PET-002` (a concrete RNG-parity gap).
