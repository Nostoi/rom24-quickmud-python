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
| INV-005 | SAME-ROOM-COMBAT-ONLY | `src/fight.c:violence_update` skips if `ch->in_room != victim->in_room` | `mud/game_loop.py:violence_tick` checks `attacker.room == victim.room` before `multi_hit` | _missing — see action item below_ | ⚠️ VERIFIED MANUALLY |
| INV-006 | FIGHTING-POINTER-COHERENCE | `src/fight.c:stop_fighting(victim, TRUE)` sweeps `char_list`, clears every `fch->fighting == victim` | `mud/combat/engine.py:stop_fighting(ch, both=True)` iterates `character_registry` | _missing — see action item below_ | ⚠️ VERIFIED MANUALLY |
| INV-007 | RNG-DETERMINISM | `src/db.c init_mm` Mitchell-Moore RNG is the only source of combat/affect rolls | All `mud/combat/`, `mud/skills/`, `mud/spells/` use `mud.math.rng_mm.number_*`; never `random.*` | _grep-based CI check; informal_ | ⚠️ ENFORCED BY CONVENTION |
| INV-008 | DUAL-LOAD-CHARACTER-COHERENCE | (Python-only) two `load_character` / `save_character` paths exist (`mud/persistence.py` + `mud/account/account_manager.py`); both must produce equivalent runtime state | Both paths must populate `character_registry`, `equipment`, `inventory`, `room`, etc. | _missing — see Open Follow-ups in `SESSION_STATUS.md`_ | ⚠️ KNOWN DIVERGENCE |

## Action items

1. **Write enforcement tests** for INV-005 (same-room combat) and
   INV-006 (fighting-pointer coherence after death). Both are
   currently held only by reading the code; a regression in
   `violence_tick` or `stop_fighting` would silently re-introduce
   cross-room damage or stuck combat.
2. **Decide on INV-007**: either codify as a `pytest -k` check (e.g.
   `tests/test_rng_determinism.py` greps for `random.` in `mud/combat/`)
   or accept it as convention and note in CONTRIBUTING.
3. **Resolve INV-008** by consolidating the two `load_character` paths
   (open follow-up in `SESSION_STATUS.md`). Until then, every change
   to either file must be mirrored to the other.

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
