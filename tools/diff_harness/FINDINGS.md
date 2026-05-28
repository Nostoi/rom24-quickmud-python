# Differential Harness — Findings

Divergences the harness has surfaced between the Python port and the ROM C
reference. Each is recorded here durably (per AGENTS.md "file durably, don't just
mention") and gated as a `KNOWN_DIVERGENCES` entry in
`tests/test_differential_smoke.py` (an `xfail` that auto-clears when the diff
goes clean). Resolving the root cause is separate from building the harness.

---

## FINDING-001 — `look` renders room NPC by name, not ROM long_descr

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
