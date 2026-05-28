# Differential Testing Harness (ROM C ⇄ Python) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local golden-trace capture/replay harness that runs the Python port and the instrumented ROM 2.4b6 C engine through identical scripted scenarios and diffs observable state + output, so parity divergences surface mechanically.

**Architecture:** Two phases sharing one snapshot schema. *Capture* (occasional, needs a C build) drives an additively-instrumented C binary over stdin and records per-step JSON traces to committed golden files. *Replay* (every run, pure Python) drives the Python engine through the same scenario, snapshots its state, normalizes both sides identically, and asserts equality. v1 is a deterministic smoke slice (no-RNG commands).

**Tech Stack:** Python 3.12, pytest, stdlib `dataclasses`/`json`/`subprocess`; C (gcc, ROM 2.4 `src/`), a separate `src/Makefile.diffshim`. Reference design: `docs/superpowers/specs/2026-05-28-differential-testing-harness-design.md`.

**Scope note:** v1 = movement + object handling only. Combat/RNG/prompt/shops/mob-ticks are explicitly out (later slices). No CI, no live dual-drive, no FFI.

---

## File structure

| Path | Responsibility | Phase |
|------|----------------|-------|
| `tools/diff_harness/__init__.py` | package marker | — |
| `tools/diff_harness/schema.py` | snapshot dataclasses + JSON (de)serialization — the shared contract | both |
| `tools/diff_harness/compare.py` | `normalize()` + `diff_traces()` + report rendering | both |
| `tools/diff_harness/pysnap.py` | build a `StepSnap` from live Python engine state | replay |
| `tools/diff_harness/scenario.py` | load a scenario JSON (seed, start room, char, watch-set, steps) | both |
| `tools/diff_harness/capture.py` | drive the C binary, write golden traces | capture |
| `tools/diff_harness/scenarios/*.json` | hand-written scenarios | both |
| `tools/diff_harness/README.md` | re-capture + run workflow | docs |
| `src/diff_shim/diffmain.c` | additive C: deterministic boot+seed, stdin driver, `__snapshot` command | capture |
| `src/Makefile.diffshim` | builds ROM objects + shim with `-DOLD_RAND` | capture |
| `tests/data/golden/diff/*.golden.json` | committed C reference traces | replay |
| `tests/test_diff_harness_unit.py` | unit tests for schema/compare/pysnap/scenario | both |
| `tests/test_differential_smoke.py` | the replay integration test | replay |

The Python modules (`schema`, `compare`, `pysnap`, `scenario`) are fully TDD-able with no C dependency and are built first (Tasks 1–4). The C shim + capture (Tasks 5–7) are the risky part and are verified by running the binary. The replay test (Task 8) ties it together. README + finalize last (Tasks 9–10).

---

## Task 1: Snapshot schema

**Files:**
- Create: `tools/diff_harness/__init__.py` (empty)
- Create: `tools/diff_harness/schema.py`
- Test: `tests/test_diff_harness_unit.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_diff_harness_unit.py
from __future__ import annotations

from tools.diff_harness.schema import CharSnap, RoomSnap, StepSnap, step_from_dict, step_to_dict


def _sample_step() -> StepSnap:
    return StepSnap(
        step=3,
        command="get sword",
        chars=[
            CharSnap(
                key="Tester", room=3001, position="STANDING",
                hp=100, max_hp=100, mana=100, move=100,
                level=5, align=0, gold=0, fighting=None,
                affects=["bless"], affect_flags=["INFRARED"],
                inventory=[3022], equipment={"16": 1},
            )
        ],
        rooms=[RoomSnap(vnum=3001, people=["Tester"], contents=[3010, 3010])],
        output=["You pick up a sword."],
    )


def test_step_roundtrips_through_dict():
    step = _sample_step()
    restored = step_from_dict(step_to_dict(step))
    assert restored == step
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest -n0 tests/test_diff_harness_unit.py::test_step_roundtrips_through_dict -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.diff_harness.schema'`

- [ ] **Step 3: Write minimal implementation**

```python
# tools/diff_harness/schema.py
"""Canonical snapshot schema shared by the C-capture and Python-replay sides.

Identity is by stable key (character name; object vnum), never pointer/object-id.
Per-field list ordering policy:
  - inventory: ORDER-PRESERVED (ROM prepends on pickup; order is observable)
  - output:    ORDER-PRESERVED (message sequence is observable)
  - room.people, room.contents, char.affects, char.affect_flags: SORTED
    (ROM linked-list order is not behaviorally meaningful here)
Equipment keys are the wear-slot integer rendered as a string ("0".."18"),
language-neutral on both sides (ROM iWear / Python int(WearLocation)).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class CharSnap:
    key: str
    room: int | None
    position: str
    hp: int
    max_hp: int
    mana: int
    move: int
    level: int
    align: int
    gold: int
    fighting: str | None
    affects: list[str] = field(default_factory=list)
    affect_flags: list[str] = field(default_factory=list)
    inventory: list[int] = field(default_factory=list)
    equipment: dict[str, int] = field(default_factory=dict)


@dataclass
class RoomSnap:
    vnum: int
    people: list[str] = field(default_factory=list)
    contents: list[int] = field(default_factory=list)


@dataclass
class StepSnap:
    step: int
    command: str
    chars: list[CharSnap] = field(default_factory=list)
    rooms: list[RoomSnap] = field(default_factory=list)
    output: list[str] = field(default_factory=list)


def step_to_dict(step: StepSnap) -> dict:
    return asdict(step)


def step_from_dict(data: dict) -> StepSnap:
    chars = [CharSnap(**c) for c in data.get("chars", [])]
    rooms = [RoomSnap(**r) for r in data.get("rooms", [])]
    return StepSnap(
        step=data["step"],
        command=data["command"],
        chars=chars,
        rooms=rooms,
        output=list(data.get("output", [])),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest -n0 tests/test_diff_harness_unit.py::test_step_roundtrips_through_dict -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/diff_harness/__init__.py tools/diff_harness/schema.py tests/test_diff_harness_unit.py
git commit -m "feat(diff-harness): snapshot schema + roundtrip"
```

---

## Task 2: Comparator (normalize + diff)

**Files:**
- Create: `tools/diff_harness/compare.py`
- Test: `tests/test_diff_harness_unit.py` (append)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_diff_harness_unit.py  (append)
from tools.diff_harness.compare import diff_traces, normalize_step


def test_normalize_sorts_unordered_lists_and_strips_ansi():
    step = StepSnap(
        step=1, command="look",
        chars=[CharSnap(
            key="Tester", room=3001, position="STANDING",
            hp=1, max_hp=1, mana=0, move=0, level=1, align=0, gold=0,
            fighting=None, affects=["bless", "armor"], affect_flags=["B", "A"],
            inventory=[3010, 3022], equipment={},
        )],
        rooms=[RoomSnap(vnum=3001, people=["zeke", "abe"], contents=[3010, 3001])],
        output=["\x1b[31mRed\x1b[0m text\r\n"],
    )
    norm = normalize_step(step)
    assert norm.chars[0].affects == ["armor", "bless"]        # sorted
    assert norm.chars[0].affect_flags == ["A", "B"]           # sorted
    assert norm.chars[0].inventory == [3010, 3022]            # order preserved
    assert norm.rooms[0].people == ["abe", "zeke"]            # sorted
    assert norm.rooms[0].contents == [3001, 3010]             # sorted
    assert norm.output == ["Red text"]                        # ANSI/CRLF/trailing stripped


def test_diff_traces_reports_first_divergence():
    a = [StepSnap(step=1, command="get sword",
                  chars=[CharSnap("T", 3001, "STANDING", 1, 1, 0, 0, 1, 0, 0, None,
                                  inventory=[3022])], rooms=[], output=[])]
    b = [StepSnap(step=1, command="get sword",
                  chars=[CharSnap("T", 3001, "STANDING", 1, 1, 0, 0, 1, 0, 0, None,
                                  inventory=[3010])], rooms=[], output=[])]
    report = diff_traces(a, b)
    assert report is not None
    assert "step 1" in report
    assert "inventory" in report


def test_diff_traces_identical_returns_none():
    a = [StepSnap(step=1, command="look", chars=[], rooms=[], output=["hi"])]
    b = [StepSnap(step=1, command="look", chars=[], rooms=[], output=["hi"])]
    assert diff_traces(a, b) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest -n0 tests/test_diff_harness_unit.py -k "normalize or diff_traces" -v`
Expected: FAIL — `ImportError: cannot import name 'diff_traces'`

- [ ] **Step 3: Write minimal implementation**

```python
# tools/diff_harness/compare.py
"""Normalization + trace diffing. Both capture and replay call normalize_step()
so canonicalization never drifts between the C and Python sides."""

from __future__ import annotations

import re
from dataclasses import replace

from tools.diff_harness.schema import CharSnap, RoomSnap, StepSnap

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _clean_line(line: str) -> str:
    return _ANSI.sub("", line).replace("\r\n", "\n").replace("\r", "\n").rstrip()


def _normalize_char(c: CharSnap) -> CharSnap:
    return replace(
        c,
        affects=sorted(c.affects),
        affect_flags=sorted(c.affect_flags),
        inventory=list(c.inventory),  # order preserved
    )


def _normalize_room(r: RoomSnap) -> RoomSnap:
    return replace(r, people=sorted(r.people), contents=sorted(r.contents))


def normalize_step(step: StepSnap) -> StepSnap:
    return replace(
        step,
        chars=[_normalize_char(c) for c in step.chars],
        rooms=[_normalize_room(r) for r in step.rooms],
        output=[_clean_line(line) for line in step.output],
    )


def diff_traces(c_trace: list[StepSnap], py_trace: list[StepSnap]) -> str | None:
    """Return a human-readable report of the FIRST divergence, or None if equal."""
    if len(c_trace) != len(py_trace):
        return f"trace length differs: C={len(c_trace)} py={len(py_trace)}"
    for c_step_raw, py_step_raw in zip(c_trace, py_trace):
        c_step = normalize_step(c_step_raw)
        py_step = normalize_step(py_step_raw)
        if c_step == py_step:
            continue
        return _render_step_diff(c_step, py_step)
    return None


def _render_step_diff(c: StepSnap, py: StepSnap) -> str:
    prefix = f"step {c.step} (command={c.command!r})"
    if c.output != py.output:
        return f"{prefix} · output · C={c.output} py={py.output}"
    c_by_key = {ch.key: ch for ch in c.chars}
    py_by_key = {ch.key: ch for ch in py.chars}
    if set(c_by_key) != set(py_by_key):
        return f"{prefix} · chars · C keys={sorted(c_by_key)} py keys={sorted(py_by_key)}"
    for key in c_by_key:
        cc, pc = c_by_key[key], py_by_key[key]
        if cc != pc:
            for f in ("room", "position", "hp", "max_hp", "mana", "move", "level",
                      "align", "gold", "fighting", "affects", "affect_flags",
                      "inventory", "equipment"):
                if getattr(cc, f) != getattr(pc, f):
                    return f"{prefix} · chars[{key}].{f} · C={getattr(cc, f)} py={getattr(pc, f)}"
    c_rooms = {r.vnum: r for r in c.rooms}
    py_rooms = {r.vnum: r for r in py.rooms}
    for vnum in c_rooms:
        if c_rooms[vnum] != py_rooms.get(vnum):
            return f"{prefix} · rooms[{vnum}] · C={c_rooms[vnum]} py={py_rooms.get(vnum)}"
    return f"{prefix} · steps differ (no field localized — inspect manually)"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest -n0 tests/test_diff_harness_unit.py -k "normalize or diff_traces" -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/diff_harness/compare.py tests/test_diff_harness_unit.py
git commit -m "feat(diff-harness): normalize + trace diff with divergence report"
```

---

## Task 3: Python snapshotter (pysnap)

**Files:**
- Create: `tools/diff_harness/pysnap.py`
- Test: `tests/test_diff_harness_unit.py` (append)

**Context for the implementer:** Python entities — `Character` (`mud/models/character.py`: `.name`, `.room`, `.position` (IntEnum), `.hit`/`.max_hit`, `.mana`/`.max_mana`, `.move`/`.max_move`, `.level`, `.alignment`, `.gold`, `.fighting`, `.inventory` (list of objects), `.equipment` (dict int-slot → object), `.affected` (list of affect objects with `.spell_name`/`.name`), `.affected_by` (int bitfield) ). `Room` (`mud/models/room.py`: `.vnum`, `.people`, `.contents`). Objects carry `.prototype.vnum`. Confirm exact attribute names against the modules before writing — adapt the getters if a name differs. Use `getattr(..., default)` defensively at these boundaries only.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_diff_harness_unit.py  (append)
import pytest

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from tools.diff_harness.pysnap import snapshot_python


@pytest.fixture
def watched_world():
    room = Room(vnum=3001, name="R", description="")
    char = Character(name="Tester", level=5, position=Position.STANDING)
    char.hit = char.max_hit = 100
    char.room = room
    room.add_character(char)
    return room, char


def test_snapshot_python_captures_watch_set(watched_world):
    room, char = watched_world
    rooms_by_vnum = {3001: room}
    chars_by_name = {"Tester": char}

    step = snapshot_python(
        step=2, command="look",
        chars_by_name=chars_by_name, rooms_by_vnum=rooms_by_vnum, output=["You see a room."],
    )

    assert step.step == 2
    assert step.command == "look"
    assert step.chars[0].key == "Tester"
    assert step.chars[0].room == 3001
    assert step.chars[0].position == "STANDING"
    assert step.chars[0].hp == 100
    assert step.rooms[0].vnum == 3001
    assert "Tester" in step.rooms[0].people
    assert step.output == ["You see a room."]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest -n0 tests/test_diff_harness_unit.py::test_snapshot_python_captures_watch_set -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.diff_harness.pysnap'`

- [ ] **Step 3: Write minimal implementation**

```python
# tools/diff_harness/pysnap.py
"""Build a StepSnap from live Python engine state over a declared watch-set."""

from __future__ import annotations

from mud.models.constants import Position
from tools.diff_harness.schema import CharSnap, RoomSnap, StepSnap


def _obj_vnum(obj: object) -> int | None:
    proto = getattr(obj, "prototype", None)
    return getattr(proto, "vnum", None)


def _affect_names(char: object) -> list[str]:
    names: list[str] = []
    for aff in getattr(char, "affected", []) or []:
        name = getattr(aff, "spell_name", None) or getattr(aff, "name", None)
        if name:
            names.append(str(name))
    return names


def _affect_flag_names(char: object) -> list[str]:
    from mud.models.constants import AffectFlag

    bits = int(getattr(char, "affected_by", 0) or 0)
    return [f.name for f in AffectFlag if f.value and (bits & int(f.value))]


def _char_snap(key: str, char: object) -> CharSnap:
    room = getattr(char, "room", None)
    fighting = getattr(char, "fighting", None)
    pos = getattr(char, "position", None)
    pos_name = pos.name if isinstance(pos, Position) else str(Position(int(pos)).name)
    inventory = [v for v in (_obj_vnum(o) for o in getattr(char, "inventory", []) or []) if v is not None]
    equipment = {
        str(int(slot)): v
        for slot, o in (getattr(char, "equipment", {}) or {}).items()
        if o is not None and (v := _obj_vnum(o)) is not None
    }
    return CharSnap(
        key=key,
        room=getattr(room, "vnum", None),
        position=pos_name,
        hp=int(getattr(char, "hit", 0)),
        max_hp=int(getattr(char, "max_hit", 0)),
        mana=int(getattr(char, "mana", 0)),
        move=int(getattr(char, "move", 0)),
        level=int(getattr(char, "level", 0)),
        align=int(getattr(char, "alignment", 0)),
        gold=int(getattr(char, "gold", 0)),
        fighting=getattr(fighting, "name", None),
        affects=_affect_names(char),
        affect_flags=_affect_flag_names(char),
        inventory=inventory,
        equipment=equipment,
    )


def _room_snap(room: object) -> RoomSnap:
    people = [getattr(p, "name", "?") for p in getattr(room, "people", []) or []]
    contents = [v for v in (_obj_vnum(o) for o in getattr(room, "contents", []) or []) if v is not None]
    return RoomSnap(vnum=int(getattr(room, "vnum", -1)), people=people, contents=contents)


def snapshot_python(
    step: int,
    command: str,
    chars_by_name: dict[str, object],
    rooms_by_vnum: dict[int, object],
    output: list[str],
) -> StepSnap:
    return StepSnap(
        step=step,
        command=command,
        chars=[_char_snap(k, c) for k, c in chars_by_name.items()],
        rooms=[_room_snap(r) for r in rooms_by_vnum.values()],
        output=list(output),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest -n0 tests/test_diff_harness_unit.py::test_snapshot_python_captures_watch_set -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/diff_harness/pysnap.py tests/test_diff_harness_unit.py
git commit -m "feat(diff-harness): python state snapshotter"
```

---

## Task 4: Scenario loader

**Files:**
- Create: `tools/diff_harness/scenario.py`
- Create: `tools/diff_harness/scenarios/movement_get_drop.json`
- Test: `tests/test_diff_harness_unit.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_diff_harness_unit.py  (append)
from pathlib import Path

from tools.diff_harness.scenario import Scenario, load_scenario


def test_load_scenario_parses_fields(tmp_path: Path):
    p = tmp_path / "s.json"
    p.write_text(
        '{"name":"s","seed":1234,"start_room":3001,'
        '"char":{"name":"Tester","level":5},'
        '"watch":{"chars":["Tester"],"rooms":[3001,3054]},'
        '"steps":["look","north"]}'
    )
    sc = load_scenario(p)
    assert isinstance(sc, Scenario)
    assert sc.name == "s"
    assert sc.seed == 1234
    assert sc.start_room == 3001
    assert sc.char_name == "Tester"
    assert sc.char_level == 5
    assert sc.watch_chars == ["Tester"]
    assert sc.watch_rooms == [3001, 3054]
    assert sc.steps == ["look", "north"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest -n0 tests/test_diff_harness_unit.py::test_load_scenario_parses_fields -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.diff_harness.scenario'`

- [ ] **Step 3: Write minimal implementation**

```python
# tools/diff_harness/scenario.py
"""Scenario loader — the single source both capture and replay read."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Scenario:
    name: str
    seed: int
    start_room: int
    char_name: str
    char_level: int
    watch_chars: list[str]
    watch_rooms: list[int]
    steps: list[str]


def load_scenario(path: str | Path) -> Scenario:
    data = json.loads(Path(path).read_text())
    char = data["char"]
    watch = data["watch"]
    return Scenario(
        name=data["name"],
        seed=int(data["seed"]),
        start_room=int(data["start_room"]),
        char_name=char["name"],
        char_level=int(char.get("level", 1)),
        watch_chars=list(watch["chars"]),
        watch_rooms=[int(v) for v in watch["rooms"]],
        steps=list(data["steps"]),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest -n0 tests/test_diff_harness_unit.py::test_load_scenario_parses_fields -v`
Expected: PASS

- [ ] **Step 5: Create the first scenario file**

```json
// tools/diff_harness/scenarios/movement_get_drop.json
{
  "name": "movement_get_drop",
  "seed": 1234,
  "start_room": 3001,
  "char": { "name": "Tester", "level": 5 },
  "watch": { "chars": ["Tester"], "rooms": [3001, 3054] },
  "steps": ["look", "inventory", "north", "look", "south", "inventory"]
}
```

> Note: object-handling steps (`get`/`drop`/`wear`/`remove`) are added in Task 7
> once a concrete object known to exist in room 3001/3054 is confirmed from the
> area data; the v1 movement scenario above is enough to prove the pipeline.

- [ ] **Step 6: Commit**

```bash
git add tools/diff_harness/scenario.py tools/diff_harness/scenarios/movement_get_drop.json tests/test_diff_harness_unit.py
git commit -m "feat(diff-harness): scenario loader + first movement scenario"
```

---

## Task 5: C instrumentation shim + build

**Files:**
- Create: `src/diff_shim/diffmain.c`
- Create: `src/Makefile.diffshim`

**Context — confirm against headers FIRST.** Before writing C, read `src/merc.h` for the exact field/function names: `boot_db` (db.c), `init_mm`/`number_mm` (db.c, `-DOLD_RAND` branch), `interpret` (interp.c), `DESCRIPTOR_DATA` + `CHAR_DATA` structs, `new_char`/`create_mobile`, `char_to_room`, `get_room_index`, `send_to_char`/`write_to_buffer`, the global `char_list` and `room_index_hash`. The ROM equivalents of the Python attributes: `ch->name`, `ch->in_room->vnum`, `ch->position`, `ch->hit`/`ch->max_hit`, `ch->mana`, `ch->move`, `ch->level`, `ch->alignment`, `ch->gold`, `ch->fighting`, `ch->carrying` (inventory linked list via `obj->next_content`), `obj->pIndexData->vnum`, `ch->affected` (AFFECT_DATA via `->next`), `ch->affected_by` (bitvector), equipment via `get_eq_char(ch, iWear)` for `iWear` 0..MAX_WEAR-1. **This task is the plan's #1 risk (synthetic descriptor + output capture); budget extra time and verify by running, not by tests.**

- [ ] **Step 1: Write the shim**

`src/diff_shim/diffmain.c` — a standalone `main()` that:
1. calls `boot_db()`;
2. reads the first line `boot seed=<n> start_room=<v> char=<name>`, calls `init_mm` forcing that seed (OLD_RAND path), creates one PC-like `CHAR_DATA` via `new_char`, sets `name`/`level`, `char_to_room` into `get_room_index(start_room)`, and attaches a synthetic `DESCRIPTOR_DATA` whose `outbuf` we can read+reset;
3. loops over stdin lines:
   - `__snapshot chars=<a,b> rooms=<v,v>` → walk the watch-set, emit one `{"type":"snapshot",...}` JSON line to stdout (fields per the schema; equipment keys = iWear int as string; inventory order = `carrying` list order; people/contents/affects emitted unsorted — Python normalizer sorts both sides);
   - any other line → reset the descriptor outbuf, call `interpret(ch, line)`, then emit `{"type":"output","lines":[...]}` from the captured buffer (split on `\n`, JSON-escape).
4. Emit JSON with a tiny hand-rolled writer (escape `"` `\` and control chars) — do **not** pull in a JSON lib.

> The full C is ~200–300 lines and depends on exact struct names; write it against
> `merc.h` confirmed in the Context above. Keep ROM `src/*.c` untouched — this
> file only *calls* them.

- [ ] **Step 2: Write the makefile**

```make
# src/Makefile.diffshim — builds ROM objects + the diff shim, deterministic RNG.
CC      = gcc
C_FLAGS = -O -g3 -Wall -DOLD_RAND -Wno-deprecated-declarations
# ROM objects EXCEPT comm.c (which owns the real main()/game_loop).
ROM_SRC = act_comm.c act_enter.c act_info.c act_move.c act_obj.c act_wiz.c \
          alias.c ban.c db.c db2.c effects.c fight.c flags.c handler.c healer.c \
          interp.c note.c lookup.c magic.c magic2.c music.c update.c \
          save.c scan.c skills.c special.c tables.c string.c
ROM_OBJ = $(ROM_SRC:.c=.o)

diffshim: $(ROM_OBJ) diff_shim/diffmain.o
	$(CC) $(C_FLAGS) -o diffshim $(ROM_OBJ) diff_shim/diffmain.o -lcrypt

%.o: %.c
	$(CC) -c $(C_FLAGS) $< -o $@

diff_shim/diffmain.o: diff_shim/diffmain.c
	$(CC) -c $(C_FLAGS) diff_shim/diffmain.c -o diff_shim/diffmain.o

clean-diffshim:
	rm -f diff_shim/diffmain.o diffshim
```

> The `ROM_SRC` list must match the actual `.c` files referenced by the symbols the
> shim calls; start from `src/Makefile`'s object list, drop `comm.c`, add
> `diff_shim/diffmain.c`. On macOS, drop `-lcrypt` if the linker rejects it
> (`crypt` is in libSystem) — confirm at build time.

- [ ] **Step 3: Build and smoke-run the binary by hand**

Run:
```bash
cd src && make -f Makefile.diffshim diffshim 2>&1 | tail -20
printf 'boot seed=1234 start_room=3001 char=Tester\nlook\n__snapshot chars=Tester rooms=3001\n' | ./diffshim
```
Expected: a `{"type":"output",...}` line for `look`, then a `{"type":"snapshot",...}` line with `"key":"Tester"`, `"room":3001`. Iterate on the C until this holds. **Do not proceed until the binary emits well-formed JSON.**

- [ ] **Step 4: Commit**

```bash
git add src/diff_shim/diffmain.c src/Makefile.diffshim
git commit -m "feat(diff-harness): additive C shim (stdin driver + __snapshot) + build"
```

> Add `src/diffshim` and `src/**/*.o` to `.gitignore` (build artifacts) in this commit.

---

## Task 6: Capture tool

**Files:**
- Create: `tools/diff_harness/capture.py`
- Test: manual (drives the C binary)

- [ ] **Step 1: Write the capture tool**

```python
# tools/diff_harness/capture.py
"""Drive the instrumented C binary through a scenario and write a golden trace.

Usage:
    python3 -m tools.diff_harness.capture --scenario <name|path> [--binary src/diffshim]
    python3 -m tools.diff_harness.capture --all
    python3 -m tools.diff_harness.capture --check     # re-capture, diff vs committed
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from tools.diff_harness.scenario import Scenario, load_scenario

REPO = Path(__file__).resolve().parents[2]
SCEN_DIR = REPO / "tools" / "diff_harness" / "scenarios"
GOLDEN_DIR = REPO / "tests" / "data" / "golden" / "diff"
DEFAULT_BINARY = REPO / "src" / "diffshim"


def _c_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO).decode().strip()


def _drive(sc: Scenario, binary: Path) -> list[dict]:
    lines = [f"boot seed={sc.seed} start_room={sc.start_room} char={sc.char_name}"]
    for step in sc.steps:
        lines.append(step)
        lines.append(f"__snapshot chars={','.join(sc.watch_chars)} rooms={','.join(map(str, sc.watch_rooms))}")
    proc = subprocess.run(
        [str(binary)], input="\n".join(lines) + "\n",
        capture_output=True, text=True, cwd=REPO / "src",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"C binary exited {proc.returncode}\nstderr:\n{proc.stderr}")

    events = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    trace: list[dict] = []
    step_no = 0
    pending_output: list[str] = []
    cmd_iter = iter(sc.steps)
    for ev in events:
        if ev["type"] == "output":
            pending_output = ev["lines"]
        elif ev["type"] == "snapshot":
            step_no += 1
            snap = ev
            snap["step"] = step_no
            snap["command"] = next(cmd_iter)
            snap["output"] = pending_output
            snap.pop("type", None)
            trace.append(snap)
            pending_output = []
    return trace


def capture(sc: Scenario, binary: Path) -> dict:
    return {
        "scenario": sc.name,
        "c_commit": _c_commit(),
        "build_flags": "-DOLD_RAND",
        "seed": sc.seed,
        "trace": _drive(sc, binary),
    }


def _write_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n")
    tmp.replace(path)


def _resolve(scenario: str) -> Scenario:
    p = Path(scenario)
    if not p.exists():
        p = SCEN_DIR / f"{scenario}.json"
    return load_scenario(p)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--binary", default=str(DEFAULT_BINARY))
    args = ap.parse_args(argv)
    binary = Path(args.binary)

    if args.all or args.check:
        scenarios = [load_scenario(p) for p in sorted(SCEN_DIR.glob("*.json"))]
    elif args.scenario:
        scenarios = [_resolve(args.scenario)]
    else:
        ap.error("one of --scenario / --all / --check required")

    failures = 0
    for sc in scenarios:
        payload = capture(sc, binary)
        gold = GOLDEN_DIR / f"{sc.name}.golden.json"
        if args.check:
            existing = json.loads(gold.read_text()) if gold.exists() else None
            if existing is None or existing.get("trace") != payload["trace"]:
                print(f"CHANGED: {sc.name}")
                failures += 1
            else:
                print(f"ok: {sc.name}")
        else:
            _write_atomic(gold, payload)
            print(f"wrote {gold.relative_to(REPO)} ({len(payload['trace'])} steps)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Capture the movement scenario**

Run:
```bash
python3 -m tools.diff_harness.capture --scenario movement_get_drop
```
Expected: `wrote tests/data/golden/diff/movement_get_drop.golden.json (6 steps)`. Open the file and sanity-check: each step has `chars[0].key == "Tester"`, plausible `room`, and `output` lines.

- [ ] **Step 3: Commit the tool + golden**

```bash
git add tools/diff_harness/capture.py tests/data/golden/diff/movement_get_drop.golden.json
git commit -m "feat(diff-harness): capture tool + movement golden trace"
```

---

## Task 7: Object-handling steps + recapture

**Files:**
- Modify: `tools/diff_harness/scenarios/movement_get_drop.json`
- Modify: `tests/data/golden/diff/movement_get_drop.golden.json` (regenerated)

- [ ] **Step 1: Find a concrete object in room 3001 or 3054**

Run:
```bash
grep -n "^#30" area/midgaard.are | head      # reset/object section
python3 -c "from mud.world import initialize_world; from mud.registry import room_registry; initialize_world(); r=room_registry[3001]; print([getattr(o.prototype,'vnum',None) for o in r.contents])"
```
Pick an object vnum present in 3001 (or move to a room that has one). Confirm its keyword for the `get` command.

- [ ] **Step 2: Add object steps to the scenario**

Edit `steps` to include the confirmed object, e.g.:
```json
"steps": ["look", "inventory", "get <keyword>", "inventory", "drop <keyword>", "inventory", "north", "south"]
```
(Replace `<keyword>` with the real keyword from Step 1.)

- [ ] **Step 3: Recapture and verify the golden reflects the object moving**

Run:
```bash
python3 -m tools.diff_harness.capture --scenario movement_get_drop
```
Expected: after `get`, the object's vnum appears in `chars[Tester].inventory` and leaves `rooms[3001].contents`; after `drop`, the reverse.

- [ ] **Step 4: Commit**

```bash
git add tools/diff_harness/scenarios/movement_get_drop.json tests/data/golden/diff/movement_get_drop.golden.json
git commit -m "feat(diff-harness): add object get/drop steps + recapture golden"
```

---

## Task 8: Replay integration test

**Files:**
- Create: `tests/test_differential_smoke.py`

**Context:** Python driving surface — `mud.world.initialize_world()`, `mud.utils.rng_mm.seed_mm(seed)`, `mud.commands.dispatcher.process_command(char, line)` (returns the command's output string), `mud.world.create_test_character(name, room_vnum)` (places a char in a room), `mud.registry.room_registry`. The smoke slice runs **no game_tick** (commands are direct effects). `process_command` returns output as a single string — split on `\n` for the snapshot `output` list.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_differential_smoke.py
"""Differential smoke test: drive the Python engine through each captured
scenario and assert its per-step state+output matches the committed C golden."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mud.commands.dispatcher import process_command
from mud.registry import room_registry
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world
from tools.diff_harness.compare import diff_traces
from tools.diff_harness.pysnap import snapshot_python
from tools.diff_harness.scenario import load_scenario
from tools.diff_harness.schema import step_from_dict

REPO = Path(__file__).resolve().parents[1]
SCEN_DIR = REPO / "tools" / "diff_harness" / "scenarios"
GOLDEN_DIR = REPO / "tests" / "data" / "golden" / "diff"


def _scenarios():
    return sorted(SCEN_DIR.glob("*.json"))


@pytest.mark.parametrize("scen_path", _scenarios(), ids=lambda p: p.stem)
def test_python_matches_c_golden(scen_path):
    sc = load_scenario(scen_path)
    gold_path = GOLDEN_DIR / f"{sc.name}.golden.json"
    if not gold_path.exists():
        pytest.skip(f"no golden captured for {sc.name} (run capture.py)")

    c_trace = [step_from_dict(s) for s in json.loads(gold_path.read_text())["trace"]]

    rng_mm.seed_mm(sc.seed)
    initialize_world()
    char = create_test_character(sc.char_name, sc.start_room)
    char.level = sc.char_level

    chars_by_name = {sc.char_name: char}
    rooms_by_vnum = {v: room_registry[v] for v in sc.watch_rooms}

    py_trace = []
    for i, command in enumerate(sc.steps, start=1):
        output = process_command(char, command) or ""
        py_trace.append(
            snapshot_python(
                step=i, command=command,
                chars_by_name=chars_by_name, rooms_by_vnum=rooms_by_vnum,
                output=output.split("\n"),
            )
        )

    report = diff_traces(c_trace, py_trace)
    assert report is None, f"Python diverged from C reference:\n{report}"
```

- [ ] **Step 2: Run the test**

Run: `pytest -n0 tests/test_differential_smoke.py -v`
Expected: It runs against the committed golden. One of two outcomes:
- **PASS** → the Python port matches ROM C for this scenario. Done.
- **FAIL with a `report`** → a *real divergence*. Triage it: read the named field/step, decide whether ROM C or Python is correct (ROM is source of truth), and file it as a parity gap (per AGENTS.md) — do **not** edit the golden to make the test pass. If the divergence is a harness artifact (e.g. a watch-set field the C shim emits differently), fix the harness side.

> Because this is the first time the two engines are compared directly, a real
> divergence here is a *success of the tool*, not a failure of the task. Capture
> any divergence as a new gap/INV and decide separately whether to fix it now.

- [ ] **Step 3: Commit**

```bash
git add tests/test_differential_smoke.py
git commit -m "feat(diff-harness): python-vs-C golden replay smoke test"
```

---

## Task 9: README + harness self-test wiring

**Files:**
- Create: `tools/diff_harness/README.md`

- [ ] **Step 1: Write the README**

Document, with the exact commands:
- one-time build: `cd src && make -f Makefile.diffshim diffshim`
- regenerate goldens: `python3 -m tools.diff_harness.capture --all`
- verify goldens vs current C: `python3 -m tools.diff_harness.capture --check`
- everyday run: `pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py`
- the schema/ordering rules (copy the summary from the spec)
- the "a divergence is a finding, not a golden to overwrite" rule
- macOS build notes (`-lcrypt` may be unnecessary; `<malloc.h>` warnings benign)

- [ ] **Step 2: Run the full harness test set**

Run: `pytest -n0 tests/test_diff_harness_unit.py tests/test_differential_smoke.py -v`
Expected: all unit tests PASS; the smoke test PASSES or reports a triaged divergence.

- [ ] **Step 3: Commit**

```bash
git add tools/diff_harness/README.md
git commit -m "docs(diff-harness): re-capture + run workflow README"
```

---

## Task 10: Finalize (changelog, version, suite)

**Files:**
- Modify: `CHANGELOG.md`, `pyproject.toml`

- [ ] **Step 1: Run the full suite**

Run: `pytest -q tests/`
Expected: no new failures vs baseline (the differential smoke test passes or is a triaged, documented divergence).

- [ ] **Step 2: CHANGELOG + version (minor bump — new test infrastructure)**

Add an `Added` entry under a new version section describing the harness (capture/replay, smoke slice, additive C shim), and bump `pyproject.toml` `version` by one minor.

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md pyproject.toml
git commit -m "chore(diff-harness): changelog + version bump for differential harness v1"
```

---

## Self-review notes

- **Spec coverage:** schema (T1), normalization+diff (T2), pysnap (T3), scenario (T4), additive C shim+build (T5), capture+golden (T6–T7), replay test (T8), README/workflow (T9), finalize (T10). All spec sections mapped.
- **Type consistency:** `StepSnap`/`CharSnap`/`RoomSnap` field names are defined in T1 and reused verbatim in T2/T3/T8; `Scenario` fields defined in T4 reused in T6/T8; `diff_traces`/`normalize_step`/`snapshot_python`/`load_scenario`/`step_from_dict` signatures consistent across tasks.
- **Known soft spots (intentional, not placeholders):** the C shim body (T5) is described structurally with confirmed ROM API calls rather than 300 lines of verbatim C, because exact struct field names must be read from `merc.h` at implementation time — each such point has an explicit "confirm against header" step and a run-to-verify gate. The object keyword in T7 is resolved by an explicit discovery step rather than guessed.
