# Cross-File Invariants — ROM 2.4b6 → Python Port

## Why this tracker exists

`ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` and the per-file `<FILE>_C_AUDIT.md`
documents verify **functions**: "does Python function X behave like ROM
function X?" That methodology is necessary but not sufficient. Three
serious bugs shipped this year against files marked ≥95% audited:

- **Duplicate combat-message delivery** (`comm.c` row says 95%): every
  combat message reached connected players TWICE because
  `_push_message` (engine.py) appended to the mailbox AND scheduled an
  async send, and `connection.py` drained the mailbox separately. Each
  function was individually fine; the *contract* between them was
  broken.
- **PC not in character_registry after WS login** (`save.c` row says
  100%): the audit pointed at `mud/persistence.py` (the JSON-pfile
  path), but production WS logins use `mud/account/account_manager.py`
  (the SQLAlchemy path), which never appended. Combat was one-way for
  every WS login.
- **Negative hp leaked into prompt** (`comm.c` row says 95%): the
  death path could render `<-15hp>` between `update_pos` setting
  `Position.DEAD` and `raw_kill` clamping to `max(1, hit)`. ROM's
  single-threaded loop forbids this; Python's async dispatch allowed
  it.

These are **invariants**, not function divergences. They live in the
spaces between modules — call chains, ordering relationships,
membership contracts. This tracker enumerates them, names them with
stable IDs (INV-NNN), and points each at an enforcement test.

## How to use this tracker

- When opening a new audit (`/rom-parity-audit`), check whether any
  invariant in this tracker touches the file under audit. If yes, run
  the enforcement test before claiming ≥95%.
- When closing a gap (`/rom-gap-closer`), if the fix touches code in a
  module other than the audit's "primary" Python file, add a line to
  the relevant invariant's "Touched by" column. This keeps the call
  chain visible.
- When a NEW invariant surfaces (root cause of a bug crosses files),
  add it here with the next free INV-NNN. Stable IDs forever — never
  renumber.
- Status values: ✅ ENFORCED (failing test exists, currently green),
  ⚠️ VERIFIED MANUALLY (read-only confirmation, no test), ❌ BROKEN
  (known regression).

## Invariants

| ID | Name | ROM mechanism | Python enforcement point | Test | Status |
|----|------|---------------|--------------------------|------|--------|
| INV-001 | SINGLE-DELIVERY | `src/comm.c:write_to_buffer` writes once per message | `mud/combat/engine.py:_push_message` returns after async send when `connection` exists | `tests/integration/test_message_delivery_no_duplicate.py` | ✅ ENFORCED |
| INV-002 | PROMPT-CLAMP | `src/comm.c:1420ff bust_a_prompt` runs after `src/fight.c:1718 raw_kill` clamps `hit >= 1` (single-threaded) | `mud/utils/prompt.py` clamps display to `max(0, hit)` at both render sites | `tests/test_prompt_clamps_hp.py` | ✅ ENFORCED |
| INV-003 | REGISTRY-MEMBERSHIP | `src/save.c:fread_char` appends to `char_list`; pulse handlers iterate it | Every `load_character` path appends to `mud.models.character.character_registry` | `tests/integration/test_character_creation_runtime.py::TestCharacterRegistryRegistration` | ✅ ENFORCED |
| INV-004 | PC-CONNECTION-SURVIVES-DEATH | `src/handler.c:2103-2187 extract_char(ch, FALSE)` keeps PC descriptor open | `mud/combat/death.py:raw_kill` does not touch `char.connection`; PC stays in registry | `tests/integration/test_pc_death_keeps_connection.py` | ✅ ENFORCED |
| INV-005 | SAME-ROOM-COMBAT-ONLY | `src/fight.c:violence_update` skips if `ch->in_room != victim->in_room` | `mud/game_loop.py:violence_tick` checks `attacker.room == victim.room` before `multi_hit` | `tests/integration/test_inv005_same_room_combat.py` | ✅ ENFORCED |
| INV-006 | FIGHTING-POINTER-COHERENCE | `src/fight.c:stop_fighting(victim, TRUE)` sweeps `char_list`, clears every `fch->fighting == victim` | `mud/combat/engine.py:stop_fighting(ch, both=True)` iterates `character_registry` | `tests/integration/test_inv006_fighting_pointer_coherence.py` | ✅ ENFORCED |
| INV-007 | RNG-DETERMINISM | `src/db.c init_mm` Mitchell-Moore RNG is the only source of combat/affect rolls | All `mud/combat/`, `mud/skills/`, `mud/spells/` use `mud.math.rng_mm.number_*`; never `random.*` | `tests/test_rng_determinism.py` | ✅ ENFORCED |
| INV-008 | DUAL-LOAD-CHARACTER-COHERENCE | (Python-only) Single canonical store for player state; no dual JSON-pfile / DB-row split | `mud/db/models.py:Character` is canonical (39 + base columns); `mud/account/account_manager.py:save_character` calls `save_character_to_db` (UPDATE), `load_character` queries the DB and runs `Character.from_orm`; the JSON pfile path is gone (deprecation banner on `mud/persistence.py`) | `tests/integration/test_inv008_persistence_coherence.py` + `tests/integration/test_db_canonical_round_trip.py` | ✅ ENFORCED |

## Action items

1. ~~**Write enforcement tests** for INV-005 (same-room combat) and
   INV-006 (fighting-pointer coherence after death).~~ **Done in 2.7.4**
   — see `tests/integration/test_inv005_same_room_combat.py` and
   `tests/integration/test_inv006_fighting_pointer_coherence.py`.
2. ~~**Decide on INV-007**: either codify as a `pytest -k` check (e.g.
   `tests/test_rng_determinism.py` greps for `random.` in `mud/combat/`)
   or accept it as convention and note in CONTRIBUTING.~~ **Done in 2.7.5**
   — `tests/test_rng_determinism.py` scans `mud/combat/`, `mud/skills/`,
   `mud/spells/`; vestigial `Random` removed from `SkillRegistry` as prerequisite.
3. ~~**Resolve INV-008** by consolidating the two `load_character`
   paths.~~ **Reversed in 2.8.x — now DB-canonical.** First closed in
   2.7.6 with the JSON pfile as canonical and the DB demoted to
   auth-only; that hybrid had a hidden seam at `create_character` /
   `Character.from_orm`, which still wrote/read the DB row at
   first-login. Reversed in two phases: 2.8.0 extended the
   `Character` SQLAlchemy model with 39 columns covering every
   `PlayerSave` field (incl. JSON columns for skills/affects/aliases/
   inventory/equipment); 2.8.1 swapped `account_manager.save_character`
   / `load_character` to the DB path and removed the JSON pfile
   delegation. `mud/persistence.py` is now a deprecation stub keeping
   only `time_info` helpers. See `docs/parity/INV008_REVERSAL_AUDIT.md`
   for the 71-field map that drove the reversal.

## Stale-row footnotes (linked from `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`)

These rows in the per-file tracker were correct *for the per-file
audit* but missed cross-file invariants. The per-file rating stays;
the cross-file work is tracked here.

- **`comm.c` (95% per-file)**: INV-001 (now ✅), INV-002 (now ✅).
  Pre-fix the row was misleading because both invariants were broken
  in code outside `comm.c` itself.
- **`fight.c` (95% per-file)**: INV-001 root cause lived in
  `mud/combat/engine.py` (the audit row's primary Python file) but
  surfaced as a `comm.c` symptom. INV-005 and INV-006 still need
  enforcement tests. Open FIGHT-XXX gaps (`do_kill → multi_hit`,
  `is_safe()` inside `damage()`) remain on the open-followups list.
- **`save.c` (100% per-file)**: row points only at
  `mud/persistence.py`. INV-003 was broken in
  `mud/account/account_manager.py` (the production path), not the
  audited file. INV-008 tracks the broader divergence between the
  two implementations.

## Maintenance

This tracker is small on purpose. If it grows past ~20 invariants,
something has gone wrong with the per-file audit methodology and the
two trackers should be merged or restructured. Discuss before adding
INV-021.
