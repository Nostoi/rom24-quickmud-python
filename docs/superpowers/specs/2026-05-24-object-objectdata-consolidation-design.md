# Object / ObjectData Consolidation Design

**Date:** 2026-05-24
**Status:** Proposed (rev 2 — post critique; Phase 2 deferred)
**Tracker:** INV-012 OBJECT-LIST-CANONICAL (to be added)
**Parallels:** INV-008 (dual-`load_character` consolidation)
**Honest commit count:** 15–25 small commits in Phase 1. Not 5.

## Problem

The runtime is built on two distinct Python classes that both represent
"an instance of an in-world object":

| Class | File | Field style | Production use |
|-------|------|-------------|----------------|
| `Object` | `mud/models/object.py` | Python-ish (`prototype`, `location`, `contained_items`) | **Yes** — `spawn_object` constructs it; `Room.contents`, `Character.inventory`, `Character.equipment` hold it; ~71 importers; magic/skills/world.obj_find/mob_cmds/do_get/do_drop/OLC all use it |
| `ObjectData` | `mud/models/obj.py` | ROM-faithful (`pIndexData`, `in_room`, `in_obj`, `carried_by`, `contains`, `next`, `next_content`) | **No** for the production hot path — `object_registry: list[ObjectData]` (line 107) is declared but **nothing ever appends to it**. **Yes** for ~35 test constructors and ~12 `isinstance(ObjectData)` branches in `mud/skills/handlers.py`, `mud/magic/effects.py`, and `mud/game_loop.py` |

Cross-file consequence (captured in
`docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` watch list as of
2.8.79): every iteration over `object_registry` is a no-op in
production. Affected systems:

- `mud/world/obj_find.py:get_obj_world` — locate-object spells.
- `mud/magic/effects.py` locate-object effect.
- `mud/mobprog.py` oload triggers.
- `mud/skills/handlers.py` global object scans.
- `mud/music/__init__.py` music decay.
- `mud/game_loop.py:object_update` decay tick.

ROM source of truth: `src/handler.c:1626-2096`. One `OBJ_DATA` struct,
one global `object_list` head, four exclusive containers (`in_room`,
`carried_by`, `in_obj`, equipped via `wear_loc`).

## Non-goals (this session)

- **Phase 2 field renames** (`prototype` → `pIndexData`, `location` →
  `in_room`, `contained_items` → `contains` across 71 files). Originally
  proposed; **dropped** after reviewer pushback. Field renames have no
  behavioral payoff; Phase 1 alone is already 15–25 commits.
  Deferred to a follow-up session under its own INV.
- `ObjIndex`, `Affect`, `obj_index_registry` restructuring.
- Per-file audit re-runs.
- Save/JSON serialization format changes. (Verified: `mud/persistence.py`
  is deleted as of 2.8.3; `mud/account/account_manager.py` and
  `mud/db/serializers.py` go through `Character.from_orm` and don't
  reference `Object.prototype` / `location` / `contained_items` by
  name. `mud/models/object_json.py` is independent. Phase 1 is
  save-format-inert.)

## Approach

**`Object` becomes canonical; `ObjectData` is deleted.** Field names
stay Python-ish for now (Phase 1 only adds *new* ROM-named fields where
they're missing; renames are Phase 2 deferred work).

### Why `Object` wins

- 71+ files import `Object`; switching the class identity to
  `ObjectData` would churn every hot path. Test surface alone:
  ~234 `Object(...)` constructors in `tests/` vs ~35 `ObjectData(...)`.
- Production constructs and holds `Object`. The duck-typed `getattr`
  callers in `game_loop.py` already work *because* they're tolerant —
  they read fields like `carried_by` that `Object` doesn't formally
  declare. Making those fields real on `Object` flips them from
  "accidentally `None`" to "actually correct".
- `ObjectData`'s field names are the parity-valuable bit; lift them
  onto `Object` (as new fields, not as renames) without renaming the
  class.

### Phase 1 — Behavioral correctness (this session, branch)

Each numbered item below = one commit. Many sub-items are also one
commit each — the honest count is 15–25 small commits, not 5. The TDD
rule (failing test before fix) applies to every commit that changes
runtime behavior; type-only commits don't need new tests but must keep
the full suite green.

**Commits 1a–1c: Extend `Object` with ROM-named fields.**

`Object` is a `@dataclass`. A `@property` named identically to a
dataclass field collides with the dataclass-generated descriptor. So:
**new fields are added as dataclass fields with `None` defaults; ROM
names that have to coexist with the existing Python-ish field are
implemented as `@property` accessors with explicit setters where
needed.**

- **1a — new dataclass fields** with `None` defaults. No aliases yet,
  no callers change.
  - `in_room: Room | None = None` (will eventually replace `location`;
    coexists for now)
  - `in_obj: Object | None = None`
  - `carried_by: Character | None = None`

  Regression: full suite green. No new test (no behavior change yet —
  fields exist and default to `None`, matching the pre-edit
  `getattr(..., None)` semantics).

- **1b — `pIndexData` property** (read + write) aliased to
  `self.prototype`. No duplicate storage; no dataclass field of that
  name.

  Test: `tests/integration/test_inv012_object_list_canonical.py::test_pindexdata_aliases_prototype`
  asserts `obj.pIndexData is obj.prototype` after `spawn_object`.

- **1c — `contains` property** (read-only — list is mutable, no setter
  needed) aliased to `self.contained_items`.

  Test: same file,
  `test_contains_aliases_contained_items`.

**Commit 2: Populate `object_registry` at spawn; drain at extract.**

- Change `mud/models/obj.py:object_registry` typing from
  `list[ObjectData]` to `list[Object]`. Keep the symbol on
  `mud/models/obj.py` to preserve every existing import statement.
- `mud/spawning/obj_spawner.py:spawn_object` appends the new instance
  to `object_registry` before returning.
- `mud/game_loop.py:_extract_obj` already calls
  `object_registry.remove(obj)` when present; verify it still works
  (it does — same symbol, now non-empty).

**Failing-test-first**:
`test_inv012_object_list_canonical.py::test_spawn_appends_to_registry`,
`::test_extract_removes_from_registry`,
`::test_extract_recursively_removes_nested_contents`.
These fail on master (registry stays empty); pass after Commit 2.

**Commit 3: Re-type Phase-1 helpers from `ObjectData` to `Object`.**

This is a *type annotation* sweep. Runtime behavior is preserved
because the callers are already passing `Object` instances. Pyright
diagnostics on `game_loop.py` / `handler.py` reduce. Subagent fan-out
is safe here:

- **3a** — `mud/game_loop.py` helpers: `_remove_from_character`,
  `_obj_to_room`, `_obj_to_char`, `_obj_to_obj`, `_obj_from_obj`,
  `_extract_obj`, `_get_obj_weight_recursive`, `_render_obj_message`,
  `_object_decay_message`, `_broadcast_decay`, `_spill_contents`,
  `_resolve_object_room`, `_clear_object_affect`,
  `_broadcast_object_wear_off`, `_tick_object_affects`.
  Annotations only — no logic changes.

- **3b** — `mud/handler.py`: `affect_enchant`, `affect_to_obj`,
  `affect_remove_obj`. Annotations only.

Two parallel subagents (one per file). Each runs `pytest` before
committing.

**Commits 3c–3g: collapse `isinstance(ObjectData)` branches.**

The reviewer found ~12 `isinstance(obj, ObjectData)` / `isinstance(target,
(Object, ObjectData))` sites in `mud/skills/handlers.py`,
`mud/magic/effects.py`, and `mud/game_loop.py`, with separate code
paths per arm. Each collapse is a deliberate behavior decision (the
`ObjectData` arm may have had distinct logic), so each gets its own
gap-closer commit with a focused test that proves the merged path
matches ROM.

Sequence (single-threaded — these need careful review):

- **3c** — `mud/skills/handlers.py` lines 657, 4096, 5294 (the three
  `if ObjectData: ... elif Object: ...` branches). One commit per
  branch with a parity-style test asserting the merged path.
- **3d** — `mud/skills/handlers.py` remaining `isinstance(ObjectData)`
  filter sites (looser — these filter OUT non-Object targets; usually
  safe to delete since `Object` is the only class left).
- **3e** — `mud/magic/effects.py` `isinstance(target, Object)` filters
  (5 sites) — these will be tautological after Commit 4 but stay in
  place during transition.
- **3f** — `mud/game_loop.py:_extract_obj` dual-shape branches at lines
  ~906/939/975 ("support both Object.contained_items and
  ObjectData.contains"). Delete the `ObjectData.contains` arm.
- **3g** — any straggler `isinstance(ObjectData)` discovered by
  `pyright --outputjson | jq` after 3a–3f.

**Commit 4 series: migrate test fixtures from `ObjectData` to
`Object`.**

35 `ObjectData(...)` constructors across 9 test files. One commit per
test file. Each file's test must still pass after the migration. This
is the bulk of the honest commit count — probably **8–10 commits**.
Subagent fan-out is safe here (each agent gets one test file in a
worktree, no cross-file dependencies):

- `tests/test_music.py`
- `tests/test_game_loop.py`
- `tests/test_skills_buffs.py`
- `tests/test_skills_damage.py`
- `tests/test_combat_death.py`
- `tests/test_obj_update_rom_parity.py`
- `tests/integration/test_music_play.py`
- `tests/integration/test_update_c_parity.py`
- `tests/integration/test_compare_critical_gaps.py`

Strategy per file: replace `ObjectData(item_type=X, weight=Y, ...)`
with `Object(instance_id=None, prototype=ObjIndex(item_type=X,
weight=Y, ...))` plus any post-construct assignments
(e.g. `obj.in_room = room`). The new fields from Commit 1a make this
mechanical.

**Commit 5: Delete `ObjectData` and lock in INV-012.**

- Remove `class ObjectData` from `mud/models/obj.py`. Leave `Affect`,
  `ObjIndex`, `obj_index_registry`, `object_registry` in place.
- Update `__all__` exports.
- Add INV-012 OBJECT-LIST-CANONICAL row to
  `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`. Contract: every
  `Object` returned by `spawn_object` is in `object_registry`;
  `_extract_obj` removes it (recursively for contents); container
  chains (room.contents, char.inventory, char.equipment,
  obj.contained_items) and the registry stay coherent.
- Move the watch-list entry from "open" to "closed" with the date and
  the merge commit pointer.

## Verification gate (strengthened from rev 1)

Per `verification-before-completion`:

- `pytest` → 4678 passed, 1 pre-existing failure (unchanged).
- `ruff check .` clean.
- INV-012 enforcement test green (registry populated + drained,
  recursive container extract, coherence sweep).
- **At least one smoke test per newly-live system, OR an explicit
  "deferred" note in INV-012 narrowing the contract to populated +
  drained.** The reviewer correctly pointed out that locate-object,
  oload, and decay paths will execute against real data for the first
  time after Commit 2; running the existing 4678 tests proves nothing
  about whether those paths are *correct* — they were never covered.
  Decision: write smoke tests as part of Commit 2 for at least:
  - `mud/world/obj_find.py:get_obj_world` returns a spawned object by
    name.
  - `mud/game_loop.py:object_update` ticks decay on a spawned object
    with `timer > 0` and decrements it.

  Anything not covered by smoke tests is documented as deferred
  follow-up under "Out-of-scope follow-ups" below.
- Cross-file tracker row added; watch-list entry struck through.
- `pyproject.toml` bumped 2.8.79 → **2.9.0** (minor — locate-object /
  oload / decay light up in production).
- `CHANGELOG.md` entry under `[2.9.0]`.
- Session handoff via `/rom-session-handoff` after the last commit.

## Risks & mitigations (revised)

| Risk | Mitigation |
|------|-----------|
| Commit 1's dataclass-property collision (a `@property` named the same as a dataclass field doesn't work) | Spec is now explicit: new ROM-named fields are dataclass fields when there's no Python-side name to collide with (`in_room`, `in_obj`, `carried_by`); ROM-named *aliases* that have to coexist are `@property` with no dataclass field of that name (`pIndexData`, `contains`). Split into 1a / 1b / 1c. |
| Test fixtures construct `ObjectData(...)` directly | Commit 4 series — one commit per test file, ~8–10 commits — migrates them before Commit 5 deletes the class. |
| `isinstance(obj, ObjectData)` branches with non-trivial logic | Commits 3c–3g collapse them deliberately, one branch per commit with a parity test. |
| `Object.location` setter sites (25+) need a setter if `location` ever becomes a property — but Phase 2 is deferred, so this doesn't bite this session | Phase 2 deferred. Phase 1 leaves `location` as the dataclass field. |
| Production paths previously masked by empty `object_registry` may surface bugs | The smoke tests in Commit 2 catch the obvious ones; anything else is a separate gap-closer commit *outside* this consolidation. INV-012 is narrowly scoped to the registry/coherence contract. |
| Save-format coupling | Verified out of scope: `mud/persistence.py` deleted in 2.8.3; account manager / db serializers use `Character.from_orm`, not `Object` field names. Phase 1 inert here. |

## Subagent fan-out (execution time)

Per user request, dispatch parallel agents where safe:

- **1a, 1b, 1c**: single-threaded (sequential, same file).
- **2**: single-threaded (registry + smoke tests).
- **3a + 3b**: 2 parallel subagents (one per file: `game_loop.py`,
  `handler.py`).
- **3c–3g**: single-threaded. Each isinstance collapse is a behavior
  decision needing review.
- **Commit 4 series**: up to 4 parallel subagents at a time, one test
  file per agent, each in its own `using-git-worktrees` worktree.
  Merge to the consolidation branch sequentially after each agent
  reports green.
- **5**: single-threaded.

## Out-of-scope follow-ups

- **Phase 2: field renames** (`prototype` → `pIndexData`, etc.). Own
  session, own INV.
- **Tautological `isinstance(target, Object)` filters in
  `mud/magic/effects.py`** — simplify in a Phase-2-adjacent cleanup.
- **New tests for newly-live systems** beyond the Commit 2 smoke
  tests: locate-object spell test, mobprog oload trigger test,
  full object-decay end-to-end test. Each is *new coverage*, not a
  consolidation gap.
- **`mud/handler.py::extract_obj`** — the file is in the known
  GitNexus indexing-gap list (per CLAUDE.md). Verify post-consolidation
  by re-running `npx gitnexus analyze` and seeing whether the file
  fits under 32 KB. If still too large, document.

## Definition of done

- `mud/models/obj.py` no longer exports `ObjectData`.
- `Object` is the only runtime object class.
- `object_registry: list[Object]` is populated at spawn and drained at
  extract, asserted by the INV-012 test plus smoke tests for
  `get_obj_world` and `object_update`.
- New ROM-named fields/aliases present on `Object`: `in_room`,
  `in_obj`, `carried_by`, `pIndexData`, `contains`.
- ~12 `isinstance(ObjectData)` branches collapsed; ~35 test
  constructors migrated.
- All 4678 currently-passing tests still pass; 1 pre-existing failure
  unchanged.
- INV-012 row added to cross-file invariants tracker; watch-list entry
  struck through.
- CHANGELOG `[2.9.0]`, version bump, SESSION_STATUS handoff all
  current.
- Branch ready for review or merge per user direction.
