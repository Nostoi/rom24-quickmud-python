# Handoff — DB-003: O-reset population semantics (dedicated reset-path audit)

**Status:** OPEN, scoped, not started. Filed `DB-003` in
`docs/parity/DB_C_AUDIT.md`. This doc consolidates the scattered notes into one
actionable starting point. Use **`/rom-parity-audit`** (reset/spawning path), NOT
`/rom-gap-closer` — see "Why this is audit-sized" below.

---

## The divergence (ROM vs Python)

**ROM `reset_room` O-case — `src/db.c:1754-1786`:**

```c
case 'O':
    // validate obj index (arg1) and room index (arg3)...
    if (pRoom->area->nplayer > 0
        || count_obj_list (pObjIndex, pRoom->contents) > 0)   // <-- ≥1 already → skip
    {
        last = FALSE;
        break;
    }
    pObj = create_object (pObjIndex, UMIN(number_fuzzy(level), LEVEL_HERO-1));
    pObj->cost = 0;
    obj_to_room (pObj, pRoom);                                // exactly ONE
    last = TRUE;
    break;
```

ROM places **at most one** instance of the object **per room**, with **no global
count limit**. `arg2` and `arg4` are **completely unused** for O-resets.

**Python `apply_resets` O-branch — `mud/spawning/reset_handler.py:502-552`
(+ the `room_obj_targets` precompute at `:385-389`):**

Two divergences:

1. **(a) per-room over-placement.** Python precomputes
   `room_obj_targets[(room_vnum, obj_vnum)]` = *the number of O-reset commands*
   for that pair (`:385-389`), then allows that many copies
   (`desired_total`, `:521-522`). ROM skips on `count_obj_list > 0` → exactly one.
   Reachable: many obj vnums have multiple O-resets across rooms; **obj 3200 has
   15 O-resets** (176 O-resets total in shipped `area/*.are`).
2. **(b) synthetic global cap.** Python applies
   `limit = _resolve_reset_limit(reset.arg2)` and skips if
   `object_counts[vnum] >= limit` (`:526-530`). ROM has **no** such cap for O
   (arg2 is unused). Where an obj's O-reset room-count exceeds its arg2 limit,
   Python **under-places** vs ROM.

Net world-object population can diverge in **either** direction.

3. **(c) POSSIBLE THIRD divergence — verify during the audit (advisor-flagged,
   not yet confirmed):** ROM's O-case looks up `pRoomIndex` from `arg3` for
   validation but then calls `obj_to_room(pObj, pRoom)` — placing into `pRoom`
   (the reset's *current* room context), not necessarily `get_room_index(arg3)`.
   Python keys placement off `arg3`'s room (`room_registry.get(room_vnum)` where
   `room_vnum = reset.arg3`). Confirm whether ROM `pRoom` and `arg3`'s room can
   differ for an O-reset, and which Python should follow. (For most areas they
   coincide; the question is the edge case.)

---

## Why this is audit-sized (NOT a gap-closer single-commit)

A `/rom-gap-closer` close needs *one failing→passing test + green suite = done*.
DB-003 fails that bar:

- **Whole-world population shift, both directions.** A synthetic unit test proves
  the *mechanism* flipped; it does **not** prove Midgaard's actual object
  population now matches ROM. That's a differential / Layer-C question — use
  `tools/diff_harness/` (author a reset-population scenario) or a before/after
  object-count diff against a C run.
- **An unreachable-premise test must be redesigned first:**
  `tests/test_spawning.py::test_reset_P_uses_last_container_instance_when_multiple`
  (line ~683) asserts **2 desks** spawn from 2 O-resets in one room — a scenario
  ROM can never produce (the 2nd O-reset sees `count_obj_list > 0` and skips). The
  real behavior it protects (P-reset picks the *last* container instance) is valid
  ROM behavior and must be re-exercised through a **ROM-valid** setup (e.g. two
  different container vnums, or G/E-placed containers) before the O-reset code can
  change. Until that test is rebuilt, the faithful fix can't land green.

---

## Suggested audit plan

1. **Read** ROM `reset_room` whole-function (`src/db.c:1602-1993`) — O, and how
   `last`/`LastObj`/`pRoom` thread through M→O→P→G→E. Confirm (c).
2. **Excise** Python's non-ROM machinery in the O-branch: drop `room_obj_targets`
   (`:385-389`, `:521-522`) → replace with ROM's `count_obj_list(pObjIndex,
   pRoom->contents) > 0` skip; drop the `_resolve_reset_limit(arg2)` global cap
   for O (`:526-530`). Keep `nplayer > 0`, `cost = 0`, level-fuzzy (those match).
3. **Redesign** `test_reset_P_uses_last_container_instance_when_multiple` to a
   ROM-valid multi-container setup *before* touching the O code (TDD-first).
4. **Differential check:** author/run a `tools/diff_harness/` scenario that diffs
   per-room object counts after a full reset cycle vs the C engine. A unit test is
   necessary but not sufficient here.
5. **Triage fallout:** the population change will ripple through other reset/shop/
   spawn tests — expect to correct any that silently encoded the per-room
   over-placement. Each corrected test must assert ROM behavior, not the old Python.

## Companion item to fold in: ARITH-208

`mud/spawning/templates.py:172` `max(0, rng_mm.dice(number, size) + bonus)` (mob
hp/mana roll). ROM `create_mobile` (`src/db.c:2074-2076`) stores
`max_hit = dice(...) + bonus` **raw** (can be negative) and sets `mob->hit =
max_hit`. Python floors at 0. **Do not remove the source floor alone** — it is
*coupled* to the policy-mandated UB-divisor floors (ARITH-001/002/003/011/012,
kept per `docs/divergences/UB_DIVISORS.md`): keeping `max(1, max_hit)` at the
divisors while removing the source `max(0,…)` yields a **new** sign divergence
(`100 * neg_hit / 1` = large negative `hp_percent`, where ROM gets neg/neg =
positive). Needs **coordinated source + divisor** treatment — same reset/spawn
audit is the natural home.

## Prerequisite at session start

**Confirm the GitNexus MCP server reconnects.** It was DOWN all of 2026-06-19
(`gitnexus_impact` / `detect_changes` returned "Connection closed"); blast radius
had to be verified via grep + full suite. The CLI reindex works fine (`npx
gitnexus analyze --skip-agents-md`), but the MCP query tools are what you want for
a world-population change of this blast radius. A CLI reindex alone does NOT
restore the MCP tools.

## Pointers

- Gap row: `docs/parity/DB_C_AUDIT.md` (search `DB-003`).
- Prior `/loop` session that filed it: `SESSION_SUMMARY_2026-06-19_LOOP_GAPCLOSER_SIGNED_MATH_RESETS.md`.
- Session that scoped this handoff: `SESSION_SUMMARY_2026-06-19_LOOP_GAPCLOSER_ARG4_SPELL_LEVEL_FLOORS.md`.
- Verified-clean baseline: v2.14.171, full suite 5886 passed / 4 skipped.
