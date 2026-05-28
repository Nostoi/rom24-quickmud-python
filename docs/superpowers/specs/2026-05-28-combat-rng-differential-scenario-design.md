# Combat/RNG Differential Scenario — Design

**Date:** 2026-05-28
**Status:** Approved (brainstorming complete) — ready for implementation plan
**Depends on:** the differential testing harness v1 (`tools/diff_harness/`, shipped 2.11.0;
input-source guard 2.11.1). See `2026-05-28-differential-testing-harness-design.md`.

## Goal

Extend the differential harness (ROM C ⇄ Python golden-trace parity) from its
RNG-free smoke slice (look/move/get/drop) to a **deterministic melee-combat
slice**, so per-round combat mechanics — to-hit rolls, damage dice, HP
decrements, hit/miss message text — are verified bit-for-bit against the ROM
2.4b6 C engine.

## Why this is now possible

The C reference is built `-DOLD_RAND`, so its Mitchell-Moore generator
bit-matches `mud/utils/rng_mm.py`. Combat is RNG-driven; with a shared,
bit-identical generator AND identical draw *order*, combat rounds are
reproducible across the two engines. The entire design below exists to
guarantee identical draw order — that is the crux.

## Scope: "both, staged"

Two scenarios, two spec→plan cycles. All shared infrastructure is built in v1;
v2 is a cheap add-on once v1's per-round path is proven clean.

- **v1 — mid-fight rounds** *(this cycle)*: PC attacks a weak mob, pump a fixed
  number of violence ticks, snapshot after each, **stop before death**.
  Isolates the highest-value surface: the per-round to-hit roll and damage dice.
- **v2 — fight to death** *(follow-up cycle)*: same setup, pump ticks until the
  mob dies; snapshot corpse creation, XP/gold gain, `stop_fighting`. A separate
  scenario file so v1 can be committed green without the death path resolving.

Out of scope for both: weapons (bare-handed only — see §RNG isolation), skills
with lag (bash/backstab/trip), spell combat, multi-combatant / assist chains,
boot-time world-spawn RNG parity (a legitimate but separate future scenario
type, deliberately not entangled here).

## Architecture: matched-pair tick pumps

Combat rounds fire from a pulse handler the existing shim never reaches. Both
engines must drive the *same* combat-round function:

| Side | Pump |
|------|------|
| C    | new `__tick` meta-command → `violence_update()` **only** |
| Python | `mud.game_loop.violence_tick(do_combat=True)` |

`violence_update` iterates only *fighting* characters, so non-combatant mobs in
the room never draw RNG during a tick — this is what makes deterministic
isolation possible. `__tick` must NOT call the rest of `update_handler`
(`mobile_update`, `char_update`, `weather_tick`, `obj_update`): each draws from
the shared stream and would desync every subsequent round.

## RNG isolation — the crux (three mechanisms)

Boot + area reset draws a large, order-sensitive amount of RNG (`create_mobile`
rolls HP/mana for every mob in every area in `area.lst`). The smoke scenario's
green trace proves nothing about stream alignment because look/move/get/drop are
RNG-free. Rather than *prove* boot aligns, the design **removes the dependency on
it**:

1. **`__seed=<n>` meta-command** (both sides: C reseed via the same `init_mm`
   path the boot line uses; Python `rng_mm.seed_mm`). Issued immediately before
   `kill`. Scopes the comparison to combat-code draws only — boot/reset RNG noise
   becomes irrelevant. Reseeding is not cheating: it *scopes* the scenario to
   combat RNG.

2. **`__mload=<vnum>` meta-command** — spawn a **fresh** combatant into the PC's
   room *after* a seed (C: `create_mobile` + `char_to_room`; Python:
   `mud.spawning.mob_spawner.spawn_mob` + place in room). Its stats roll from a
   known RNG position identically on both engines. This closes the gap a
   reseed-alone leaves: a boot-spawned mob's HP is pre-rolled during boot, so
   even a combat-boundary reseed would leave it at divergent HP. Spawning fresh
   sidesteps boot-spawn-order entirely and also guarantees the mob is in the PC's
   room.

3. **Matched test-char combat stats** between the C `make_test_char` and Python
   `create_test_character` stubs (harness-only — the FINDING-002 pattern
   generalized): level, hitroll, damroll, AC, str/dex. **Bare-handed in v1** so
   there is no weapon object to match across stubs. Second/third-attack skill
   values must be equal (even at 0) because `multi_hit` calls `number_percent()`
   for each extra-attack check regardless of skill level — so the *draw count*
   per round must match, not just the outcome.

Why the advisor's "probe boot-alignment first" step is intentionally skipped:
`__mload`-after-`__seed` means v1 never depends on boot RNG, so the probe's
outcome (boot aligns or not) cannot change the v1 design.

## Combatant: drunk (vnum 3064)

Chosen by probe (`data/areas/midgaard.json`):
- **Mobprog-free** (no prog/trigger keys) and **spec_fun-free** (not in
  `specials`) — no extra behavior or RNG source.
- **Level 2** — never threatens a level-5 PC.
- `hit_dice = "1d1+99"` → **exactly 100 HP with zero RNG draw**: ROM
  `number_range(1,1)` returns early (`to-from+1 <= 1`) without consuming the
  generator, and `dice(1,1)` is one such call; `rng_mm` mirrors this. So the
  mob's starting HP aligns trivially regardless of seed — the mob-spawn-RNG risk
  evaporates for this combatant.

100 HP vs a bare-handed L5 PC is many rounds — ample mid-fight window for v1, a
longer-but-bounded fight for v2.

## New shim meta-commands (additive to `src/diff_shim/diffmain.c`)

All additive; ROM `src/*.c` untouched, same discipline as the existing
`__snapshot`. The shim already links `char_to_room` and `init_mm` and parses a
`seed=` token on the boot line, so these are incremental:

- `__seed=<n>` — reseed the generator deterministically.
- `__mload=<vnum>` — `create_mobile(get_mob_index(vnum))` + `char_to_room` into
  the booted PC's room.
- `__tick` — call `violence_update()` once.

## Python replay changes (`tests/test_differential_smoke.py`)

Teach the replay loop the three meta-commands so a scenario step that is not a
plain command is dispatched specially:

- `__seed=<n>` → `rng_mm.seed_mm(n)`
- `__mload=<vnum>` → `spawn_mob(vnum)` then place into the PC's room
- `__tick` → `violence_tick(do_combat=True)`

Add the combatant mob to the scenario's `watch_chars` so its HP/position are
snapshotted and compared each step.

## Snapshot extension

Minimal. The combatant mob joins the watched chars; `CharSnap` already carries
`hp` / `position` / `fighting`. Combat hit/miss/damage text flows through the
existing output channel (command return value + drained `char.messages`,
normalized identically to the C descriptor buffer). **`wait` is deliberately
excluded from the v1 snapshot** (see Risk 2).

## Scenario files

**v1 `tools/diff_harness/scenarios/combat_melee_rounds.json`:**
```
boot   seed=<n> start_room=3001 level=5 char=tester
__seed=<n>
__mload=3064
__seed=<m>
kill drunk
__tick   (snapshot)
__tick   (snapshot)
__tick   (snapshot)
__tick   (snapshot)
```
Snapshots watch the PC and the drunk: HP decrements, position, fighting target,
and the per-round combat output. The two reseeds are distinct on purpose: the
seed before `__mload` makes the spawn deterministic (belt-and-suspenders for 3064,
which draws no spawn RNG, but required for any future combatant with real HP
dice); the seed before `kill` makes the combat rounds deterministic. The concrete
seed values and the round count `N` are tuned during plan implementation — capture
once, observe the HP curve, pick `N` so the mob stays alive across all snapshots.

**v2 `tools/diff_harness/scenarios/combat_to_death.json`** *(follow-up cycle)*:
same prefix, `__tick` repeated until the mob dies; final snapshots capture corpse
creation, the PC's XP/gold delta, and `fighting` cleared.

## Testing & the loop

Capture v1 golden from the C shim (`python3 -m tools.diff_harness.capture
--scenario combat_melee_rounds`), commit it, replay through Python, first-
divergence comparator. Each divergence is recorded in `tools/diff_harness/
FINDINGS.md` and closed on master via `rom-gap-closer` (the proven MOVE-003 /
LOOK-004 loop). Combat damage-message wording is a known parity surface, so v1
may surface 0–2 findings — that is the harness working as intended.

## Risks (carried into the implementation plan)

1. **RNG cascade.** Combat is a sequence sharing one stream; one extra/missing
   draw early offsets every later round, so a single root cause presents as
   "everything after round 1 differs." Diagnose by RNG-draw count, not by
   symptom. The `__seed` boundary bounds the blast radius to combat code.

2. **`do_kill` sets lag.** `src/fight.c:2317` — `WAIT_STATE(ch, PULSE_VIOLENCE)`.
   Descriptor-burn paths differ (connected players burn one pulse at a time; the
   descriptor-less harness PC burns in `PULSE_VIOLENCE` chunks in
   `violence_tick`). Mitigated for v1 by **excluding `wait` from the snapshot**,
   so the divergence is unobserved. **Must confirm `violence_update` does not
   gate `multi_hit` on `wait`** — if it did, a waited PC would stall the fight
   and no rounds would resolve. This is the implementation plan's first
   verification step.

3. **Stub-stat drift.** If `make_test_char` (C) and `create_test_character`
   (Python) differ on any combat-input stat or attack-skill level, per-round
   draw counts diverge. Reconcile the full combat-input surface as an explicit,
   tested step (FINDING-002 pattern). Harness-only; never touch the shared
   `create_test_character` callers' contract.
