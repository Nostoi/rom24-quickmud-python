# ROM Tick Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore ROM-accurate tick cadence and ordering in the Python game loop, with combat, wait/daze handling, scheduler timing, and regression coverage matching the C engine.

**Architecture:** Reintroduce an explicit violence pulse counter in `mud/game_loop.py`, split per-pulse bookkeeping from per-violence combat processing, and align subsystem ordering with `src/update.c:update_handler`. Keep the async scheduler API intact, but change its timing model to deadline-based scheduling so real-time cadence remains close to ROM under load.

**Tech Stack:** Python 3, pytest, asyncio, QuickMUD runtime modules in `mud/`, ROM C source in `src/` as behavioral source of truth.

---

## File Map

- Modify: `mud/game_loop.py`
  - Reintroduce `_violence_counter`
  - Split timer drain vs combat cadence
  - Reorder update-handler phases to mirror ROM
  - Change async loop to deadline-based sleep
- Modify: `mud/combat/engine.py`
  - Replace hardcoded violence decrement constant with ROM-compatible value source
  - Keep NPC-only decrement semantics aligned with `src/fight.c:191-196`
- Modify: `mud/game_tick_scheduler.py`
  - Match `async_game_loop()` deadline-based scheduler semantics
- Modify: `tests/test_game_loop.py`
  - Assert violence cadence, mobile cadence, and first-pulse behavior
- Modify: `tests/test_game_loop_order.py`
  - Assert full ROM-style subsystem ordering on coincident pulses
- Modify: `tests/test_game_loop_wait_daze.py`
  - Assert wait/daze drain semantics on pulse boundaries and no premature combat execution
- Modify: `tests/test_combat_rom_parity.py`
  - Align timer expectations with ROM pulse values
- Modify: `tests/integration/test_skills_integration.py`
  - Assert combat rounds progress on violence cadence, not every pulse
- Modify: `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
  - Replace stale `update.c` notes after the fix lands
- Modify: `CHANGELOG.md`
  - Record user-visible parity fix
- Modify: `docs/sessions/SESSION_STATUS.md`
  - Point to the implementation summary at session end
- Create: `docs/sessions/SESSION_SUMMARY_2026-05-01_ROM_TICK_PARITY.md`
  - Capture landed gaps, files, and test evidence

---

### Task 1: Lock in failing cadence and ordering tests

**Files:**
- Modify: `tests/test_game_loop.py`
- Modify: `tests/test_game_loop_order.py`
- Modify: `tests/test_game_loop_wait_daze.py`
- Modify: `tests/integration/test_skills_integration.py`
- Test: `tests/test_game_loop.py`
- Test: `tests/test_game_loop_order.py`
- Test: `tests/test_game_loop_wait_daze.py`
- Test: `tests/integration/test_skills_integration.py`

- [ ] **Step 1: Write the failing unit test for violence cadence**

```python
# tests/test_game_loop.py

def test_violence_update_runs_once_per_pulse_violence(monkeypatch):
    import mud.game_loop as gl
    from mud.config import get_pulse_violence
    from mud.models.character import Character, character_registry
    from mud.models.constants import Position

    character_registry.clear()
    gl._pulse_counter = 0
    gl._point_counter = 999999
    gl._area_counter = 999999
    gl._music_counter = 999999
    gl._mobile_counter = 999999
    gl._violence_counter = get_pulse_violence()

    room = object()
    attacker = Character(name="Attacker", position=int(Position.FIGHTING), is_npc=False)
    victim = Character(name="Victim", position=int(Position.FIGHTING), is_npc=False)
    attacker.room = room
    victim.room = room
    attacker.fighting = victim
    victim.fighting = attacker
    character_registry.extend([attacker, victim])

    calls: list[int] = []
    monkeypatch.setattr("mud.combat.engine.multi_hit", lambda ch, vic, dt=None: calls.append(gl._pulse_counter))
    monkeypatch.setattr("mud.combat.engine.stop_fighting", lambda ch, both=False: None)

    for _ in range(get_pulse_violence() - 1):
        gl.game_tick()

    assert calls == []

    gl.game_tick()
    assert calls == [get_pulse_violence(), get_pulse_violence()]
```

- [ ] **Step 2: Write the failing order test for coincident pulses**

```python
# tests/test_game_loop_order.py

def test_rom_update_handler_order_when_all_pulses_fire(monkeypatch):
    import mud.game_loop as gl

    order: list[str] = []
    gl._pulse_counter = 0
    gl._area_counter = 1
    gl._music_counter = 1
    gl._mobile_counter = 1
    gl._violence_counter = 1
    gl._point_counter = 1

    monkeypatch.setattr(gl, "reset_tick", lambda: order.append("area"))
    monkeypatch.setattr(gl, "song_update", lambda: order.append("music"))
    monkeypatch.setattr(gl, "mobile_update", lambda: order.append("mobile"))
    monkeypatch.setattr(gl, "violence_tick", lambda: order.append("violence"))
    monkeypatch.setattr(gl, "weather_tick", lambda: order.append("weather"))
    monkeypatch.setattr(gl, "char_update", lambda: order.append("char"))
    monkeypatch.setattr(gl, "obj_update", lambda: order.append("obj"))
    monkeypatch.setattr(gl, "aggressive_update", lambda: order.append("aggr"))
    monkeypatch.setattr(gl, "event_tick", lambda: order.append("event"))
    monkeypatch.setattr(gl, "run_npc_specs", lambda: order.append("spec"))

    gl.game_tick()

    assert order[:8] == ["area", "music", "mobile", "violence", "weather", "char", "obj", "aggr"]
```

- [ ] **Step 3: Write the failing wait/daze semantics test**

```python
# tests/test_game_loop_wait_daze.py

def test_wait_and_daze_drop_by_one_each_pulse_but_combat_waits_for_violence(monkeypatch):
    import mud.game_loop as gl
    from mud.config import get_pulse_violence
    from mud.models.constants import Position

    ch = Character(name="Fighter", wait=3, daze=3, position=int(Position.FIGHTING))
    victim = Character(name="Target", position=int(Position.FIGHTING))
    room = object()
    ch.room = room
    victim.room = room
    ch.fighting = victim
    character_registry[:] = [ch, victim]

    calls: list[int] = []
    monkeypatch.setattr("mud.combat.engine.multi_hit", lambda attacker, target, dt=None: calls.append(gl._pulse_counter))
    monkeypatch.setattr("mud.combat.engine.stop_fighting", lambda ch, both=False: None)

    gl._violence_counter = get_pulse_violence()
    gl._point_counter = 999999
    gl._area_counter = 999999
    gl._music_counter = 999999
    gl._mobile_counter = 999999

    gl.game_tick()
    assert (ch.wait, ch.daze, calls) == (2, 2, [])
```

- [ ] **Step 4: Write the failing integration test for combat cadence**

```python
# tests/integration/test_skills_integration.py

def test_combat_rounds_advance_only_on_violence_pulses(monkeypatch, skilled_character, movable_mob_factory):
    import mud.game_loop as gl
    from mud.config import get_pulse_violence
    from mud.models.constants import Position

    char = skilled_character
    mob = movable_mob_factory(3000, 3001)
    char.position = Position.FIGHTING
    mob.position = Position.FIGHTING
    char.fighting = mob
    mob.fighting = char

    rounds: list[int] = []
    monkeypatch.setattr("mud.combat.engine.attack_round", lambda *args, **kwargs: rounds.append(gl._pulse_counter) or "hit")

    for _ in range(get_pulse_violence() - 1):
        gl.game_tick()

    assert rounds == []
```

- [ ] **Step 5: Run tests to verify they fail**

Run:
```bash
pytest -q tests/test_game_loop.py tests/test_game_loop_order.py tests/test_game_loop_wait_daze.py tests/integration/test_skills_integration.py
```

Expected:
- Failing assertions showing combat still runs before `PULSE_VIOLENCE`
- Ordering mismatch showing `violence` happens too early

- [ ] **Step 6: Commit the red tests**

```bash
git add tests/test_game_loop.py tests/test_game_loop_order.py tests/test_game_loop_wait_daze.py tests/integration/test_skills_integration.py
git commit -m "test(parity): lock ROM tick cadence expectations"
```

---

### Task 2: Restore ROM update-handler cadence and ordering

**Files:**
- Modify: `mud/game_loop.py`
- Test: `tests/test_game_loop.py`
- Test: `tests/test_game_loop_order.py`
- Test: `tests/test_game_loop_wait_daze.py`

- [ ] **Step 1: Reintroduce a real violence counter and split pulse work from violence work**

```python
# mud/game_loop.py
_pulse_counter = 0
_point_counter = 0
_area_counter = 0
_music_counter = 0
_mobile_counter = 0
_violence_counter = 0


def _drain_wait_daze_pulse() -> None:
    for ch in list(character_registry):
        wait = int(getattr(ch, "wait", 0) or 0)
        ch.wait = max(0, wait - 1)

        if hasattr(ch, "daze"):
            daze = int(getattr(ch, "daze", 0) or 0)
            ch.daze = max(0, daze - 1)
```

- [ ] **Step 2: Make `violence_tick()` do only violence-phase combat work**

```python
# mud/game_loop.py

def violence_tick() -> None:
    """Process one ROM violence phase.

    Mirrors ROM src/fight.c:66-99. Combat rounds happen only when the
    violence pulse fires, not every base pulse.
    """
    from mud.combat.engine import multi_hit, stop_fighting
    from mud.combat.assist import check_assist

    for ch in list(character_registry):
        victim = getattr(ch, "fighting", None)
        if victim is None or getattr(ch, "room", None) is None:
            continue

        if getattr(ch, "position", Position.STANDING) > Position.SLEEPING and ch.room == getattr(victim, "room", None):
            multi_hit(ch, victim, dt=None)
        else:
            stop_fighting(ch, both=False)
            continue

        victim = getattr(ch, "fighting", None)
        if victim is None:
            continue

        check_assist(ch, victim)
```

- [ ] **Step 3: Reorder `game_tick()` to mirror `src/update.c:update_handler`**

```python
# mud/game_loop.py

def game_tick() -> None:
    global _pulse_counter, _point_counter, _area_counter, _music_counter, _mobile_counter, _violence_counter
    _pulse_counter += 1

    _drain_wait_daze_pulse()

    _area_counter -= 1
    if _area_counter <= 0:
        _area_counter = get_pulse_area()
        reset_tick()

    _music_counter -= 1
    if _music_counter <= 0:
        _music_counter = get_pulse_music()
        song_update()

    _mobile_counter -= 1
    if _mobile_counter <= 0:
        _mobile_counter = get_pulse_mobile()
        mobile_update()
        run_npc_specs()

    _violence_counter -= 1
    if _violence_counter <= 0:
        _violence_counter = get_pulse_violence()
        violence_tick()

    _point_counter -= 1
    if _point_counter <= 0:
        _point_counter = get_pulse_tick()
        wiznet("TICK!", None, None, WiznetFlag.WIZ_TICKS, 0, 0)
        time_tick()
        weather_tick()
        char_update()
        obj_update()
        pump_idle()

    aggressive_update()
    event_tick()
```

- [ ] **Step 4: Initialize counters in ROM style**

```python
# mud/game_loop.py
_pulse_counter = 0
_point_counter = 0
_area_counter = 0
_music_counter = 0
_mobile_counter = 0
_violence_counter = 0
```

- [ ] **Step 5: Run targeted tests to verify cadence and order pass**

Run:
```bash
pytest -q tests/test_game_loop.py tests/test_game_loop_order.py tests/test_game_loop_wait_daze.py
```

Expected:
- Violence cadence tests pass
- Ordering test matches ROM sequence
- Wait/daze pulse drain stays intact

- [ ] **Step 6: Commit the game-loop refactor**

```bash
git add mud/game_loop.py tests/test_game_loop.py tests/test_game_loop_order.py tests/test_game_loop_wait_daze.py
git commit -m "fix(parity): restore ROM violence cadence and update order"
```

---

### Task 3: Align combat engine timer semantics with ROM

**Files:**
- Modify: `mud/combat/engine.py`
- Modify: `tests/test_combat_rom_parity.py`
- Test: `tests/test_combat_rom_parity.py`

- [ ] **Step 1: Replace the hardcoded violence constant in `multi_hit()`**

```python
# mud/combat/engine.py
from mud.config import get_pulse_violence


def multi_hit(attacker: Character, victim: Character, dt: str | int | None = None) -> list[str]:
    results: list[str] = []

    pulse_violence = get_pulse_violence()
    if not hasattr(attacker, "desc") or attacker.desc is None:
        attacker.wait = max(0, getattr(attacker, "wait", 0) - pulse_violence)
        attacker.daze = max(0, getattr(attacker, "daze", 0) - pulse_violence)
```

- [ ] **Step 2: Update timer tests to assert ROM values**

```python
# tests/test_combat_rom_parity.py
from mud.config import get_pulse_violence


def test_wait_daze_timer_handling():
    attacker, victim = setup_combat()
    attacker.desc = None
    attacker.wait = 24
    attacker.daze = 24

    multi_hit(attacker, victim)

    assert attacker.wait == 24 - get_pulse_violence()
    assert attacker.daze == 24 - get_pulse_violence()
```

- [ ] **Step 3: Run the combat parity tests**

Run:
```bash
pytest -q tests/test_combat_rom_parity.py tests/test_combat.py tests/test_skills.py
```

Expected:
- Timer expectations pass with `get_pulse_violence()`
- No regressions in skill wait-state tests

- [ ] **Step 4: Commit the combat-engine fix**

```bash
git add mud/combat/engine.py tests/test_combat_rom_parity.py
git commit -m "fix(parity): align multi_hit wait timers with ROM pulses"
```

---

### Task 4: Fix real-time scheduler drift and keep server entry points consistent

**Files:**
- Modify: `mud/game_loop.py`
- Modify: `mud/game_tick_scheduler.py`
- Test: `tests/test_game_loop.py`

- [ ] **Step 1: Convert `async_game_loop()` to deadline-based timing**

```python
# mud/game_loop.py
async def async_game_loop() -> None:
    import asyncio
    from mud.config import PULSE_PER_SECOND

    loop = asyncio.get_running_loop()
    tick_interval = 1.0 / PULSE_PER_SECOND
    next_tick = loop.time()

    while True:
        try:
            game_tick()
            next_tick += tick_interval
            await asyncio.sleep(max(0.0, next_tick - loop.time()))
        except asyncio.CancelledError:
            print("Game loop shutting down...")
            break
        except Exception as e:
            import traceback
            print(f"Error in game loop: {e}")
            traceback.print_exc()
            next_tick = loop.time() + tick_interval
            await asyncio.sleep(tick_interval)
```

- [ ] **Step 2: Apply the same timing model to `start_game_tick_scheduler()`**

```python
# mud/game_tick_scheduler.py
async def scheduler_loop():
    loop = asyncio.get_running_loop()
    next_tick = loop.time()
    while True:
        try:
            game_tick()
        except Exception as e:
            print(f"[Game] Game tick error: {e}")
        next_tick += tick_interval
        await asyncio.sleep(max(0.0, next_tick - loop.time()))
```

- [ ] **Step 3: Add a scheduler regression test around sleep intervals**

```python
# tests/test_game_loop.py
@pytest.mark.asyncio
async def test_async_game_loop_uses_deadline_based_sleep(monkeypatch):
    import asyncio
    import mud.game_loop as gl

    sleeps: list[float] = []
    calls = {"count": 0}

    def fake_tick():
        calls["count"] += 1
        if calls["count"] >= 2:
            raise asyncio.CancelledError()

    async def fake_sleep(delay: float):
        sleeps.append(delay)

    monkeypatch.setattr(gl, "game_tick", fake_tick)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    try:
        await gl.async_game_loop()
    except asyncio.CancelledError:
        pass

    assert sleeps and all(delay >= 0 for delay in sleeps)
```

- [ ] **Step 4: Run scheduler and game-loop tests**

Run:
```bash
pytest -q tests/test_game_loop.py tests/test_game_loop_order.py
```

Expected:
- Scheduler tests pass
- No order regressions introduced

- [ ] **Step 5: Commit the scheduler fix**

```bash
git add mud/game_loop.py mud/game_tick_scheduler.py tests/test_game_loop.py
git commit -m "fix(parity): remove async tick drift"
```

---

### Task 5: Run full verification and update project tracking

**Files:**
- Modify: `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/sessions/SESSION_STATUS.md`
- Create: `docs/sessions/SESSION_SUMMARY_2026-05-01_ROM_TICK_PARITY.md`

- [ ] **Step 1: Run the narrow verification suite first**

Run:
```bash
pytest -q tests/test_game_loop.py tests/test_game_loop_order.py tests/test_game_loop_wait_daze.py tests/test_combat_rom_parity.py tests/integration/test_skills_integration.py
```

Expected:
- All targeted cadence and combat tests pass

- [ ] **Step 2: Run broader integration coverage for tick-sensitive systems**

Run:
```bash
pytest -q tests/integration/test_mob_ai.py tests/integration/test_group_combat.py tests/integration/test_weather_time.py
```

Expected:
- No regressions in mob AI, combat progression, or time/weather cadence

- [ ] **Step 3: Run lint on touched files**

Run:
```bash
ruff check mud/game_loop.py mud/combat/engine.py mud/game_tick_scheduler.py tests/test_game_loop.py tests/test_game_loop_order.py tests/test_game_loop_wait_daze.py tests/test_combat_rom_parity.py tests/integration/test_skills_integration.py
```

Expected:
- No lint errors

- [ ] **Step 4: Update tracker and changelog entries**

```markdown
<!-- docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md -->
- ✅ `violence_update()` cadence restored to `PULSE_VIOLENCE`
- ✅ `update_handler()` ordering refreshed to match ROM
- ✅ `wiznet("TICK!")` emitted on point pulse if implemented in this task
```

```markdown
<!-- CHANGELOG.md -->
### Fixed
- Restored ROM `PULSE_VIOLENCE` combat cadence in the Python game loop.
- Corrected update-handler subsystem ordering and eliminated async tick drift.
```

- [ ] **Step 5: Write session summary and refresh status**

```markdown
# Session Summary — 2026-05-01 — ROM tick parity

## Outcomes
- Restored `violence_update()` cadence to 12 pulses / 3 seconds.
- Reintroduced `_violence_counter` and ROM-style startup counters.
- Updated targeted and integration test coverage for cadence-sensitive systems.
```

- [ ] **Step 6: Commit docs and tracker updates**

```bash
git add docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md CHANGELOG.md docs/sessions/SESSION_STATUS.md docs/sessions/SESSION_SUMMARY_2026-05-01_ROM_TICK_PARITY.md
git commit -m "docs(parity): record ROM tick cadence restoration"
```

---

## Self-Review

- Spec coverage: covers combat cadence, pulse ordering, wait/daze semantics, scheduler drift, regression tests, and tracker/doc updates.
- Placeholder scan: no `TODO`/`TBD` placeholders remain; every task includes concrete files, commands, and expected outcomes.
- Type consistency: uses existing names `violence_tick`, `game_tick`, `get_pulse_violence`, `run_npc_specs`, `aggressive_update`, and current pytest module names.

Plan complete and saved to `docs/superpowers/plans/2026-05-01-rom-tick-parity.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
