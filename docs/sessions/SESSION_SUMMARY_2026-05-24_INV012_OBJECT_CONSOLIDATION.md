# Session Summary — 2026-05-24 — INV-012 OBJECT-LIST-CANONICAL

(Third pass on the cross-file invariants list this day; follows
[SESSION_SUMMARY_2026-05-24_INV011_CARRY_WEIGHT_COHERENCE.md](SESSION_SUMMARY_2026-05-24_INV011_CARRY_WEIGHT_COHERENCE.md).)

## Outcome

- New cross-file invariant **INV-012 OBJECT-LIST-CANONICAL** added to
  `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`, locked in by an
  8-test enforcement suite in
  `tests/integration/test_inv012_object_list_canonical.py`.
- The watch-list "Dual `Object` / `ObjectData`" entry — opened during
  the INV-011 session as the highest-value open candidate — is closed
  as INV-012.
- Production payoff (the bug this was actually fixing): every
  iteration over `object_registry` was a no-op in production because
  the registry was never populated. Locate-object spells, mobprog
  oload triggers, global object scans, music decay, and object
  decay tick all silently iterated an empty list. After this
  session, `spawn_object` populates the registry and `_extract_obj`
  drains it; those code paths now execute against real data for the
  first time.
- Version bumped 2.8.79 → **2.9.0** (minor — newly-live behavior).
  CHANGELOG updated. CROSS_FILE_INVARIANTS_TRACKER closed at 12 of
  ~20 budget; watch list now reads "Open: none right now."
- Implementation followed the
  brainstorming → writing-plans → using-git-worktrees →
  subagent-driven-development pipeline. Spec at
  `docs/superpowers/specs/2026-05-24-object-objectdata-consolidation-design.md`
  (rev 2 post-critique). Plan at
  `docs/superpowers/plans/2026-05-24-object-objectdata-consolidation.md`.

## Commit ladder (this branch)

Branch: `inv-012-object-consolidation` off master at `adab7f78`.

| # | SHA (short) | Phase | Summary |
|---|-------------|-------|---------|
| 1 | `e33d0df1` | 1a | Add `in_room`/`in_obj`/`carried_by` dataclass fields to `Object` (incl. `mob_cmds._extract_runtime_object` hasattr→isinstance fix that the field-addition surfaced) |
| 2 | `6d5a121c` | 1b | `pIndexData` `@property` aliases `prototype` (read+write) |
| 3 | `fa6af66e` | 1c | `contains` `@property` aliases `contained_items` (read-only) |
| 4 | `df905a78` | 2 | `spawn_object` appends to `object_registry`; retype list as `list[Object]`; autouse cleanup fixture; 5 new tests (registry membership + recursive extract + `get_obj_world` smoke + `obj_update` smoke) |
| 5 | `c8b13664` | 3b | Retype `mud/handler.py` affect helpers `ObjectData → Object` |
| 6 | `fef2923d` | 3a | Retype 17 helpers in `mud/game_loop.py` `ObjectData → Object` |
| 7–15 | `a614f11a`…`516e3ecd` | 4 | Migrate 9 test files from `ObjectData(...)` to `Object(instance_id=None, prototype=ObjIndex(...))` (35 constructor sites) |
| 16 | `3e397a8d` | 3c+3d | Collapse 3 single-arm + 9 tuple-filter `isinstance(ObjectData)` branches in `mud/skills/handlers.py`; drop `Object \| ObjectData` unions |
| 17 | `439b6cfe` | 3f | Delete 4 dual-shape `getattr(obj, "contained_items", None) or getattr(obj, "contains", [])` fallbacks in `mud/game_loop.py` |
| 18 | `874473dd` | 3g | Straggler sweep — `mud/music`, `mud/ai`, dead `isinstance` branch in `mud/mob_cmds._extract_runtime_object` |
| 19 | (this commit) | 5 | Delete `ObjectData` class; drop re-export from `mud/models/__init__.py`; add INV-012 row; bump 2.9.0; CHANGELOG + session handoff |

17 implementation commits total (Tasks 1a–4 + 3 separate Task 3 commits + Task 5). Within the 15–25 estimate from the spec.

## Process learnings

1. **The plan's ordering of Tasks 3 → 4 was wrong.** Tasks 3c–3d
   tighten the isinstance checks to require `Object`. The existing
   tests constructed `ObjectData` and broke as soon as the checks
   tightened. **Resequenced inline**: did Task 4 (test migration)
   before re-running Task 3c–3d. Spec's commit ordering was kept on
   paper, but execution flowed 1a → 1b → 1c → 2 → 3a → 3b → 4 → 3c
   → 3d → 3f → 3g → 5. Cleaner mental model for future "lift names
   onto X, then delete Y" consolidations.
2. **The advisor / reviewer found 6 critical flaws in the spec's
   rev 1** (hatasr-vs-isinstance pitfalls, dataclass-property
   collisions, undercounted commits, unsafe Phase 2 worktree
   parallelism). Rev 2 of the spec absorbed all of them. Doing
   review-before-write pays off.
3. **The Task 1a edit triggered a real bug surface** —
   `mob_cmds._extract_runtime_object` had a hasattr-based heuristic
   to detect `ObjectData` ("if the obj has `in_room`/`in_obj`/
   `carried_by`/`contains` attrs, route to legacy `_extract_obj`").
   After Task 1a made those fields real on `Object`, the heuristic
   false-positived on every `Object`. Caught by an existing test
   (`test_mpjunk_removes_equipped_items_and_nested_contents`); fix
   was to replace the heuristic with an explicit
   `isinstance(obj, ObjectData)` (and later in Task 3g, delete the
   branch entirely once `ObjectData` was scheduled for removal).
4. **Subagent dispatch worked well at the right grain.** Task 2
   (load-bearing behavioral commit) needed a single focused agent.
   Task 3a + 3b (annotation-only sweep) parallelized cleanly. Task 4
   (9 mechanical fixture migrations) ran best as a single subagent
   doing all 9 sequential commits — vs. 9 separate dispatches with
   per-agent setup overhead. Tasks 3c–3g were small enough to do
   inline.

## Verification

Final gate (run from the worktree, on the consolidation branch):

- `python3 -m pytest` → 4686 passed + 1 pre-existing failure
  (`test_wait_and_daze_decrement_on_violence_pulse`, unchanged from
  master baseline). Includes 8 INV-012 enforcement tests.
- `grep -rn "ObjectData" mud/ --include="*.py" | grep -v "comment\|docstring"`
  → only comments/docstrings remain as audit trail.
- `grep -rn "ObjectData(" tests/ --include="*.py"` → 0 results.
- `pyproject.toml` version → `2.9.0`.
- CROSS_FILE_INVARIANTS_TRACKER `INV-012 row` → ✅ ENFORCED;
  watch-list entry struck through.

## Followups for next session

- **`mud/magic/effects.py` `isinstance(target, Object)` filters
  (5 sites)** are now tautological after the dual-class consolidation.
  Simplify in a one-commit cleanup (Task 3e was deferred per spec).
- **End-to-end coverage of the newly-live systems** (locate-object
  spell hits a spawned object; mobprog oload trigger fires; full
  object decay sequence end-to-end). The INV-012 smoke tests cover
  `get_obj_world` and `obj_update` direct callability; integration
  tests over the gameplay surface are *new coverage*, not part of
  this consolidation. Worth a dedicated test session.
- **Phase 2 field renames** (the deferred `prototype → pIndexData`,
  `location → in_room`, `contained_items → contains` across 71
  files) — purely cosmetic ROM-parity polish. Own session, own INV
  if pursued.
- **Pre-existing
  `test_wait_and_daze_decrement_on_violence_pulse` failure** is
  still on master. Unrelated to this work, but increasingly visible
  every session it remains red.

## Branch state

Local commits only — never pushed. Branch
`inv-012-object-consolidation` (HEAD `<this-commit>`) sits ready
for the user's review/merge/push decision. Per session push-gate,
no `origin/master` push without explicit per-cluster approval.
