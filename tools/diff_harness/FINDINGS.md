# Differential Harness — Findings

Divergences the harness has surfaced between the Python port and the ROM C
reference. Each is recorded here durably (per AGENTS.md "file durably, don't just
mention") and gated as a `KNOWN_DIVERGENCES` entry in
`tests/test_differential_smoke.py` (an `xfail` that auto-clears when the diff
goes clean). Resolving the root cause is separate from building the harness.

---

## FINDING-004 — room object list shows obj name, not ROM ground `description`

**Status:** Open — **real parity bug** (object analog of FINDING-001/LOOK-001).
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

## FINDING-003 — movement emits a non-ROM "You walk <dir> to <room>." line

**Status:** Open — **real parity bug.** Surfaced once the harness output capture
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
For midgaard-based scenarios the two engines load from different sources; this
did not cause FINDING-001 (both prototypes have long_descr) but must be
reconciled before trusting midgaard divergences in general — either regenerate
the JSON from the repaired `.are`, repair `area/midgaard.are` at source, or point
both engines at the same data.

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
