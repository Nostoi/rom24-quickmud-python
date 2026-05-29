# Session Summary — 2026-05-29 — spell_combat differential scenario (FINDING-012/013/014) + SHOP-PET-001

## Scope

Continued from the FINDING-011 handoff (differential harness at zero known
divergences, per-file audit tracker exhausted, cross-file/new-scenario probing the
active mode). Two threads this session:

1. **SHOP-PET-001** — the most self-contained documented follow-up in
   `FIGHT_C_AUDIT.md`. Investigation showed its premise was factually wrong;
   reclassified N/A and filed the real residual divergence as SHOP-PET-002.
2. **A new differential scenario** (`spell_combat`) to surface the next divergence,
   since the existing scenarios (`combat_melee_rounds`, `movement_get_drop`) both
   converge. Built the scenario + a reusable `__learn` harness primitive; it
   surfaced three divergences (FINDING-012/013/014), all now resolved.

## Outcomes

### `SHOP-PET-001` — ❌ N/A (premise-incorrect), `SHOP-PET-002` filed (master 2.11.17, `8003d33f`)

- **Claim**: a bought pet's `dam_type` ends up `0` → attack index 0 → noun "hit",
  because `_clone_pet_character` reads `proto.dam_type` (left at 0 by the loader).
- **Reality**: `template` is the kennel `MobInstance` (from `apply_resets` →
  `spawn_mob` → `from_prototype`), whose `dam_type` is already resolved to a non-zero
  attack-table index (FIGHT-023). Verified end-to-end: a "beating" proto's pet gets
  `dam_type == 13` and renders "beating", never 0/"hit". No code change.
- **Guard**: `tests/integration/test_shop_pet_001_dam_type_resolution.py` (2 tests).
- **SHOP-PET-002 (open)**: the genuine residual — ROM `do_buy` does
  `create_mobile(pIndexData)` (a fresh re-roll, `src/act_obj.c:2613`), where
  `_clone_pet_character` clones the template's runtime fields (no random-default
  re-roll, no spawn-RNG-stream advance, inherited HP/mana/gold). Tracked in
  `FIGHT_C_AUDIT.md`; not fixed (RNG-stream scope, breaks pet-shop gold assertions).

### `FINDING-012` — ✅ FIXED (master 2.11.18, `2a3ac8fd`)

- **Python**: `mud/spawning/templates.py` (`MobInstance`)
- **ROM C**: `src/magic.c:170` (`saves_spell` reads `victim->saving_throw`),
  `src/db.c` `create_mobile` (leaves a mob's `saving_throw` at 0)
- **Gap**: `MobInstance` mirrored many `CHAR_DATA` fields but omitted `saving_throw`,
  so casting any `saves_spell` offensive spell at a real NPC raised
  `AttributeError: 'MobInstance' object has no attribute 'saving_throw'` (surfaced as
  "Spell cast failed: …" — `do_cast` wraps `spell_fun` in try/except). No prior test
  caught it: existing spell tests use a `Character` victim or monkeypatch
  `saves_spell` away.
- **Fix**: added `saving_throw: int = 0` (additive; default mirrors ROM `create_mobile`).
- **Tests**: `tests/integration/test_finding_012_npc_spell_save.py` (failing-first
  AttributeError → pass). Full suite 4954 passed.

### `FINDING-013` — ✅ FIXED (master 2.11.19, `f1134681`)

- **Python**: `mud/commands/combat.py` (`do_cast`)
- **ROM C**: `src/magic.c:553-563` (`do_cast` success path — no `send_to_char`)
- **Gap**: ROM `do_cast` is silent on a successful cast; all output comes from the
  spell function (e.g. `damage()` → "Your magic missile maims the drunk."). Python's
  `do_cast` returned `f"You cast {skill.name}."`, which the dispatcher sends to the
  player — an extra line ROM never produces.
- **Fix**: `do_cast` returns `""` on success; the spell handler already delivers its
  messages via `char.messages`. Full spell suite stayed green, so no handler relied
  on the removed fallback for its only output. `skill_registry.cast`'s separate
  `_default_success_message` fallback (mob/item casting) left unchanged.
- **Tests**: `tests/integration/test_finding_013_cast_silent_on_success.py`
  (failing-first); re-baselined `test_do_cast_offensive_no_target_defaults_to_fighting_victim`.

### `FINDING-014` — ✅ RESOLVED as architectural divergence (diff-harness, `fb7adb7b`)

- **Class**: synchronous pulse-loop vs async (same class as `MESSAGE_DELIVERY.md`),
  **not a parity bug** — no production change.
- ROM `do_cast` only *sets* `WAIT_STATE` (`src/magic.c:547`); the wait gate lives in
  the comm.c input loop (`src/comm.c:619-621`/`:820-822`), which silently defers
  input. The C golden shows back-to-back casts firing only because the diffshim calls
  `interpret()` directly, **bypassing ROM's own loop gate** — an instrument artifact.
  Python's handler-level `char.wait > 0` enforcement is the more faithful end-state,
  and `wait` is not in the snapshot schema.
- **Resolution** (harness-only): the replay now drives ordinary commands below the
  wait gate (`char.wait = 0` before `process_command`), mirroring the C shim. With
  that, `spell_combat` converges end-to-end and is removed from `KNOWN_DIVERGENCES`.
- A real input-loop wait gate for Python is noted in `FINDINGS.md` as an optional
  separate async-architecture project.

### New harness infrastructure (diff-harness, `3feb9942`)

- **`spell_combat` scenario** (`tools/diff_harness/scenarios/spell_combat.json`) +
  committed golden — an L5 mage learns and casts magic missile at the drunk #3064
  twice, then a combat tick.
- **`__learn=<spell>` directive** — reusable, symmetric on both engines (C shim
  `skill_lookup` → `learned[sn]=100`; Python replay canonicalizes via
  `skill_registry.find_spell`). `learned == 100` → deterministic success + no
  `check_improve` RNG, so a cast draws only the `number_percent` success roll + the
  spell's own draws (symmetric). C binary rebuilt.

## Files Modified

### master (3 commits, 2.11.17 → 2.11.19)
- `mud/spawning/templates.py` — `MobInstance.saving_throw` (FINDING-012)
- `mud/commands/combat.py` — `do_cast` returns `""` on success (FINDING-013)
- `tests/integration/test_shop_pet_001_dam_type_resolution.py` — SHOP-PET-001 guard
- `tests/integration/test_finding_012_npc_spell_save.py` — FINDING-012 regression
- `tests/integration/test_finding_013_cast_silent_on_success.py` — FINDING-013 regression
- `tests/test_skills_spells_cast_listing.py` — re-baselined 1 assertion (FINDING-013)
- `docs/parity/FIGHT_C_AUDIT.md` — SHOP-PET-001 → N/A, SHOP-PET-002 filed
- `CHANGELOG.md`, `pyproject.toml` — 2.11.16 → 2.11.19

### diff-harness (3 commits)
- `tools/diff_harness/scenarios/spell_combat.json` + golden — new scenario
- `src/diff_shim/diffmain.c` — `__learn` directive (C binary rebuilt)
- `tests/test_differential_smoke.py` — `__learn` handler, replay drives below the
  wait gate, `KNOWN_DIVERGENCES` self-cleared
- `tools/diff_harness/FINDINGS.md` — FINDING-012/013/014

## Test Status

- Full suite (master `f1134681`): **4954 passed, 4 skipped** (~99s).
- Differential (diff-harness `fb7adb7b`): **9 passed, 0 xfail** — all three scenarios
  (`movement_get_drop`, `combat_melee_rounds`, `spell_combat`) converge end-to-end.
- `ruff check` on touched files clean (pre-existing F541/I001 debt in
  `combat.py`/`templates.py` left untouched — not introduced this session).

## Outstanding

- **`SHOP-PET-002`** (open, `FIGHT_C_AUDIT.md`) — pet purchase should
  `create_mobile(pIndexData)` (fresh re-roll), not clone the template. RNG-stream
  scope; breaks existing pet-shop gold assertions.
- **Python input-loop wait gate** (optional, `FINDINGS.md` FINDING-014) — enforce
  wait at dispatch/loop level like ROM `comm.c`; async-architecture project, not a
  parity gap.
- **`test_combat_death.py` xdist flake** (carried from prior session) — seed RNG in
  the unit death tests.
- **`ACT-CAP-001`** (`FIGHT_C_AUDIT.md`) — non-combat act() capitalization.
- Stray uncommitted 1-line doc tweak to `.claude/skills/gitnexus/gitnexus-cli/SKILL.md`
  (present in both worktrees; unrelated to parity).

## Next Steps

The differential harness is back at **zero known divergences** across three scenarios.
Next session should add another `spell_combat`-style scenario for an un-probed path
(defensive/affect spells like `bless`/`armor`/`chill touch`, multi-mob room, group
fight) to surface the next divergence — the `__learn` primitive makes spell scenarios
cheap now. Alternatively, pick up `SHOP-PET-002` (a concrete RNG-parity gap) or the
optional Python input-loop wait gate.
