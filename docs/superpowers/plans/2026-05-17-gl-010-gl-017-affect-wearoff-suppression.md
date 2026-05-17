# GL-010 / GL-017 Affect Wear-Off Suppression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close `GL-010` and `GL-017` by matching ROM `src/update.c` same-type wear-off suppression for character and object affect ticking.

**Architecture:** ROM suppresses `msg_off` / `msg_obj` when the next affect in the linked list has the same `type` and a non-expired duration. Python already keeps ordered `affected` lists for both characters and objects, so this can be implemented by driving expiration from those lists and only emitting wear-off text when the next affect does not keep the same spell active. No list-model rewrite is required.

**Tech Stack:** Python 3.12, pytest, ruff, ROM `src/update.c`, GitNexus CLI

---

## File Map

- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/affects/engine.py`
  - Character spell-effect ticking and wear-off message emission.
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/game_loop.py`
  - Object affect ticking and wear-off broadcast suppression.
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/UPDATE_C_AUDIT.md`
  - Mark `GL-010` and `GL-017` fixed with test references.
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
  - Update `update.c` remaining-gap notes.
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_STATUS.md`
  - Point to the new summary and next target.
- Create: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_SUMMARY_2026-05-17_GL_010_GL_017_AFFECT_WEAROFF_SUPPRESSION_CLOSED.md`
  - Session handoff summary.
- Test: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_affects.py`
  - Character same-type wear-off suppression regression.
- Test: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_obj_update_rom_parity.py`
  - Object same-type wear-off suppression regression.

### Task 1: Lock character wear-off suppression with a failing test

**Files:**
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_affects.py`
- Reference: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/src/update.c:762-786`

- [ ] **Step 1: Write the failing test**

```python
def test_tick_spell_effects_suppresses_wear_off_when_same_spell_remains_active():
    ch = Character(level=20)
    ch.affected = [
        AffectData(type="armor", level=20, duration=0, location=17, modifier=-20, bitvector=0),
        AffectData(type="armor", level=20, duration=2, location=17, modifier=-20, bitvector=0),
    ]
    ch.spell_effects["armor"] = SpellEffect(
        name="armor",
        duration=0,
        level=20,
        ac_mod=-20,
        wear_off_message="You feel less protected.",
    )

    messages = tick_spell_effects(ch)

    assert messages == []
    assert "armor" in ch.spell_effects
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest -q /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_affects.py -k same_spell_remains_active`
Expected: FAIL because current code removes the spell effect and emits the wear-off message.

### Task 2: Lock object wear-off suppression with a failing test

**Files:**
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_obj_update_rom_parity.py`
- Reference: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/src/update.c:939-957`

- [ ] **Step 1: Write the failing test**

```python
def test_object_affect_wear_off_suppressed_when_same_type_still_active(monkeypatch):
    obj = create_test_object(ItemType.WEAPON, timer=10)
    obj.affected = [
        Affect(where=0, type=1, duration=0, modifier=10, location=1, bitvector=0, level=10),
        Affect(where=0, type=1, duration=2, modifier=10, location=1, bitvector=0, level=10),
    ]
    seen: list[tuple[object, object]] = []
    monkeypatch.setattr("mud.game_loop._broadcast_object_wear_off", lambda obj_arg, aff_arg: seen.append((obj_arg, aff_arg)))

    _tick_object_affects(obj)

    assert seen == []
    assert len(obj.affected) == 1
    assert obj.affected[0].duration == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest -q /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_obj_update_rom_parity.py -k same_type_still_active`
Expected: FAIL because current code broadcasts the wear-off message unconditionally before removal.

### Task 3: Implement minimal ROM-parity fix

**Files:**
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/affects/engine.py`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/game_loop.py`

- [ ] **Step 1: Update character affect ticking to inspect ordered `affected` entries**

```python
# Conceptual shape only; implementation must preserve existing public API.
for index, paf in enumerate(list(character.affected)):
    next_paf = ordered[index + 1] if index + 1 < len(ordered) else None
    if paf.duration > 0:
        ...
    elif paf.duration == 0:
        suppress = (
            next_paf is not None
            and next_paf.type == paf.type
            and int(next_paf.duration or 0) <= 0
        )
        ...
```

Use the actual ROM rule from `src/update.c`: emit `msg_off` only when next affect is absent, or next affect type differs, or next affect duration is **greater than 0**.

- [ ] **Step 2: Keep legacy `spell_effects` dict synchronized without over-removing**

```python
# When one expired AffectData is removed but another same-type AffectData remains,
# do not call remove_spell_effect(name). Only drop the single expired AffectData entry.
```

- [ ] **Step 3: Apply the same suppression rule to `_tick_object_affects()`**

```python
next_affect = affects[index + 1] if index + 1 < len(affects) else None
should_emit = (
    next_affect is None
    or next_affect.type != affect.type
    or int(next_affect.duration or 0) > 0
)
```

- [ ] **Step 4: Run the focused tests**

Run:
- `./venv/bin/python -m pytest -q /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_affects.py -k same_spell_remains_active`
- `./venv/bin/python -m pytest -q /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_obj_update_rom_parity.py -k same_type_still_active`
Expected: PASS.

### Task 4: Verify adjacent behavior and update docs

**Files:**
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/UPDATE_C_AUDIT.md`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_STATUS.md`
- Create: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_SUMMARY_2026-05-17_GL_010_GL_017_AFFECT_WEAROFF_SUPPRESSION_CLOSED.md`

- [ ] **Step 1: Run the focused parity slice**

Run:
- `./venv/bin/python -m pytest -q /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_affects.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_obj_update_rom_parity.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_update_c_parity.py -k 'wear_off or affect or obj_update or point_pulse or plague or poison'`
- `./venv/bin/python -m ruff check /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/affects/engine.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/game_loop.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_affects.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_obj_update_rom_parity.py`
Expected: clean targeted test pass and clean lint.

- [ ] **Step 2: Update the audit records**

Record `GL-010` and `GL-017` as fixed with the new test names and remove the deferred architectural note.

- [ ] **Step 3: Write the session summary**

Summarize ROM references, code changes, exact verification commands, and the next recommended ROM-source-first slice.

## Self-Review

- Spec coverage: covers both deferred rows (`GL-010`, `GL-017`), code, tests, audit docs, and session docs.
- Placeholder scan: no TODO markers or undefined commands remain.
- Type consistency: plan uses existing `AffectData`, `SpellEffect`, and `Affect` structures already present in the repo.

## Execution Handoff

Plan complete and saved to `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/superpowers/plans/2026-05-17-gl-010-gl-017-affect-wearoff-suppression.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
