# Object / ObjectData Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate `mud.models.object.Object` and `mud.models.obj.ObjectData` into a single runtime class (`Object`), populate the canonical `object_registry` at spawn, drain it at extract, lock the contract in as INV-012 — unblocking locate-object spells, mobprog oload triggers, and object decay tick in production.

**Architecture:** `Object` becomes canonical (71+ existing importers, 234+ test constructors). `ObjectData`'s ROM-faithful field names (`in_room`, `in_obj`, `carried_by`, `pIndexData`, `contains`) are lifted onto `Object` — as new dataclass fields where there's no name collision, as `@property` accessors where there is. `ObjectData` is then deleted. ~15–25 small TDD commits across 5 phases.

**Tech Stack:** Python 3.12, dataclasses, pytest, ruff. ROM C source at `src/handler.c:1626-2096` is the canonical reference for object lifecycle semantics.

**Spec:** `docs/superpowers/specs/2026-05-24-object-objectdata-consolidation-design.md` (rev 2, post-critique).

---

## Pre-flight

### Task 0: Worktree + branch setup

**Files:** none modified yet — this creates the isolated workspace.

- [ ] **Step 1: Confirm clean state on master**

Run: `git status && git log -1 --oneline`
Expected: clean working tree on `master`, last commit `be4f643` (spec).

- [ ] **Step 2: Create the consolidation worktree via `using-git-worktrees`**

Invoke the `superpowers:using-git-worktrees` skill with branch name `inv-012-object-consolidation`. All subsequent work happens in the new worktree.

- [ ] **Step 3: Capture the baseline test count in the worktree**

Run: `python3 -m pytest 2>&1 | tail -3`
Expected: `1 failed, 4678 passed, 4 skipped`. Record this — it's the gate every subsequent commit must hold.

- [ ] **Step 4: Capture the baseline lint state**

Run: `ruff check . 2>&1 | tail -5`
Expected: clean. Record any pre-existing warnings — they must not grow.

---

## Phase 1: Extend `Object` with ROM-named fields

### Task 1a: Add `in_room`, `in_obj`, `carried_by` dataclass fields

ROM ref: `src/merc.h` `OBJ_DATA` struct fields `in_room`, `in_obj`, `carried_by`.

**Files:**
- Modify: `mud/models/object.py:14-34` (Object dataclass)

- [ ] **Step 1: Pre-edit sanity check — confirm these names are NOT already used as dataclass fields**

Run: `grep -nE "^\s+(in_room|in_obj|carried_by)\s*:" mud/models/object.py`
Expected: empty (no matches). If anything matches, abort and re-read the file.

- [ ] **Step 2: Write a passing-after-edit smoke test asserting fields exist with `None` defaults**

Create: `tests/integration/test_inv012_object_list_canonical.py`

```python
"""INV-012 OBJECT-LIST-CANONICAL enforcement.

ROM ref: src/handler.c:1626 obj_to_char, 1642 obj_from_char,
1904 obj_from_room, 1953 obj_to_room, 1968 obj_to_obj, 1996 obj_from_obj,
2051 extract_obj. ROM keeps a single global linked list (`object_list`)
of every OBJ_DATA instance; create_object appends, extract_obj removes
(recursively for contents).

Python contract (INV-012):

    Every Object returned by `spawn_object` appears in `object_registry`.
    `_extract_obj` removes it (recursively for nested contents).
    Container chains stay coherent with the registry.

See docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md INV-012.
"""

from __future__ import annotations

from mud.models.obj import ObjIndex
from mud.models.object import Object


def test_object_has_rom_named_fields_with_none_defaults():
    """Task 1a — Object exposes the ROM-named container fields."""
    proto = ObjIndex(vnum=93000, short_descr="a test object")
    obj = Object(instance_id=None, prototype=proto)
    # New dataclass fields (Commit 1a):
    assert obj.in_room is None
    assert obj.in_obj is None
    assert obj.carried_by is None
```

- [ ] **Step 3: Run the new test — it must FAIL on master**

Run: `python3 -m pytest tests/integration/test_inv012_object_list_canonical.py::test_object_has_rom_named_fields_with_none_defaults -v`
Expected: FAIL with `AttributeError: 'Object' object has no attribute 'in_room'`.

- [ ] **Step 4: Add the three fields to `Object`**

Edit `mud/models/object.py`, in the `Object` dataclass body (around line 32 — just before `_short_descr_override`). Insert:

```python
    # ROM-faithful container fields (INV-012). Initially None; populated by
    # spawn / obj_to_room / obj_to_char / obj_to_obj at runtime.
    in_room: "Room | None" = None  # ROM: ROOM_INDEX_DATA *in_room
    in_obj: "Object | None" = None  # ROM: OBJ_DATA *in_obj (container)
    carried_by: "Character | None" = None  # ROM: CHAR_DATA *carried_by
```

The `Character` forward ref requires the import block at top of the file:

```python
if TYPE_CHECKING:
    from .room import Room
    from .character import Character
```

(adding `from .character import Character` to the existing `TYPE_CHECKING` block).

- [ ] **Step 5: Re-run the new test — it must PASS**

Run: `python3 -m pytest tests/integration/test_inv012_object_list_canonical.py::test_object_has_rom_named_fields_with_none_defaults -v`
Expected: PASS.

- [ ] **Step 6: Run the full suite — no regressions**

Run: `python3 -m pytest 2>&1 | tail -3`
Expected: `1 failed, 4679 passed, 4 skipped` (4678 baseline + 1 new INV-012 test).

- [ ] **Step 7: Lint**

Run: `ruff check mud/models/object.py tests/integration/test_inv012_object_list_canonical.py`
Expected: clean.

- [ ] **Step 8: Commit**

```bash
git add mud/models/object.py tests/integration/test_inv012_object_list_canonical.py
git commit -m "$(cat <<'EOF'
feat(parity): INV-012/1a — add in_room/in_obj/carried_by to Object

Prep for the Object/ObjectData consolidation. Adds three ROM-named
container fields (in_room, in_obj, carried_by) to mud.models.object.Object
with None defaults. No callers change yet; the new fields default to
None, matching the pre-edit getattr(..., None) semantics that the
duck-typed game_loop.py helpers already rely on.

ROM ref: src/merc.h OBJ_DATA struct.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 1b: Add `pIndexData` property aliased to `prototype`

ROM ref: `src/merc.h` `OBJ_DATA::pIndexData` field. ROM's `pIndexData->vnum` is read everywhere; Python's `prototype.vnum` is the same data, different name.

**Files:**
- Modify: `mud/models/object.py` (add `@property pIndexData` with getter + setter)
- Test: `tests/integration/test_inv012_object_list_canonical.py` (extend)

- [ ] **Step 1: Append the new test**

Add to `tests/integration/test_inv012_object_list_canonical.py`:

```python
def test_pindexdata_aliases_prototype():
    """Task 1b — pIndexData is a property aliased to prototype."""
    proto = ObjIndex(vnum=93001, short_descr="another object")
    obj = Object(instance_id=None, prototype=proto)
    assert obj.pIndexData is obj.prototype
    assert obj.pIndexData is proto

    # Setter round-trips through prototype.
    new_proto = ObjIndex(vnum=93002, short_descr="replacement")
    obj.pIndexData = new_proto
    assert obj.prototype is new_proto
```

- [ ] **Step 2: Run it — must FAIL**

Run: `python3 -m pytest tests/integration/test_inv012_object_list_canonical.py::test_pindexdata_aliases_prototype -v`
Expected: FAIL with `AttributeError: 'Object' object has no attribute 'pIndexData'`.

- [ ] **Step 3: Add the property to `Object`**

Append, after the existing `short_descr` / `description` properties in `mud/models/object.py`:

```python
    # ROM-faithful prototype accessor (INV-012). Same backing field as
    # `prototype`; no duplicate storage.
    @property
    def pIndexData(self) -> ObjIndex:
        return self.prototype

    @pIndexData.setter
    def pIndexData(self, value: ObjIndex) -> None:
        self.prototype = value
```

- [ ] **Step 4: Re-run the test — must PASS**

Run: `python3 -m pytest tests/integration/test_inv012_object_list_canonical.py::test_pindexdata_aliases_prototype -v`
Expected: PASS.

- [ ] **Step 5: Full suite**

Run: `python3 -m pytest 2>&1 | tail -3`
Expected: `1 failed, 4680 passed, 4 skipped`.

- [ ] **Step 6: Commit**

```bash
git add mud/models/object.py tests/integration/test_inv012_object_list_canonical.py
git commit -m "feat(parity): INV-012/1b — pIndexData property aliases prototype

ROM-faithful accessor for Object.prototype. Read+write property with
no duplicate storage. Sets the stage for later phases that read
obj.pIndexData.vnum directly.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 1c: Add `contains` property aliased to `contained_items`

ROM ref: `src/merc.h` `OBJ_DATA::contains` field.

**Files:**
- Modify: `mud/models/object.py`
- Test: `tests/integration/test_inv012_object_list_canonical.py`

- [ ] **Step 1: Append the test**

```python
def test_contains_aliases_contained_items():
    """Task 1c — contains is a property returning contained_items."""
    proto = ObjIndex(vnum=93003, short_descr="a container")
    obj = Object(instance_id=None, prototype=proto)
    assert obj.contains is obj.contained_items
    assert obj.contains == []

    # Mutations through the underlying list are visible via the alias.
    child_proto = ObjIndex(vnum=93004, short_descr="a coin")
    child = Object(instance_id=None, prototype=child_proto)
    obj.contained_items.append(child)
    assert obj.contains == [child]
```

- [ ] **Step 2: Run — must FAIL**

Run: `python3 -m pytest tests/integration/test_inv012_object_list_canonical.py::test_contains_aliases_contained_items -v`
Expected: FAIL with `AttributeError`.

- [ ] **Step 3: Add the property**

Append in `mud/models/object.py`, after the `pIndexData` property:

```python
    # ROM-faithful contents accessor (INV-012). Same backing list as
    # `contained_items`; no setter — callers mutate the list in place.
    @property
    def contains(self) -> list["Object"]:
        return self.contained_items
```

- [ ] **Step 4: Re-run — must PASS**

Run: `python3 -m pytest tests/integration/test_inv012_object_list_canonical.py::test_contains_aliases_contained_items -v`
Expected: PASS.

- [ ] **Step 5: Full suite**

Run: `python3 -m pytest 2>&1 | tail -3`
Expected: `1 failed, 4681 passed, 4 skipped`.

- [ ] **Step 6: Commit**

```bash
git add mud/models/object.py tests/integration/test_inv012_object_list_canonical.py
git commit -m "feat(parity): INV-012/1c — contains property aliases contained_items

Read-only @property pointing at the same backing list. Sets the stage
for later phases that read obj.contains in ROM-faithful idiom.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 2: Populate `object_registry` + smoke tests

### Task 2: Populate at spawn, drain at extract, smoke-test newly-live systems

ROM ref: `src/db.c:create_object` appends to `object_list`; `src/handler.c:2051 extract_obj` removes (`object_list == obj` → `object_list = obj->next`, else unlink from list).

**Files:**
- Modify: `mud/models/obj.py:107` (retype `object_registry`)
- Modify: `mud/spawning/obj_spawner.py:73` (append before return)
- Verify: `mud/game_loop.py:1000-1001` (already calls `object_registry.remove(obj)`)
- Test: `tests/integration/test_inv012_object_list_canonical.py` (extend)

- [ ] **Step 1: Append the registry-membership + smoke tests**

```python
def test_spawn_appends_to_registry():
    """Task 2 — every spawn_object appends to object_registry."""
    from mud.models.obj import object_registry
    from mud.spawning.obj_spawner import spawn_object
    from mud.registry import obj_registry

    obj_registry[93010] = ObjIndex(vnum=93010, short_descr="a stone", item_type=1)
    try:
        before = len(object_registry)
        inst = spawn_object(93010)
        assert inst is not None
        assert inst in object_registry
        assert len(object_registry) == before + 1
    finally:
        if 'inst' in dir() and inst in object_registry:
            object_registry.remove(inst)
        obj_registry.pop(93010, None)


def test_extract_removes_from_registry():
    """Task 2 — _extract_obj drains the registry."""
    from mud.game_loop import _extract_obj
    from mud.models.obj import object_registry
    from mud.spawning.obj_spawner import spawn_object
    from mud.registry import obj_registry

    obj_registry[93011] = ObjIndex(vnum=93011, short_descr="a doomed thing", item_type=1)
    try:
        inst = spawn_object(93011)
        assert inst in object_registry
        _extract_obj(inst)
        assert inst not in object_registry
    finally:
        obj_registry.pop(93011, None)


def test_extract_recursively_removes_nested_contents():
    """Task 2 — _extract_obj on a container also drains its contents
    (ROM extract_obj recursion at src/handler.c:2063-2067)."""
    from mud.game_loop import _extract_obj
    from mud.models.obj import object_registry
    from mud.spawning.obj_spawner import spawn_object
    from mud.registry import obj_registry

    obj_registry[93012] = ObjIndex(vnum=93012, short_descr="a sack", item_type=15)
    obj_registry[93013] = ObjIndex(vnum=93013, short_descr="a coin", item_type=20)
    try:
        sack = spawn_object(93012)
        coin = spawn_object(93013)
        sack.contained_items.append(coin)
        coin.in_obj = sack

        assert sack in object_registry
        assert coin in object_registry

        _extract_obj(sack)

        assert sack not in object_registry
        assert coin not in object_registry, (
            "extract_obj must recurse into contents (src/handler.c:2063-2067)"
        )
    finally:
        obj_registry.pop(93012, None)
        obj_registry.pop(93013, None)


def test_get_obj_world_smoke_finds_spawned_object():
    """Task 2 smoke — locate-object plumbing returns a real spawned
    object. Was previously a no-op because object_registry was empty.
    """
    from mud.models.obj import object_registry
    from mud.spawning.obj_spawner import spawn_object
    from mud.registry import obj_registry
    from mud.world.obj_find import get_obj_world

    obj_registry[93014] = ObjIndex(
        vnum=93014,
        name="findme uniquekeyword",
        short_descr="a uniquely-named widget",
        item_type=1,
    )
    try:
        inst = spawn_object(93014)
        # Need a "looker" for get_obj_world; use the simplest possible char.
        from mud.models.character import Character

        looker = Character(name="Watcher", level=60)
        hit = get_obj_world(looker, "uniquekeyword")
        assert hit is inst, "get_obj_world must find spawned objects via object_registry"
    finally:
        if inst in object_registry:
            object_registry.remove(inst)
        obj_registry.pop(93014, None)


def test_object_update_smoke_decrements_timer_on_spawned_object():
    """Task 2 smoke — object decay tick iterates object_registry and
    decrements timers on spawned objects. Previously no-op."""
    from mud.models.obj import object_registry
    from mud.spawning.obj_spawner import spawn_object
    from mud.registry import obj_registry

    obj_registry[93015] = ObjIndex(vnum=93015, short_descr="a fading thing", item_type=1)
    try:
        inst = spawn_object(93015)
        inst.timer = 3

        from mud import game_loop

        game_loop.object_update()

        assert inst.timer == 2, (
            f"object_update must decrement timers on spawned objects; got {inst.timer}"
        )
    finally:
        if inst in object_registry:
            object_registry.remove(inst)
        obj_registry.pop(93015, None)
```

- [ ] **Step 2: Run the new tests — they MUST fail**

Run: `python3 -m pytest tests/integration/test_inv012_object_list_canonical.py -v -k "registry or smoke or get_obj_world or object_update"`
Expected: at least `test_spawn_appends_to_registry` FAILS (registry stays empty on master). The smoke tests may also fail or error.

- [ ] **Step 3: Retype `object_registry`**

Edit `mud/models/obj.py:107`. Replace:

```python
object_registry: list[ObjectData] = []
```

with:

```python
# INV-012: canonical instance list (parallels ROM `object_list` in src/db.c).
# Populated by mud/spawning/obj_spawner.py:spawn_object and drained by
# mud/game_loop.py:_extract_obj.
object_registry: list["Object"] = []  # noqa: F821 — Object lives in mud.models.object
```

You'll need a forward-string ref because `mud.models.obj` cannot import `mud.models.object` (the latter imports `Affect, ObjIndex` from the former).

- [ ] **Step 4: Add the spawn-time append**

Edit `mud/spawning/obj_spawner.py:73`. Just before `return inst`, insert:

```python
    # INV-012: canonical instance list — ROM src/db.c:create_object adds the
    # new obj to object_list before returning. Python mirror.
    from mud.models.obj import object_registry

    object_registry.append(inst)
    return inst
```

(Replace the existing `return inst` with the two-line block above. If `inst` is currently constructed and returned in the same expression, refactor to a local first.)

- [ ] **Step 5: Re-run the new tests**

Run: `python3 -m pytest tests/integration/test_inv012_object_list_canonical.py -v`
Expected: all 8 tests in the file PASS.

- [ ] **Step 6: Full suite — no regressions**

Run: `python3 -m pytest 2>&1 | tail -10`
Expected: `1 failed, 4686 passed, 4 skipped` (4681 from Phase 1 + 5 new Phase 2 tests). Verify the failure is still the pre-existing `test_wait_and_daze_decrement_on_violence_pulse` — not a new one.

**Failure-triage rule for this step:** if a previously-passing test now fails because `object_registry` is non-empty and an iteration hit it for the first time, treat it as a *real bug surfaced by the consolidation* and stop. Open a separate gap-closer commit *outside* this plan; document in the commit message that Phase 2 surfaced it. Do **not** "fix" it by inhibiting the registry append.

- [ ] **Step 7: Lint**

Run: `ruff check mud/models/obj.py mud/spawning/obj_spawner.py tests/integration/test_inv012_object_list_canonical.py`
Expected: clean.

- [ ] **Step 8: Commit**

```bash
git add mud/models/obj.py mud/spawning/obj_spawner.py tests/integration/test_inv012_object_list_canonical.py
git commit -m "$(cat <<'EOF'
feat(parity): INV-012/2 — populate object_registry at spawn

mud/spawning/obj_spawner.py:spawn_object now appends every new Object
instance to mud.models.obj.object_registry, mirroring ROM
src/db.c:create_object adding to object_list before returning.

Retypes object_registry from list[ObjectData] to list[Object]. The
symbol stays on mud.models.obj to preserve every existing import.

mud/game_loop.py:_extract_obj already calls object_registry.remove(obj);
that branch now actually does something instead of being a no-op
against an empty list.

Production payoffs (previously dead code paths now live):

- mud/world/obj_find.py:get_obj_world (locate-object spells)
- mud/magic/effects.py locate-object effect
- mud/mobprog.py oload triggers
- mud/skills/handlers.py global object scans
- mud/music/__init__.py music decay tick
- mud/game_loop.py:object_update (object decay)

Smoke tests for get_obj_world and object_update included so the
consolidation's verification gate catches regressions on these
newly-live paths. INV-012 enforcement still narrowly scoped to the
registry-coherence contract.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Phase 3: Type sweep + isinstance collapse

### Task 3a: Re-type `mud/game_loop.py` helpers (`ObjectData` → `Object`)

**Subagent dispatch** (one of two parallel agents). See Task 3b for the sibling.

Prompt to give the subagent (verbatim):

> You are working in the `inv-012-object-consolidation` worktree of the rom24-quickmud-python repo (already on the consolidation branch — do NOT create a new worktree). Your job is **type annotations only** on `mud/game_loop.py` — change every `ObjectData` annotation to `Object`. No logic changes.
>
> Steps:
> 1. `grep -n "ObjectData" mud/game_loop.py` — list every occurrence.
> 2. For each function listed in the plan's Task 3a (`_remove_from_character`, `_obj_to_room`, `_obj_to_char`, `_obj_to_obj`, `_obj_from_obj`, `_extract_obj`, `_get_obj_weight_recursive`, `_render_obj_message`, `_object_decay_message`, `_broadcast_decay`, `_spill_contents`, `_resolve_object_room`, `_clear_object_affect`, `_broadcast_object_wear_off`, `_tick_object_affects`), change the parameter annotation `obj: ObjectData` → `obj: Object`. Update the import at the top of the file: `from mud.models.obj import ObjectData, object_registry` → `from mud.models.obj import object_registry` and add `from mud.models.object import Object` if not already present.
> 3. **Do not** delete the dual-shape `getattr(obj, "contained_items", None) or getattr(obj, "contains", [])` patterns at lines 906, 926, 939, 975. Those are Task 3f's scope, not yours.
> 4. **Do not** touch `isinstance(..., ObjectData)` lines. Those are Task 3c–3g's scope.
> 5. Run `python3 -m pytest` — must still report `1 failed, 4686 passed, 4 skipped` (or whatever the baseline at start of this task is — confirm with the caller before proceeding if uncertain).
> 6. Run `ruff check mud/game_loop.py` — must be clean.
> 7. Commit on the consolidation branch: `feat(parity): INV-012/3a — retype game_loop.py helpers ObjectData→Object`.
> 8. Report back: commit SHA, line count changed, any anomalies.
>
> Hard constraints: no behavior changes. If anything beyond annotations needs to move to make the suite pass, stop and report — do not improvise.

- [ ] **Step 1: Dispatch Task 3a + Task 3b in parallel** (see Task 3b for sibling prompt)

Per `superpowers:dispatching-parallel-agents`. Both agents read-only on each other's files; both write on the same branch. Sequence the commits but execute in parallel.

- [ ] **Step 2: When both agents report green, verify**

Run: `git log --oneline -2`
Expected: two new commits with prefixes `INV-012/3a` and `INV-012/3b`.

Run: `python3 -m pytest 2>&1 | tail -3`
Expected: same `1 failed, 4686 passed, 4 skipped` (annotations don't change runtime).

---

### Task 3b: Re-type `mud/handler.py` affect helpers

**Subagent dispatch** (sibling of Task 3a). Prompt verbatim:

> You are working in the `inv-012-object-consolidation` worktree of rom24-quickmud-python. Your job is **type annotations only** on `mud/handler.py` — change every `ObjectData` annotation to `Object`.
>
> Steps:
> 1. `grep -n "ObjectData" mud/handler.py` — list every occurrence.
> 2. For `affect_enchant`, `affect_to_obj`, `affect_remove_obj`, change `obj: ObjectData` → `obj: Object`. Update imports: drop `ObjectData` from `from mud.models.obj import ObjectData`, add `from mud.models.object import Object` if not present.
> 3. Do not touch logic. Do not touch any other file.
> 4. `python3 -m pytest` — must still report `1 failed, 4686 passed, 4 skipped`.
> 5. `ruff check mud/handler.py` — clean.
> 6. Commit on the consolidation branch: `feat(parity): INV-012/3b — retype handler.py affect helpers ObjectData→Object`.
> 7. Report commit SHA + any anomalies.
>
> Hard constraints: annotations only. Stop and report if anything else needs touching.

---

### Task 3c: Collapse `isinstance(obj, ObjectData)` single-arm at `mud/skills/handlers.py:657`

ROM ref: depends on the function. Read the surrounding context first.

**Files:**
- Modify: `mud/skills/handlers.py:657` area
- Test: new — see Step 2

- [ ] **Step 1: Read context to see what behavior the `ObjectData` arm provides**

Run: `sed -n '640,690p' mud/skills/handlers.py`

Determine: is there an `else` / `elif` arm with different behavior, or is the arm simply a type-guard? Document the finding inline as a code comment in the commit. If logic differs, the merged path must match ROM C — read the relevant `src/*.c` function.

- [ ] **Step 2: Write a failing test in `tests/test_skills_handlers_isinstance_collapse.py`** (new file) asserting the post-merge behavior

Test name: `test_handlers_657_branch_handles_object`. Construct a scenario where the line-657 path executes with an `Object` instance, assert the expected outcome.

- [ ] **Step 3: Run — should FAIL or ERROR**

Run: `python3 -m pytest tests/test_skills_handlers_isinstance_collapse.py::test_handlers_657_branch_handles_object -v`

- [ ] **Step 4: Collapse the branch**

Replace `if isinstance(obj, ObjectData):` with `if isinstance(obj, Object):` (or delete the guard entirely if the arm becomes the default). Adjust the import at the top of the file.

- [ ] **Step 5: Re-run test — must PASS**

- [ ] **Step 6: Full suite**

Run: `python3 -m pytest 2>&1 | tail -3`
Expected: `1 failed, 4687 passed, 4 skipped`.

- [ ] **Step 7: Commit**

```bash
git add mud/skills/handlers.py tests/test_skills_handlers_isinstance_collapse.py
git commit -m "feat(parity): INV-012/3c — collapse skills/handlers.py:657 ObjectData branch"
```

---

### Task 3c-bis: Collapse `mud/skills/handlers.py:4096` single-arm

Same shape as Task 3c. New test: `test_handlers_4096_branch_handles_object`. One commit: `feat(parity): INV-012/3c — collapse skills/handlers.py:4096 ObjectData branch`.

---

### Task 3c-ter: Collapse `mud/skills/handlers.py:5294` single-arm

Same shape. New test: `test_handlers_5294_branch_handles_object`. Commit suffix: `:5294`.

---

### Task 3d: Collapse `(Object, ObjectData)` tuple-filter sites in `mud/skills/handlers.py`

Sites: 2249, 3276, 3417, 5593, 6172, 6636, 6788, 6808, 6811. These are filter patterns like `if not isinstance(target, (Object, ObjectData)):` — safe to simplify to `if not isinstance(target, Object):` because `ObjectData` will be deleted in Phase 5.

**Files:** `mud/skills/handlers.py` (9 sites)

- [ ] **Step 1: Sweep all 9 sites in one pass**

For each line, replace `(Object, ObjectData)` with `Object` and `(ObjectData, Object)` with `Object`.

- [ ] **Step 2: Full suite — no regressions**

Expected: same count as before Task 3d. These are tuple-filter simplifications; behavior unchanged because every instance was already either `Object` or `None`.

- [ ] **Step 3: Commit**

```bash
git add mud/skills/handlers.py
git commit -m "refactor(parity): INV-012/3d — simplify (Object, ObjectData) tuple filters

ObjectData is being deleted in INV-012/5. The tuple unions in 9 filter
sites collapse to plain isinstance(target, Object). Behavior-inert.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

This is the ONLY commit in the entire plan that does not need a failing test first — it is a strict refactor (delete a not-yet-deleted-but-doomed class from a type union). The full suite is the safety net. If the suite drops a test, abort.

---

### Task 3e: Audit `mud/magic/effects.py` for `isinstance(target, Object)` filters

Sites: 5 known (per spec). These will become tautological after Phase 5 but are correct today. **Skip in this session.** Document in the INV-012 row's "Touched by" trail as a deferred follow-up.

No commit for this task.

---

### Task 3f: Delete `_extract_obj` dual-shape branches in `mud/game_loop.py`

Sites: 906, 926, 939, 975 — `getattr(obj, "contained_items", None) or getattr(obj, "contains", [])`.

After Task 1c, `obj.contains` is just `obj.contained_items`, so the dual lookup is redundant. After Task 4 (test fixture migration), there will be no `ObjectData` instances left to receive the second `getattr`. So this commit safely deletes the second arm.

**Files:** `mud/game_loop.py:906, 926, 939, 975`

- [ ] **Step 1: Verify state before edit**

Run: `grep -nE 'contained_items.*contains|contains.*contained_items' mud/game_loop.py`
Expected: exactly 4 matches at the lines above.

- [ ] **Step 2: Sweep — replace at each site**

Replace `getattr(obj, "contained_items", None) or getattr(obj, "contains", [])` with `getattr(obj, "contained_items", [])`. Same for `container`.

- [ ] **Step 3: Full suite**

Expected: same pass/fail count as before — `Object.contains` aliases the same list, so `obj.contained_items` is sufficient.

- [ ] **Step 4: Commit**

```bash
git add mud/game_loop.py
git commit -m "refactor(parity): INV-012/3f — delete ObjectData dual-shape fallbacks in game_loop.py"
```

---

### Task 3g: Straggler sweep

- [ ] **Step 1: Find any remaining `ObjectData` references in `mud/`**

Run: `grep -rn "ObjectData" mud/ --include="*.py" | grep -v "mud/models/obj.py"`
Expected: empty, OR only the test-fixture-migration files queued for Task 4.

If non-empty and not in Task 4's queue, each remaining site gets its own one-commit collapse following the Task 3c template. If empty, skip.

---

## Phase 4: Test fixture migration

### Task 4: Migrate 9 test files from `ObjectData(...)` to `Object(...)`

**Subagent dispatch — up to 4 parallel.** Each agent gets ONE test file in ONE worktree.

Prompt template for each agent (substitute `$TEST_FILE`):

> You are migrating `$TEST_FILE` from `ObjectData(...)` constructors to `Object(...)` constructors as part of INV-012.
>
> Steps:
> 1. **Create your own worktree** via `superpowers:using-git-worktrees` off the `inv-012-object-consolidation` branch (NOT off master). Name it `inv-012-test-$TEST_FILE_BASENAME`. You will produce a single commit there and report the branch back to the parent so it can be merged sequentially.
> 2. `grep -n "ObjectData(" $TEST_FILE` — list every constructor call.
> 3. For each `ObjectData(item_type=X, weight=Y, name=Z, ...)`, rewrite as `Object(instance_id=None, prototype=ObjIndex(item_type=X, weight=Y, name=Z, ...))`. Any post-construct assignments like `obj.in_room = room`, `obj.carried_by = ch`, `obj.in_obj = container` work as-is — the fields were added in Task 1a.
> 4. Imports: drop `from mud.models.obj import ObjectData` (or remove `ObjectData` from a tuple import); add `from mud.models.object import Object` and `from mud.models.obj import ObjIndex` if not present.
> 5. Run `python3 -m pytest $TEST_FILE -v` — every test that passed before must still pass. If any test fails because of a constructor argument the new `ObjIndex` doesn't accept (rare — `ObjIndex` and `ObjectData` share most fields), report the field name back to the parent rather than improvising.
> 6. Run `python3 -m pytest 2>&1 | tail -3` — full-suite count must not drop.
> 7. `ruff check $TEST_FILE`.
> 8. Commit: `chore(test): INV-012/4 — migrate $TEST_FILE_BASENAME from ObjectData to Object`.
> 9. Report: branch name, commit SHA, any anomalies.
>
> Hard constraints: do not modify production code. Do not touch any test file other than `$TEST_FILE`. If a test asserts something specific to `ObjectData` that doesn't translate (e.g. `isinstance(obj, ObjectData)` inside the test body), STOP and report.

**Sequencing:**

- Dispatch 4 agents in parallel for the first batch:
  - `tests/test_music.py`
  - `tests/test_game_loop.py`
  - `tests/test_skills_buffs.py`
  - `tests/test_skills_damage.py`
- Wait for all 4 to report.
- Merge each branch into `inv-012-object-consolidation` sequentially:

```bash
git merge --no-ff <branch-1> -m "Merge INV-012/4 test_music migration"
python3 -m pytest 2>&1 | tail -3   # verify still green
git merge --no-ff <branch-2> -m "Merge INV-012/4 test_game_loop migration"
python3 -m pytest 2>&1 | tail -3
# ... etc
```

If a merge causes a conflict (shouldn't — each agent touches a distinct file), resolve manually before continuing.

- Dispatch second batch (5 more) once first batch is merged:
  - `tests/test_combat_death.py`
  - `tests/test_obj_update_rom_parity.py`
  - `tests/integration/test_music_play.py`
  - `tests/integration/test_update_c_parity.py`
  - `tests/integration/test_compare_critical_gaps.py`

Use 4 parallel + 1 sequential, or 3 + 2 etc. — whichever your dispatcher prefers.

- [ ] **Step 1: Dispatch batch 1 (4 parallel agents)**

- [ ] **Step 2: Merge batch 1 sequentially, running pytest between merges**

- [ ] **Step 3: Dispatch batch 2 (up to 4 parallel agents)**

- [ ] **Step 4: Merge batch 2 sequentially**

- [ ] **Step 5: Final verification after all 9 merges**

Run: `grep -rn "ObjectData(" tests/ --include="*.py" | wc -l`
Expected: `0`.

Run: `python3 -m pytest 2>&1 | tail -3`
Expected: `1 failed, 4686+ passed, 4 skipped` (same baseline; some test counts may shift slightly because individual tests' parametrize ids changed).

---

## Phase 5: Delete `ObjectData` and lock in INV-012

### Task 5: Final consolidation

**Files:**
- Modify: `mud/models/obj.py` (delete `class ObjectData`, update `__all__` if present)
- Modify: `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` (add INV-012 row; close watch-list entry)
- Modify: `CHANGELOG.md` (add `[2.9.0]` section)
- Modify: `pyproject.toml` (bump 2.8.79 → 2.9.0)
- Modify: `docs/sessions/SESSION_STATUS.md` (refresh)
- Create: `docs/sessions/SESSION_SUMMARY_2026-05-24_INV012_OBJECT_CONSOLIDATION.md`

- [ ] **Step 1: Confirm `ObjectData` has zero remaining references outside `mud/models/obj.py`**

Run: `grep -rn "ObjectData" . --include="*.py" --exclude-dir=.venv --exclude-dir=node_modules | grep -v "mud/models/obj.py"`
Expected: empty.

If non-empty, return to Phase 3/4 to clean up before proceeding. Do NOT skip.

- [ ] **Step 2: Delete the class**

Edit `mud/models/obj.py`: remove the entire `@dataclass\nclass ObjectData:` block (lines ~60-104 in current state). Keep `Affect`, `ObjIndex`, `obj_index_registry`, `object_registry`.

- [ ] **Step 3: Update `__all__` if present**

Run: `grep -n "__all__" mud/models/obj.py`
If present, drop `"ObjectData"` from the list.

- [ ] **Step 4: Add INV-012 row to the tracker**

Edit `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`. Insert immediately after the INV-011 row (numerical order):

```
| INV-012 | OBJECT-LIST-CANONICAL | `src/db.c:create_object` appends to `object_list`; `src/handler.c:2051 extract_obj` removes (recursively via 2063-2067 for contents). One canonical instance list; one `OBJ_DATA` struct. | (a) `mud/models/object.py:Object` is the only runtime class; `mud/models/obj.py:ObjectData` deleted in 2.9.0. (b) `mud/spawning/obj_spawner.py:spawn_object` appends to `mud.models.obj.object_registry` before returning; `mud/game_loop.py:_extract_obj` removes (recursively). (c) ROM-named fields `in_room`, `in_obj`, `carried_by` live on `Object` as dataclass fields; `pIndexData` and `contains` as `@property` aliases of `prototype` / `contained_items`. | `tests/integration/test_inv012_object_list_canonical.py` | ✅ ENFORCED |
```

Also: in the watch-list section, strike through the "Dual `Object` / `ObjectData` classes" entry — replace with `~~Dual `Object` / `ObjectData` classes...~~ **Closed as INV-012 in 2.9.0.**`

- [ ] **Step 5: Bump version**

Edit `pyproject.toml`: `version = "2.8.79"` → `version = "2.9.0"`.

- [ ] **Step 6: CHANGELOG entry**

Edit `CHANGELOG.md`. Add under `## [Unreleased]`:

```markdown
## [2.9.0]

### Added
- **`INV-012` — OBJECT-LIST-CANONICAL locked in** (`docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`, `tests/integration/test_inv012_object_list_canonical.py`): single canonical `Object` runtime class. `mud.models.obj.ObjectData` deleted. `object_registry` is now populated at spawn (`mud/spawning/obj_spawner.py:spawn_object`) and drained at extract (`mud/game_loop.py:_extract_obj`, including recursive contents per ROM `src/handler.c:2063-2067`). New ROM-named fields on `Object`: `in_room`, `in_obj`, `carried_by` (dataclass fields), `pIndexData` and `contains` (`@property` aliases of `prototype` / `contained_items`).

### Fixed
- **`object_registry` was never populated** (now-live in production): every iteration over the global instance list was a no-op before this consolidation, silently disabling locate-object spells (`mud/world/obj_find.py:get_obj_world`, `mud/magic/effects.py`), mobprog oload triggers (`mud/mobprog.py`), global object scans (`mud/skills/handlers.py`), music decay (`mud/music/__init__.py`), and object decay tick (`mud/game_loop.py:object_update`). Smoke tests for `get_obj_world` and `object_update` ship with INV-012; per-system tests are out-of-scope follow-ups.

### Changed
- ~12 `isinstance(target, ObjectData)` / `isinstance(target, (Object, ObjectData))` branches across `mud/skills/handlers.py` and `mud/game_loop.py` collapsed to `Object`-only. ~35 test fixtures across 9 test files migrated from `ObjectData(...)` to `Object(instance_id=None, prototype=ObjIndex(...))`.
```

- [ ] **Step 7: Run the full verification gate**

```bash
python3 -m pytest 2>&1 | tail -3
ruff check . 2>&1 | tail -5
python3 -m pytest tests/integration/test_inv012_object_list_canonical.py -v
```

Expected:
- pytest: `1 failed, 4686+ passed, 4 skipped` (pre-existing failure unchanged).
- ruff: clean.
- INV-012 file: all tests green.

- [ ] **Step 8: Commit Phase 5**

```bash
git add mud/models/obj.py docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md CHANGELOG.md pyproject.toml
git commit -m "$(cat <<'EOF'
feat(parity): INV-012/5 — delete ObjectData, lock in OBJECT-LIST-CANONICAL (2.9.0)

Consolidation complete. mud.models.obj.ObjectData removed. The Object
class in mud.models.object is the only runtime object class. Container
fields (in_room, in_obj, carried_by) and ROM-faithful accessors
(pIndexData, contains) live on Object directly.

Tracker: INV-012 OBJECT-LIST-CANONICAL added to cross-file invariants;
dual-class watch-list entry struck through.

Production payoffs newly live (previously no-op against empty
object_registry):

- Locate-object spells (get_obj_world, magic.locate_object)
- Mobprog oload triggers
- Global object scans (skills.handlers)
- Music and object decay ticks

Smoke tests for get_obj_world and object_update gate INV-012;
per-system end-to-end tests deferred as out-of-scope follow-ups.

Version: 2.8.79 → 2.9.0 (minor — new behaviors light up).

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 9: Session handoff via `/rom-session-handoff`**

Invoke `rom-session-handoff` skill. It will:
- Write `docs/sessions/SESSION_SUMMARY_2026-05-24_INV012_OBJECT_CONSOLIDATION.md`
- Refresh `docs/sessions/SESSION_STATUS.md` to point at the new summary, mark version 2.9.0, count INVs at 12.
- (CHANGELOG, pyproject.toml are already updated; the skill will confirm.)

Commit the handoff:

```bash
git add docs/sessions/
git commit -m "docs(session): INV-012 OBJECT-LIST-CANONICAL session handoff"
```

---

## Verification gate (final, before declaring done)

- [ ] `python3 -m pytest 2>&1 | tail -3` → `1 failed, 4686+ passed, 4 skipped`. The 1 failure is the pre-existing `test_wait_and_daze_decrement_on_violence_pulse` — unchanged.
- [ ] `ruff check .` → clean.
- [ ] `python3 -m pytest tests/integration/test_inv012_object_list_canonical.py -v` → all green.
- [ ] `grep -rn "ObjectData" mud/ tests/ --include="*.py"` → 0 results.
- [ ] `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` shows INV-012 ✅ ENFORCED; watch-list entry struck through.
- [ ] `pyproject.toml` version is `2.9.0`.
- [ ] `CHANGELOG.md` has a `[2.9.0]` section.
- [ ] `docs/sessions/SESSION_STATUS.md` points at the INV-012 summary, version 2.9.0.

Once all green, **stop and report to the user**. Do **not** push to `origin/master` without explicit per-cluster approval (per AGENTS.md). The branch sits ready for review / merge / push.

---

## Rollback plan

Abort points and recovery procedures, by phase:

| If broken during… | Recovery |
|--------------------|----------|
| **Phase 1 (1a/1b/1c)** | `git reset --hard master` in the worktree, ditch the branch. Cost: minutes. Spec stays in master. |
| **Phase 2 (registry populate)** | Same: `git reset --hard master`. The new test file is unreachable. Cost: minutes. |
| **Phase 3a/3b (annotation sweep)** | Cherry-pick the Phase 1 + 2 commits onto a fresh branch off master and stop. Phase 3 annotation work is throwaway. Cost: ~10 minutes. |
| **Phase 3c–3g (isinstance collapse)** | Revert the specific isinstance-collapse commit (`git revert <sha>`); the rest of Phase 3 stands. Cost: minutes. |
| **Phase 4 (test fixture migration)** | Each test-file migration is its own commit; revert only the offending one. The rest of Phase 4 stands. Cost: minutes per file. |
| **Phase 5 (ObjectData deletion)** | `git revert` the deletion commit. ObjectData class returns; tests reference Object (Task 4 migrations stay green); registry stays populated (Task 2). Cost: minutes. |

**Hard abort criteria** (stop the consolidation entirely and surface to user):
- A previously-passing test fails because `object_registry` is now non-empty (real bug surfaced — handle outside this plan).
- Any subagent reports they had to invent behavior to make a migration work. Surface for human judgment.
- The pre-existing `test_wait_and_daze_decrement_on_violence_pulse` failure changes shape or stack trace — investigate before continuing.

**Soft abort criteria** (pause, sync with user, decide):
- The honest commit count climbs past 25. The plan said 15–25; if we're at 26+, something is wrong with the decomposition.
- A subagent's parallel work conflicts in a non-trivial way. Sequence the remaining work instead of paralleling it.

---

## Self-review notes

- **Spec coverage:** Every numbered commit in the spec (1a, 1b, 1c, 2, 3a–3g, 4, 5) has a corresponding Task above with concrete steps. The smoke-test requirement (get_obj_world + object_update) is bundled into Task 2.
- **Placeholder scan:** Task 3c's "Read context to determine if there's an `else` arm with different behavior" is open-ended — but it has to be, because the merge decision depends on what `src/*.c` says about that path. The plan tells the engineer exactly where to look (`src/*.c` for ROM ref) and what to do (write test, then collapse). That is concrete-enough for a TDD-disciplined operator; making it more concrete without reading those lines first would be guessing.
- **Type consistency:** `Object`, `ObjIndex`, `object_registry`, `_extract_obj`, `spawn_object` referenced consistently. `prototype` (Python-ish) and `pIndexData` (ROM) both used per Task 1b's contract.
- **Subagent prompts:** Task 3a, 3b, and Task 4's batch use explicit prompts with hard constraints, stop-and-report rules, and merge protocols.
- **Rollback ladder:** present at every phase, with clear cost estimates.
- **Push gate:** explicit at the end — no auto-push to master.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-24-object-objectdata-consolidation.md`. Two execution options:

1. **Subagent-Driven (recommended)** — REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`. Fresh subagent per task; two-stage review between tasks. Best fit because Tasks 3a/3b and Task 4 are explicitly parallel.
2. **Inline Execution** — REQUIRED SUB-SKILL: `superpowers:executing-plans`. Batch execution with checkpoints in the current session.

Which approach?
