# Combat/RNG Differential Scenario (v1 mid-fight) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the differential harness with a deterministic melee-combat scenario that verifies per-round ROM↔Python combat (to-hit, damage, HP decrement, hit/miss text) bit-for-bit.

**Architecture:** Add three additive meta-commands to the C shim (`__seed`, `__mload`, `__tick`) and teach the Python replay loop the same three. `__tick` drives `violence_update()` (C) / `violence_tick(do_combat=True)` (Python) — the matched combat-round pump. A combat-boundary `__seed` scopes RNG to combat draws; `__mload` spawns a fresh deterministic combatant (drunk vnum 3064, HP 100). The harness PC's combat-input stats are reconciled to the C shim's `make_test_char`, and the snapshot is extended with effective combat stats so that reconciliation is test-enforced.

**Tech Stack:** ROM 2.4b6 C (`-DOLD_RAND`, built via `src/Makefile.diffshim`), Python 3.12, pytest, the existing `tools/diff_harness/` capture/replay harness.

**Working directory:** all paths relative to the diff-harness worktree
`/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/.worktrees/diff-harness`.
Run every command from there; do **not** cd to the original repo root.

---

## File Structure

| File | Responsibility | Change |
|------|----------------|--------|
| `src/diff_shim/diffmain.c` | Instrumented C driver | Modify: add `__seed`/`__mload`/`__tick` handlers + emit effective combat stats in `handle_snapshot` |
| `tools/diff_harness/schema.py` | Shared snapshot schema | Modify: add `eff_hitroll`/`eff_damroll`/`eff_ac` to `CharSnap` |
| `tools/diff_harness/compare.py` | Normalize + diff | Modify: compare the 3 new fields in `_render_step_diff` |
| `tools/diff_harness/pysnap.py` | Python state → snapshot | Modify: populate the 3 new fields via `mud.math.stat_apps` |
| `tests/test_differential_smoke.py` | Replay driver | Modify: matched PC stub stats; dispatch `__seed`/`__mload`/`__tick`; register the mob in the watch set |
| `tools/diff_harness/scenarios/combat_melee_rounds.json` | v1 scenario | Create |
| `tests/data/golden/diff/combat_melee_rounds.golden.json` | Captured C golden | Create (via capture tool) |
| `tests/data/golden/diff/movement_get_drop.golden.json` | Existing golden | Re-capture (new snapshot fields) |
| `tools/diff_harness/FINDINGS.md` | Divergence log | Modify (per finding) |
| `CHANGELOG.md`, `pyproject.toml` | Release hygiene | Modify (finalize) |

**Key reference facts (verified during design):**
- `src/fight.c:79` — `violence_update` calls `multi_hit` gated on `IS_AWAKE && same room` only, **not** on `wait`. A lagged PC still auto-attacks; the fight does not stall.
- `src/fight.c:90` — `violence_update` calls `check_assist` each tick; other mobs in the room can be pulled in and draw RNG. **Fight in a mob-free room (3008)** so `room.people == [PC, drunk]`.
- Combatant drunk **vnum 3064**: mobprog-free, spec_fun-free, level 2, `hit_dice=1d1+99` → HP **100** deterministic, sex `male` (no spawn sex-RNG draw). Keyword/`char_key` = `drunk`.
- C `make_test_char` (`src/diff_shim/diffmain.c:380`): class 0 (mage), `perm_stat` all 13 with prime (INT) +3 → STR 13 / INT 16 / DEX 13, no gear → stored hitroll/damroll 0, armor 100×4.
- Python `create_test_character` (`mud/world/world_state.py:256`): leaves `perm_stat=[]` and `armor=[100,100,100,100]`; `ch_class=0`. The empty `perm_stat` is the gap to close for combat.
- Python combat reads effective stats via `mud.math.stat_apps.get_hitroll/get_damroll/get_ac` and `compute_thac0(level, ch_class, ...)` (`mud/combat/engine.py:18,432`).
- `spawn_mob(vnum)` (`mud/spawning/mob_spawner.py:9`) adds to `character_registry` but does **not** place the mob in a room — caller must `room.add_character(mob)`.
- Python combat-round pump: `mud.game_loop.violence_tick(do_combat=True)`.
- `_person_key` (`tools/diff_harness/pysnap.py:60`) already keys a mob by `prototype.player_name`'s first word.

---

### Task 1: C shim — add `__seed`, `__mload`, `__tick` meta-commands

**Files:**
- Modify: `src/diff_shim/diffmain.c:514` (insert before the "Ordinary ROM command" block at line 524)

- [ ] **Step 1: Add the three meta-command handlers**

In `src/diff_shim/diffmain.c`, immediately **before** the existing block:

```c
        /* Ordinary ROM command: capture its output. */
        if (ch == NULL)
            continue;
        shim_reset_output ();
        interpret (ch, line);
        emit_output ();
```

insert:

```c
        /* __seed=<n>: reseed OLD_RAND mid-run, same convention as boot
         * (init_mm seeds piState from current_time). Scopes the next
         * commands' RNG to a known stream position. */
        if (strncmp (line, "__seed=", 7) == 0)
        {
            current_time = (time_t) atol (line + 7);
            init_mm ();
            continue;
        }

        /* __mload=<vnum>: spawn a fresh mob into the PC's current room
         * (ROM create_mobile + char_to_room). */
        if (strncmp (line, "__mload=", 8) == 0)
        {
            int vnum = atoi (line + 8);
            MOB_INDEX_DATA *mi = get_mob_index (vnum);
            if (mi != NULL && ch != NULL && ch->in_room != NULL)
            {
                CHAR_DATA *mob = create_mobile (mi);
                char_to_room (mob, ch->in_room);
            }
            continue;
        }

        /* __tick: run one violence_update() pulse (combat round only),
         * capturing the PC's combat output. */
        if (strncmp (line, "__tick", 6) == 0)
        {
            shim_reset_output ();
            violence_update ();
            emit_output ();
            continue;
        }
```

`get_mob_index`, `create_mobile`, `char_to_room`, `violence_update`, and `MOB_INDEX_DATA` are all declared in `merc.h` (already included; `char_to_room`/`get_room_index` are used elsewhere in this file), so no new externs are needed.

- [ ] **Step 2: Rebuild the shim**

Run: `make -C src -f Makefile.diffshim diffshim`
Expected: compiles to `src/diffshim`, exit 0. If the linker complains about an undeclared symbol, add `void violence_update (void);` to the forward-declarations block near `src/diff_shim/diffmain.c:33` and rebuild.

- [ ] **Step 3: Manual smoke — confirm combat resolves and HP drops**

Run:
```bash
cd src && printf 'boot seed=12345 start_room=3008 level=5 char=Tester\n__seed=777\n__mload=3064\n__seed=777\nkill drunk\n__snapshot chars=Tester,drunk rooms=3008\n__tick\n__snapshot chars=Tester,drunk rooms=3008\n__tick\n__snapshot chars=Tester,drunk rooms=3008\n' | ./diffshim 2>/dev/null | python3 -c "import sys,json; [print(json.loads(l).get('type'), [c.get('key'),c.get('hp')] if json.loads(l).get('type')=='snapshot' else '') for l in sys.stdin if l.strip()]"
cd ..
```
Expected: `snapshot` events appear; the `drunk` `hp` is below 100 and **decreasing** across the two `__tick` snapshots, and `Tester` is alive. If the drunk's HP never drops, combat is not resolving — stop and inspect (likely the `kill` did not set fighting, or `__tick` is not reaching `violence_update`).

- [ ] **Step 4: Commit**

```bash
git add src/diff_shim/diffmain.c
git commit -m "feat(diff-harness): C shim __seed/__mload/__tick combat meta-commands"
```

---

### Task 2: Extend the snapshot with effective combat stats + reconcile the harness PC

This task makes the harness PC's combat inputs match the C shim's `make_test_char`, and adds the effective combat stats to the snapshot so the match is **test-enforced on the existing movement scenario** (which already runs the same PC through both engines). Do the snapshot extension and the stub fix together: the new fields would otherwise make the movement scenario diverge.

**Files:**
- Modify: `tools/diff_harness/schema.py:34`
- Modify: `tools/diff_harness/compare.py:73`
- Modify: `tools/diff_harness/pysnap.py` (`_char_snap`)
- Modify: `src/diff_shim/diffmain.c` (`handle_snapshot` char emit)
- Modify: `tests/test_differential_smoke.py:45-54` (shared PC setup)
- Re-capture: `tests/data/golden/diff/movement_get_drop.golden.json`

- [ ] **Step 1: Add fields to `CharSnap`**

In `tools/diff_harness/schema.py`, append to `CharSnap` (after `equipment`, line 34):

```python
    eff_hitroll: int = 0
    eff_damroll: int = 0
    eff_ac: list[int] = field(default_factory=list)
```

Defaults keep `step_from_dict` (line 57, `CharSnap(**c)`) working for goldens captured before this change.

- [ ] **Step 2: Compare the new fields**

In `tools/diff_harness/compare.py`, extend the field tuple in `_render_step_diff` (line 73) to include the three new fields:

```python
            for f in ("room", "position", "hp", "max_hp", "mana", "move", "level",
                      "align", "gold", "fighting", "eff_hitroll", "eff_damroll",
                      "eff_ac", "affects", "affect_flags",
                      "inventory", "equipment"):
```

- [ ] **Step 3: Populate the fields on the Python side**

In `tools/diff_harness/pysnap.py`, add an import at the top:

```python
from mud.math.stat_apps import get_ac, get_damroll, get_hitroll
```

and in `_char_snap`, add to the `CharSnap(...)` constructor call (after `equipment=equipment,`):

```python
        eff_hitroll=int(get_hitroll(char)),
        eff_damroll=int(get_damroll(char)),
        eff_ac=[int(get_ac(char, i)) for i in range(4)],
```

`get_ac(ch, ac_type)` (`mud/math/stat_apps.py:246`) returns `armor[ac_type] + (IS_AWAKE ? dex_app[DEX].defensive : 0)`, mirroring ROM `GET_AC`; `range(4)` yields the [PIERCE, BASH, SLASH, EXOTIC] order matching `AC_PIERCE..AC_EXOTIC`.

- [ ] **Step 4: Emit the fields on the C side**

In `src/diff_shim/diffmain.c`, in `emit_char_snapshot (CHAR_DATA *ch)` (line 184), insert immediately **after** the level/align/gold line (line 203) and **before** the `/* fighting: ... */` block (line 205). The `GET_AC`/`GET_HITROLL`/`GET_DAMROLL` macros and `AC_PIERCE`/`AC_BASH`/`AC_SLASH`/`AC_EXOTIC` constants are defined in `merc.h` (lines 996-999, 2104-2109):

```c
    printf (",\"eff_hitroll\":%d", GET_HITROLL (ch));
    printf (",\"eff_damroll\":%d", GET_DAMROLL (ch));
    printf (",\"eff_ac\":[%d,%d,%d,%d]",
            GET_AC (ch, AC_PIERCE), GET_AC (ch, AC_BASH),
            GET_AC (ch, AC_SLASH), GET_AC (ch, AC_EXOTIC));
```

Rebuild: `make -C src -f Makefile.diffshim diffshim`.

- [ ] **Step 5: Reconcile the harness PC's combat stats**

In `tests/test_differential_smoke.py`, in the shared PC setup (currently lines 45-54, after the HMV seeding `char.max_move = char.move = 100`), add:

```python
    # Mirror the C shim's make_test_char (src/diff_shim/diffmain.c:380):
    # class 0 (mage), perm_stat all 13 with prime (INT) +3, no gear. The shared
    # create_test_character stub leaves perm_stat empty, which combat math reads;
    # set it so effective hitroll/damroll/AC match the C reference. ROM stat order
    # is STR, INT, WIS, DEX, CON.
    char.ch_class = 0
    char.perm_stat = [13, 16, 13, 13, 13]
    char.hitroll = 0
    char.damroll = 0
    char.armor = [100, 100, 100, 100]
```

- [ ] **Step 6: Re-capture the movement golden and run the differential test**

Run:
```bash
python3 -m tools.diff_harness.capture --scenario movement_get_drop
pytest -n0 tests/test_differential_smoke.py -v
```
Expected: `movement_get_drop` **passes**. The re-captured golden now carries `eff_hitroll`/`eff_damroll`/`eff_ac` for `Tester`, and the Python side matches them. If it diverges on one of the new fields, the C value is the source of truth — adjust the Python stub in Step 5 to the C value shown in the diff (e.g. if C `eff_ac` differs, set `char.armor` so the effective AC matches), then re-run. Do **not** change the C side to match Python.

- [ ] **Step 7: Commit**

```bash
git add tools/diff_harness/schema.py tools/diff_harness/compare.py tools/diff_harness/pysnap.py src/diff_shim/diffmain.c tests/test_differential_smoke.py tests/data/golden/diff/movement_get_drop.golden.json
git commit -m "feat(diff-harness): snapshot effective combat stats + reconcile harness PC to make_test_char"
```

---

### Task 3: Author the v1 combat scenario + teach the replay the meta-commands

**Files:**
- Create: `tools/diff_harness/scenarios/combat_melee_rounds.json`
- Modify: `tests/test_differential_smoke.py` (replay step loop, currently lines 66-80)

- [ ] **Step 1: Write the scenario file**

Create `tools/diff_harness/scenarios/combat_melee_rounds.json`:

```json
{
  "name": "combat_melee_rounds",
  "seed": 12345,
  "start_room": 3008,
  "char": { "name": "Tester", "level": 5 },
  "watch": { "chars": ["Tester", "drunk"], "rooms": [3008] },
  "steps": ["__seed=777", "__mload=3064", "__seed=777", "kill drunk", "__tick", "__tick", "__tick", "__tick"]
}
```

The two reseeds are intentional (see the spec): the first makes the spawn deterministic; the second scopes the combat rounds. The round count (4) is provisional — Task 4 Step 3 tunes it so the drunk stays alive across all snapshots.

- [ ] **Step 2: Dispatch the meta-commands in the replay loop**

In `tests/test_differential_smoke.py`, replace the body of the `for i, command in enumerate(sc.steps, start=1):` loop's first line (`response = process_command(char, command) or ""`) with a dispatcher. Add these imports near the top of the file:

```python
from mud.spawning.mob_spawner import spawn_mob
from tools.diff_harness.pysnap import _person_key
```

and change the loop so each step is routed:

```python
    for i, command in enumerate(sc.steps, start=1):
        if command.startswith("__seed="):
            rng_mm.seed_mm(int(command[len("__seed="):]))
            response = ""
        elif command.startswith("__mload="):
            mob = spawn_mob(int(command[len("__mload="):]))
            assert mob is not None, f"spawn_mob failed for {command}"
            char.room.add_character(mob)
            chars_by_name[_person_key(mob)] = mob
            response = ""
        elif command.startswith("__tick"):
            from mud.game_loop import violence_tick
            violence_tick(do_combat=True)
            response = ""
        else:
            response = process_command(char, command) or ""
        drained = list(char.messages)
        char.messages.clear()
        lines: list[str] = []
        for chunk in (response, *drained):
            lines.extend(chunk.split("\n"))
        py_trace.append(
            snapshot_python(
                step=i, command=command,
                chars_by_name=chars_by_name, rooms_by_vnum=rooms_by_vnum,
                output=lines,
            )
        )
```

(Combat messages reach the descriptor-less harness PC via `char.messages`, the documented test fallback — see AGENTS.md "Message Delivery" — so the existing drain captures them.)

- [ ] **Step 3: Run the differential test for the combat scenario (expect skip — no golden yet)**

Run: `pytest -n0 tests/test_differential_smoke.py -v`
Expected: `combat_melee_rounds` is **skipped** ("no golden captured"), `movement_get_drop` still **passes**. The replay loop must execute the meta-commands without raising (an exception would fail, not skip). If `combat_melee_rounds` errors (e.g. `char.room.add_character` missing, or `violence_tick` import error), fix the replay code before continuing.

- [ ] **Step 4: Commit**

```bash
git add tools/diff_harness/scenarios/combat_melee_rounds.json tests/test_differential_smoke.py
git commit -m "feat(diff-harness): combat_melee_rounds scenario + replay meta-command dispatch"
```

---

### Task 4: Capture the C golden and run the differential (RED), then tune round count

**Files:**
- Create: `tests/data/golden/diff/combat_melee_rounds.golden.json`

- [ ] **Step 1: Capture the C golden**

Run: `python3 -m tools.diff_harness.capture --scenario combat_melee_rounds`
Expected: writes `tests/data/golden/diff/combat_melee_rounds.golden.json`, exit 0, prints step count.

- [ ] **Step 2: Inspect the golden — confirm the fight is a clean mid-fight window**

Run:
```bash
python3 -c "import json; t=json.load(open('tests/data/golden/diff/combat_melee_rounds.golden.json'))['trace']; [print(s['command'], {c['key']: c['hp'] for c in s['chars']}) for s in t]"
```
Expected: after `kill drunk`, the drunk's HP decreases each `__tick` and stays **> 0** through the last step; `Tester` HP stays > 0. The room snapshot should show only `Tester` and `drunk` (confirms 3008 is mob-free — if a third occupant appears, pick another mob-free room from the design's list and update `start_room` in the scenario, re-capture).

- [ ] **Step 3: Tune the round count if needed**

If the drunk dies before the last `__tick` (HP hits 0), reduce the number of trailing `__tick` steps in `combat_melee_rounds.json` so the final snapshot still has the drunk alive, then re-capture (Step 1). If the fight is too short to be interesting (drunk barely scratched), that's fine for v1 — HP must simply be monotonically decreasing and positive.

- [ ] **Step 4: Run the differential (this is the RED step)**

Run: `pytest -n0 tests/test_differential_smoke.py::test_python_matches_c_golden -v`
Expected: `combat_melee_rounds` either **passes** (Python combat already matches ROM — proceed to Task 6) or **fails with a first-divergence report**. Read the report: it names the step, the field (`output`, `chars[drunk].hp`, `eff_*`, …), and the C vs Python values. Proceed to Task 5 to triage.

- [ ] **Step 5: Commit the golden** (regardless of pass/fail — the golden is the captured C reference)

```bash
git add tests/data/golden/diff/combat_melee_rounds.golden.json tools/diff_harness/scenarios/combat_melee_rounds.json
git commit -m "feat(diff-harness): capture combat_melee_rounds C golden"
```

---

### Task 5: Triage divergences

For **each** divergence the comparator reports, classify and route it. Work one divergence at a time; the first-divergence comparator advances only after the prior one is resolved.

- [ ] **Step 1: Classify the first divergence**

- **`eff_hitroll` / `eff_damroll` / `eff_ac` differ on `Tester`** → harness stub mismatch (the PC's combat inputs still don't match `make_test_char`). Fix in `tests/test_differential_smoke.py` Step 5 of Task 2 (set the field to the C value), re-run. Not a ROM bug.
- **`eff_*` differ on `drunk`, or `drunk` `max_hp` ≠ 100** → mob spawn-stat parity gap (`MobInstance.from_prototype` vs ROM `create_mobile`). This is a **real parity bug** → record in FINDINGS.md and close on master (Step 3).
- **`output` differs** (hit/miss verb, damage tier wording, message text) → **real parity bug** in combat message rendering → FINDINGS.md + master gap-closer.
- **`hp` differs but `eff_*` and RNG inputs match** → **real parity bug** in damage calculation → FINDINGS.md + master gap-closer.
- **Everything from round 2 onward differs but round 1 matched** → RNG cascade from a single earlier mismatch (likely one extra/missing draw). Find the first-round root cause by counting RNG draws in the Python combat path vs ROM `multi_hit`/`one_hit`; fix that one cause.

- [ ] **Step 2: Record every finding in FINDINGS.md (durable, before fixing)**

Add a `## FINDING-00N — <title> — OPEN` section to `tools/diff_harness/FINDINGS.md` with: ROM C reference, Python reference, the divergence (C vs Python values), and proposed fix shape. Use the next free number (current max is FINDING-005). If the scenario must stay red until the master fix lands, add the scenario name to `KNOWN_DIVERGENCES` in `tests/test_differential_smoke.py` with the finding reference (the xfail auto-clears when the diff goes clean).

- [ ] **Step 3: Close real parity bugs on master via the gap-closer loop**

For each real bug (not a harness stub mismatch): invoke `Skill({skill: "rom-gap-closer", args: "<gap-id> — <description>"})` after filing the gap in the relevant `docs/parity/<FILE>_C_AUDIT.md`. This produces a failing-integration-test-first fix on master (the proven MOVE-003/LOOK-004 loop). After it lands on master and merges into this branch, re-capture is **not** needed (the golden is the C reference, unchanged); just re-run the differential — the Python fix should clear the divergence.

- [ ] **Step 4: Re-run until clean**

Run: `pytest -n0 tests/test_differential_smoke.py -v`
Repeat Steps 1-3 until `combat_melee_rounds` passes (or is a documented xfail pending a master fix). Then remove any `KNOWN_DIVERGENCES` entry whose root cause has landed.

---

### Task 6: Finalize — FINDINGS, changelog, version, full suite

**Files:**
- Modify: `tools/diff_harness/FINDINGS.md`, `CHANGELOG.md`, `pyproject.toml`

- [ ] **Step 1: Mark resolved findings**

In `tools/diff_harness/FINDINGS.md`, flip any FINDING opened in Task 5 that is now fixed to `✅ RESOLVED` with the master commit reference, matching the existing FINDING-001/003/004 format.

- [ ] **Step 2: Update CHANGELOG and bump version**

In `CHANGELOG.md`, add under `## [Unreleased]`:

```markdown
### Added
- **Differential harness combat slice (v1)** — `combat_melee_rounds` scenario drives a deterministic melee fight (PC vs drunk #3064) through ROM C and Python via new `__seed`/`__mload`/`__tick` shim meta-commands and `violence_tick(do_combat=True)`, verifying per-round to-hit/damage/HP/message parity. Snapshot extended with effective hitroll/damroll/AC; harness PC reconciled to the C shim's `make_test_char`. `tools/diff_harness/FINDINGS.md`.
```

Add a `### Fixed` line per real parity bug closed. Bump `pyproject.toml` `version` (patch — e.g. 2.11.1 → 2.11.2; minor if you consider the new scenario type a feature, 2.11.x → 2.12.0).

- [ ] **Step 3: Lint + full suite**

Run:
```bash
ruff check . && ruff format --check tools/diff_harness/ tests/test_differential_smoke.py
pytest -q
```
Expected: ruff clean; full suite green (≈4920+ passed, the 4 documented skips, 0 failed). If `combat_melee_rounds` is a pending xfail, it shows as `xfailed`, not failed.

- [ ] **Step 4: Commit**

```bash
git add tools/diff_harness/FINDINGS.md CHANGELOG.md pyproject.toml
git commit -m "docs(diff-harness): finalize combat v1 — FINDINGS, changelog, version bump"
```

---

## Out of scope (do not implement here)

- **v2 fight-to-death** (corpse, XP/gold, `raw_kill`, `death_cry`) — a separate spec→plan cycle.
- **Weapons / wielded combat** — v1 is bare-handed to minimize the matched-stub surface.
- **Lag-inducing skills** (bash/backstab/trip) and the descriptor-vs-chunk wait-burn path — deferred; `wait` is deliberately not snapshotted.
- **Boot-time world-spawn RNG parity** — a legitimate but separate scenario type; the `__seed`+`__mload` design intentionally removes v1's dependency on it.
