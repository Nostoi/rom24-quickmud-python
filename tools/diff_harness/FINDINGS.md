# Differential Harness — Findings

Divergences the harness has surfaced between the Python port and the ROM C
reference. Each is recorded here durably (per AGENTS.md "file durably, don't just
mention") and gated as a `KNOWN_DIVERGENCES` entry in
`tests/test_differential_smoke.py` (an `xfail` that auto-clears when the diff
goes clean). Resolving the root cause is separate from building the harness.

---

## FINDING-007 — mob spawn RNG draw-order diverges (gold vs HP) — 🔴 OPEN, gates combat v1

**Status:** 🔴 OPEN — **real Python parity bug.** Surfaced 2026-05-28 by the
`combat_melee_rounds` scenario: the drunk #3064 spawns at HP **31** in ROM C vs **33**
in Python from the *same* seed (777). Both roll the correct `2d6+22` (FINDING-006 is
fixed); the values differ because the two engines draw RNG in a **different order**
during mob creation.

**Root cause.** ROM `create_mobile` (`src/db.c:2047-2091`) draws in this order:
1. **gold/wealth** — `number_range(wealth/2, 3*wealth/2)` then `number_range(wealth/200, wealth/100)` (2 draws when `wealth > 0`),
2. **HP** dice, 3. **mana** dice, 4. random damtype via `number_range(1,3)` *only if* `dam_type == 0`.

Python `MobInstance.from_prototype` (`mud/spawning/templates.py:364-394`) draws:
1. random damtype (`number_range(1,3)`) *first* if `dam_type == 0`,
2. **HP**, 3. **mana**, 4. **gold** *last*.

So gold is drawn last in Python but first in ROM, and the damtype roll is first vs
last. The drunk has `wealth=65 > 0`, so ROM's 2 gold draws precede its HP roll while
Python's don't — shifting the `2d6`. This affects **every seed-dependent mob spawn**
game-wide (mob stats diverge from ROM), latent because the suite uses synthetic mobs.

**Fix shape (master gap-closer, e.g. SPAWN-001 / a templates.py row):** reorder
`from_prototype`'s RNG draws to match `create_mobile` exactly — gold/wealth first, then
HP, then mana, then the `dam_type == 0` random roll last. Bounded to one function;
expect possible seeded-test fallout (it changes spawn RNG order). Same pattern as
DB2-007: a real Python parity bug surfaced by the harness, fixed on master, then
re-run the differential (the `combat_melee_rounds` `KNOWN_DIVERGENCES` xfail
auto-clears when the diff goes clean).

**Gated:** `combat_melee_rounds` is in `KNOWN_DIVERGENCES` (xfail) until this lands.

---

## FINDING-006 — area JSON mob HP/mana/damage dice are mislabeled (field-shifted) — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-05-28 via **DB2-007** (master 2.11.2, commit `1857b5f8`).
Root cause was a phantom scalar `ac` token at stat-line index [2] in
`mud/loaders/mob_loader.py` (ROM has no scalar AC there — it's on the next line), which
shifted every dice field by one and dropped the real HP dice. Fixed; all 52 area JSONs
regenerated; full suite 4925/0. The per-file `DB2_C_AUDIT.md` Phase 2 had marked this
stat line ✅ — corrected. Regression: `tests/test_mob_dice_parity.py`.

**Combat-v1 follow-on (not a data bug — normal harness RNG-alignment work):** with the
fix, the drunk #3064 now rolls `2d6+22` on both engines, but the *value* still differs
(C 31, Python 33) because the RNG stream position at `__mload` time isn't yet aligned
between `create_mobile` and `from_prototype` (seeding convention and/or spawn draw
order). The combat scenario's `__seed`-before-`__mload` + matched-stub tasks address
this; the first capture will surface it as the mob's starting-HP diff to triage.

### (historical, root-cause notes below)

**Status:** 🔴 OPEN — **real, systematic Python parity bug.** Surfaced 2026-05-28 while
preparing the combat differential scenario (drunk #3064 spawned at 100 HP in Python
vs 31 in ROM C). **Blocks** `combat_melee_rounds` (the combatant's HP cannot match
across engines until fixed).

**Root cause.** ROM new-format mob stat line (`src/db.c` `load_mobiles`) is
`level hitroll <hp-dice> <mana-dice> <dam-dice> damtype`. The `.are`→JSON conversion
that produced `data/areas/*.json` shifted these by one field:

| JSON field | Holds (wrong) | Should hold |
|------------|---------------|-------------|
| `hit_dice` | the `.are` **mana** dice | the `.are` **HP** dice |
| `mana_dice` | the `.are` **damage** dice | the `.are` **mana** dice |
| `damage_dice` | the **damtype** word (e.g. `"beating"`) | the `.are` **damage** dice |

The real HP dice is dropped entirely. `MobInstance.from_prototype`
(`mud/spawning/templates.py:374`) then rolls `max_hit` from `hit_dice` — i.e. from the
mana dice — so every JSON-loaded mob has the wrong HP, mana, and damage.

**Evidence (drunk #3064, room 3008, seed 777):**
- `area/midgaard.are`: `2 -1 2d6+22 1d1+99 1d6+0 beating` → HP `2d6+22`, mana `1d1+99`, dam `1d6+0`.
- C shim (`src/diffshim`, = ROM loading the `.are`): `max_hp = 31` (a `2d6+22` roll).
- Python `spawn_mob(3064).max_hit = 100` (parsed `1d1+99`, the **mana** dice).
- Hassan #3001 `.are` HP `1d1+999` → ROM 1000 HP; JSON `hit_dice='1d1+99'` → Python 100 HP.

**Scope.** Systematic: **62 of 65** midgaard mobs mismatch on `hit_dice` (the 3 that
"match" do so only because their HP and mana dice are coincidentally equal). Almost
certainly affects **all** `data/areas/*.json`, not just midgaard — i.e. every
JSON-loaded mob game-wide has wrong HP/mana/damage. Latent because the test suite
uses synthetic mobs (`movable_mob_factory` with explicit points), never asserting a
JSON-loaded mob's HP against ROM.

**Fix shape (master, NOT this branch — wide blast radius, needs scoping with the user):**
likely fix the `.are`→JSON converter's field mapping and regenerate every
`data/areas/*.json`, then add a regression that checks a JSON-loaded mob's HP/mana/
damage dice against the `.are`. Route via `rom-gap-closer` once scoped; file the
data-conversion bug in the appropriate tracker. Until fixed, `combat_melee_rounds`
stays uncaptured / out of `KNOWN_DIVERGENCES`.

---

## FINDING-005 — input-source asymmetry (C reads `.are`, Python reads JSON) — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-05-28 — investigated, found **structurally benign**,
and locked with a guard test. This was the last harness-soundness follow-up before
`diff-harness` can merge.

The two engines load world data from different sources: the C shim reads the
repaired `midgaard` `.are` overlay (`src/diff_shim/area/`), the Python replay reads
`data/areas/*.json`. The concern (carried from FINDING-001's "separate latent
issue") was that for midgaard scenarios the two might load **different** data and
manufacture false divergences.

**Probe result (2026-05-28):** the JSON and the repaired `.are` cover an
**identical** room/mobile/object vnum set (143 / 65 / 160 each; `only in .are=[]`,
`only in JSON=[]`). The JSON was generated from a correctly-parsed (or pre-repaired)
source — it does **not** drop the entities the malformed stock `area/midgaard.are`
would (the `#`→`#ROOMS` / `~ROOMS`→`~` corruption at the OBJECTS→ROOMS boundary
only ever affected the C-side raw parse, which the overlay repairs). So the
soundness coverage is already complete:
- structural drift (a vnum in one source but not the other) → none today;
- field drift on an entity a scenario exercises → caught by the per-step snapshot diff;
- field drift on a non-exercised entity → invisible but irrelevant (not exercised).

**Fix:** added `tests/test_diff_harness_data_parity.py`, which reconstructs the
repaired `.are` in-Python (byte-identical to the `Makefile.diffshim` `area-overlay`
awk, verified — so it does not depend on the gitignored build artifact) and asserts
its room/mob/object vnum sets equal the JSON the Python loader reads. Any future edit
to either source that desyncs the two engines' world data now fails this guard.

**Not done (deliberately):** repairing stock `area/midgaard.are` + regenerating
`midgaard.json` (Option B). The probe proves it is unnecessary for soundness, and
regenerating the JSON has a wide blast radius across tests asserting current
JSON-loaded state. The overlay + guard is the minimal sound close.

**⚠️ Update (FINDING-006):** this guard checks vnum-set *coverage* only, not field
*values*. FINDING-006 (below) found the JSON's mob HP/mana/damage dice are
field-shifted vs the `.are` — so the two sources are NOT value-equivalent even though
their vnum sets match. The guard should be extended to compare mob dice as part of
FINDING-006's fix.

---

## FINDING-004 — room object list shows obj name, not ROM ground `description` — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-05-28 via **LOOK-004** (master 2.10.5, commit `2e5ebf3f`).
The `_describe_room` object loop now emits `obj.description` (ROM
`format_obj_to_char` fShort=FALSE) and skips description-less objects. Merged into
this branch; the differential `movement_get_drop` diff is clean. (Aura/stat
prefixes remain a separate latent gap, noted in the audit.) Original analysis below.

**Status (historical):** Open — **real parity bug** (object analog of FINDING-001/LOOK-001).
Surfaced once the harness output capture was made fair (see "Harness soundness
fixes" below). On `look`/auto-look, ROM lists each object lying in a room by its
**`description`** (the long ground line), e.g. `"A pit for sacrifices is in front
of the altar."` Python (`mud/world/look.py:171-173`) lists `obj.short_descr or
obj.name`, e.g. `"the donation pit"`.
- **ROM C:** `src/act_info.c` `do_look` room display → `show_list_to_char` →
  `format_obj_to_char(obj, ch, FALSE)` emits `obj->description` for ground items.
- **Python:** `mud/world/look.py:172-173` (`_describe_room` object loop).
- **Fix (master gap-closer, e.g. `LOOK-003`/`OBJ-DESC-001`):** show the object's
  `description` for items on the ground; fall back to short_descr only when
  `description` is empty. Mirror the LOOK-001 long_descr approach.
- Gated under `KNOWN_DIVERGENCES["movement_get_drop"]` until fixed on master.

---

## FINDING-003 — movement emits a non-ROM "You walk <dir> to <room>." line — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-05-28 via **MOVE-003** (master 2.10.4, commit `ab8f9bd9`).
`move_character` now returns the destination room view (ROM `act_move.c:204`
`do_look "auto"`) instead of the "You walk" line; ~25 assertions across 14 files
were updated to the ROM-faithful output. Merged into this branch; the differential
`movement_get_drop` diff is clean. Original analysis below.

**Status (historical):** Open — **real parity bug.** Surfaced once the harness output capture
was made fair. On `north`/`south`, ROM shows only the destination room
(`do_look auto`); the mover gets **no** "you walk" line. Python
(`mud/world/movement.py:455,470`) returns `"You walk {dir} to {room}."`, which the
live server (`mud/net/connection.py:1981`) sends to the player **before** draining
the auto-look messages — so a Python player sees an extra line AND in the wrong
order (walk-line → room; ROM: room only).
- **ROM C:** `src/act_move.c:204` — `do_function(ch, &do_look, "auto");` is the
  only output to the mover; there is no walk-line anywhere in `move_char`.
- **Python:** `mud/world/movement.py:455` and `:470` (`move_character` return).
- **Fix (master gap-closer, e.g. `MOVE-001`):** drop the `"You walk ..."` return
  string; keep the `_auto_look(char)` call. Note the **ordering** is part of the
  bug — the same fix resolves both (remove the pre-room line, leaving room-only).
  Audit fallout in any test asserting the `"You walk ..."` return.
- Gated under `KNOWN_DIVERGENCES["movement_get_drop"]` until fixed on master.

---

## Harness soundness fixes — 2026-05-28 (this commit)

Three start-state / capture asymmetries that made the harness's diffs untrustworthy
were reconciled (harness-only changes — no ROM `src/` edits, no production `mud/`
edits). These are NOT parity bugs; they were unfairness in the comparison itself:

1. **Test-character HMV (FINDING-002, resolved below).** Python now seeds the
   harness char with ROM `new_char()` defaults (recycle.c:299-304: hp/max=20,
   mana/max=100, move/max=100) so it matches the C shim's `make_test_char`.
   `tests/test_differential_smoke.py`.
2. **Scenario `level` not passed to C.** `capture.py:_drive` boot line now includes
   `level={char_level}` (the C shim already parsed it). Previously C always booted
   at level 1 while Python set the scenario level — a hidden second divergence the
   first-divergence comparator masked behind the hp diff.
3. **Snapshot people-key field.** `pysnap._room_snap` now keys room occupants the
   way the C shim's `char_key` does — first word of ROM's `ch->name`, which for a
   mob is the keyword list (`MobIndex.player_name`, e.g. `"healer"`), not the
   display `short_descr` (`"the healer"`). PCs key on their own name.
4. **Output capture channel.** The replay now captures the full player-visible
   output — the command return value followed by drained `char.messages`
   (send_to_char delivery), mirroring the live server loop
   (`mud/net/connection.py:1979-2000`) — instead of the return value alone. This
   is what surfaced FINDING-003 and FINDING-004 above.

The golden was recaptured (only `char.level` 1→5 changed; output arrays
unchanged, confirming the C side was untouched).

---

## FINDING-002 — test-character hp/level differ between C shim and Python replay — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-05-28 — harness-soundness (not a parity bug). Two
parts: (a) Python's `create_test_character` (a shared test stub, not ROM's
new-player path) left hp/mana/move at the dataclass default 0 while the C shim's
`make_test_char` copied ROM `new_char()` defaults (20/100/100); (b) `capture.py`
never passed the scenario `level=` to the C shim, so C booted at level 1 vs
Python's level 5. Both reconciled as harness start-state fixes (see "Harness
soundness fixes" above): the replay seeds the recycle.c HMV defaults and the boot
line now carries `level=`. Golden recaptured. The remaining `movement_get_drop`
divergences are the real parity bugs FINDING-003 + FINDING-004.

---

## FINDING-001 — `look` renders room NPC by name, not ROM long_descr — ✅ RESOLVED

**Status:** ✅ RESOLVED 2026-05-28 via **LOOK-001** (master 2.10.1) + **LOOK-002**
(2.10.2). It was a real, broad parity bug after all (not the data asymmetry):
`MobInstance` didn't carry `long_descr`/`description` from its prototype (ROM
`create_mobile`) and `mud/world/look.py` used the PERS path instead of
`show_char_to_char_0`'s long_descr branch. Fixed on master; the differential
room/output rendering now matches the C reference exactly. The scenario's
remaining xfail is FINDING-002 (character hp), a separate harness-soundness item.
Historical investigation notes retained below.

### (historical) root-cause investigation

**Status:** ROOT CAUSE CONFIRMED (2026-05-28) — real, broad parity bug; fix
pending (xfailed in `movement_get_drop`). It is **not** the malformed
`midgaard.are`: Python loads area data from JSON (`initialize_world(use_json=True)`),
and the JSON Hassan *prototype* has the correct
`long_descr = "Hassan is here, waiting to dispense some justice.\n"`. The earlier
"diagnostic nondeterminism" was transient (the area overlay was still being
written by the build subagent); it is now stable: 986 mobs, exactly 1
(vnum 2006, unrelated) without a prototype long_descr.

**Confirmed root cause (two parts):**
1. **`mud/world/look.py:151-156`** renders each room occupant via
   `describe_character()` — which returns ROM `PERS` (short_descr/name + affect
   auras), e.g. `"Hassan"`. ROM's `show_char_to_char_0` (`src/act_info.c`)
   instead prints an NPC's **`long_descr`** when `IS_NPC(victim)`, its long_descr
   is non-empty, and `victim->position == victim->default_pos`; otherwise it
   falls back to a `PERS`+position line. So Python uses the wrong renderer for the
   room occupant list — **every room `look` shows NPC names instead of ROM long
   descriptions.**
2. **`mud/spawning/templates.py` `MobInstance`** has no `long_descr` field and
   `from_prototype` never copies it, so even once look.py is fixed the instance
   would read `None`. ROM `create_mobile` (`src/db.c:2040`) does
   `mob->long_descr = str_dup(pMobIndex->long_descr)`.

**Fix shape (a real parity fix — belongs on `master`, not just this branch):**
- Add `long_descr` (and likely `description`) to `MobInstance`; copy from the
  prototype in `from_prototype` (mirror `create_mobile`).
- In `look.py` room-occupant rendering, implement `show_char_to_char_0`: for an
  NPC in its `default_pos` with a non-empty `long_descr`, emit the long_descr
  (with affect prefixes); else fall back to the existing PERS+position path.
- **Wide blast radius:** changes room-look output for ALL NPCs game-wide. Expect
  fallout in any test asserting the current name-based room rendering — triage
  each (a test asserting non-ROM behavior is a test bug per AGENTS.md). Do this
  as a `/rom-gap-closer` with a failing test first.
- When fixed, the differential `movement_get_drop` diff goes clean and the
  `KNOWN_DIVERGENCES` entry is removed.

**Separate latent issue (harness soundness, not FINDING-001):** the C side reads
`.are` files (a repaired midgaard overlay) while Python reads `data/areas/*.json`.
For midgaard-based scenarios the two engines load from different sources. **This is
now resolved — see FINDING-005:** the two sources were proven to cover an identical
vnum set, and `tests/test_diff_harness_data_parity.py` guards the equivalence.

### (historical) original triage notes

**Symptom:** In room 3001 (Temple of Mota), `look`:
- ROM C: `Hassan is here, waiting to dispense some justice.` (mob `long_descr`)
- Python: `Hassan` (mob name)

Every other room-description line matches byte-for-byte after normalization;
this is the only divergence in the movement_get_drop scenario.

**Why the root cause is ambiguous (two confounded causes):**

1. **Unequal inputs (harness fairness).** `area/midgaard.are` is malformed vs
   stock ROM 2.4 (bare `#` instead of `#ROOMS` at the OBJECTS→ROOMS boundary;
   the `ROOMS` keyword migrated onto the previous record's `~` terminator as
   `~ROOMS`). The C shim reads a **repaired** midgaard via a generated overlay
   (`src/diff_shim/area/`), while the Python replay reads the **original**
   `area/midgaard.are`. So for midgaard rooms the two engines may not be reading
   identical data, which can manufacture false-positive divergences. This must
   be reconciled before midgaard divergences can be trusted as real: either
   repair `area/midgaard.are` in the tracked data (so both engines read the
   well-formed file) or point the Python replay at the same repaired overlay.

2. **Possible prototype-vs-instance `long_descr` gap (unconfirmed).** Direct
   inspection showed the spawned Hassan *instance* in `room.people` had
   `long_descr = None`, yet a sweep of `mob_registry` *prototypes* returned
   inconsistent counts across identical runs (one run: 1 mob without long_descr;
   the next: 0). **That nondeterminism is itself unexplained and must be pinned
   first** — it may indicate registry state leakage or that instances don't
   inherit `long_descr` from their prototype. Until it's understood, do not
   conclude this is purely a data problem.

**Next triage steps (separate session):**
1. Pin the `mob_registry` long_descr count nondeterminism (run the same probe
   repeatedly; identify what state differs).
2. Reconcile inputs: parse the *repaired* midgaard with the Python loader and
   check whether Hassan's `long_descr` populates. If yes → the cause is the
   malformed `area/midgaard.are`; repair it (matching stock ROM) so both engines
   read the same data, then re-run the harness.
3. If `long_descr` is still `None` from a well-formed file → real Python
   loader/instance bug; fix it (ROM is source of truth) and file the gap.
4. When the diff goes clean, remove the `movement_get_drop` entry from
   `KNOWN_DIVERGENCES`.

**Meta:** This is the harness working as intended — it found a real
discrepancy (and a data-integrity question about `midgaard.are`) on its first
run. The value is in surfacing it; the fix is deliberately deferred so the
harness can land green-with-findings.
