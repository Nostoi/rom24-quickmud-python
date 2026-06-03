# Session Summary — 2026-06-02 — INV-034 pointer-identity root fix

## Scope

Picked up from the prior session's documented next task (SESSION_STATUS 2.12.77,
"Root-fix INV-034 — the highest-value concrete next step"). Last session's
`/rom-divergence-sweep` on divergence class 6 (pointer-identity) had *filed* the
root cause as INV-034 (⚠️ OPEN, Layer C) with a strict-xfail demonstration test,
but deliberately deferred the fix per the probe-only mandate (≈91-site blast
radius; needs a value-equality test-reliance sweep first). This session executed
that scoped fix.

## Outcomes

### `INV-034` POINTER-IDENTITY-COMPARISON — ✅ ENFORCED (root cause FIXED)

- **Python**: every entity **runtime** type flipped to `@dataclass(eq=False)`:
  `mud/models/character.py:392` (`Character`, PCs),
  `mud/spawning/templates.py:240` (`MobInstance`, the live `spawn_mob` mob type
  — **highest-risk** twin case), `mud/models/object.py:14` (`Object`,
  `spawn_object`), and `mud/spawning/templates.py:221` (`ObjectInstance`, legacy
  / uninstantiated, flipped for consistency). `MobInstance`/`ObjectInstance` were
  **caught by adversarial review after the first `Character`/`Object` commit** —
  a single class's `eq=False` does not propagate to sibling non-subclass entity
  dataclasses, and `MobInstance` (not a `Character` subclass) is the actual
  runtime type for mobs in `room.people`.
- **ROM C**: entity compares are pointer (address) compares throughout
  (`src/handler.c` passim; `src/fight.c` `is_same_group`/`stop_fighting` sweep
  `char_list` by pointer). No value-equality concept in C.
- **Gap**: both models were plain `@dataclass` (`eq=True`) → value-based
  `__eq__`, and the spawn path leaves `instance_id`/`id` unset, so two distinct
  same-prototype entities compared `==`-equal. This poisoned the ~91
  `obj in <list>` / `list.remove(obj)` / `.index(obj)` idioms (all `==`-based).
- **Fix**: `@dataclass(eq=False)` on both → `__eq__`/`__hash__` inherited from
  `object` (identity compare + identity hash = ROM pointer semantics; entities
  also become hashable, a pure gain). Updated the now-inert `compare=False`
  comment on `Object`'s graph-pointer fields.
- **Gating sweep (pre-flight, mandated)**: `grep -rn "assert .*(obj|char|victim|
  item).*==" tests/` — every hit was an `.attr` compare or two references to the
  *same* object; **no** test relied on distinct-twin value-equality. Production
  `attacker != victim` / decay-loop `object_registry.remove` sites are
  *corrected*, not regressed.
- **Tests**: `tests/test_inv034_pointer_identity_divergence.py` — the two
  strict-xfail demonstrations flipped xfail→pass; converted to plain assertions
  (a future failure now means a model dataclass regressed to `eq=True`).

### Divergence class 6 (pointer-identity) — ✅ FIXED

Roster class 6 and Layer-C row 12 flipped to FIXED/enforced; the to-do item 5
(root-fix INV-034) marked DONE. Follow-up noted: `Room` is the same class (still
`eq=True`), lower risk (vnum-keyed singletons) — a Room identity test +
`eq=False` flip can land independently.

## Files Modified

- `mud/models/character.py` — `@dataclass` → `@dataclass(eq=False)` + INV-034 docstring note.
- `mud/models/object.py` — `@dataclass` → `@dataclass(eq=False)` + docstring note; updated stale `compare=False` comment.
- `mud/spawning/templates.py` — `MobInstance` + `ObjectInstance` → `@dataclass(eq=False)` + INV-034 docstring notes (the post-commit adversarial-review extension).
- `tests/test_inv034_pointer_identity_divergence.py` — removed strict-xfail markers; converted to plain assertions; added a Character behavioral test + `test_entity_runtime_types_use_identity_equality` regression guard (all four runtime types); docstring → ENFORCED.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-034 row → ✅ ENFORCED (root cause FIXED).
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — class 6 → ✅ FIXED; Layer-C row 12 → enforced; to-do item 5 → DONE.
- `AGENTS.md` — "Entity identity" rule updated: the runtime types `Character`/`MobInstance`/`Object`/`ObjectInstance` now `eq=False` (`==`/`is` agree); `Room` still `eq=True` (value-compare landmine); use `is` for all regardless; added the "`eq=False` doesn't propagate to sibling entity dataclasses" lesson.
- `CHANGELOG.md` — Fixed entry under `[Unreleased]`.
- `pyproject.toml` — 2.12.77 → 2.12.78 → 2.12.79.

## Test Status

- `tests/test_inv034_pointer_identity_divergence.py` — 4/4 passing (was 2 xfailed
  + 2 new regression guards).
- Full suite: **5360 passed, 4 skipped** in 189.81s — +4 vs the 2.12.77 baseline
  (5356) = 2 inv034 demos flipping xfail→pass + 2 new guards; **zero
  regressions**, including the heavily-exercised mob membership/combat paths.
- `ruff check` on edited code lines: clean (templates.py carries pre-existing
  import-sort/UP037 errors, none at the edited lines).
- `gitnexus_impact` on `MobInstance`: LOW (3 importers, 0 processes).

## Commits

- `199827b4` — `fix(parity): root-fix INV-034 — Character/Object identity equality (eq=False) (2.12.78)`
- `fb4b6c0f` — `docs(session): INV-034 pointer-identity root fix summary + SESSION_STATUS (2.12.78)`
- _(this follow-up)_ — `MobInstance`/`ObjectInstance` `eq=False` extension + regression guards (2.12.79), caught by adversarial review.

## Process note (worth keeping)

The first commit (2.12.78) shipped `Character`/`Object` only and claimed class 6
"FIXED" — but `MobInstance` (mobs) and `ObjectInstance` (legacy) are **separate,
non-subclass** `@dataclass`es that regenerate their own value-based `__eq__`, so
they escaped the fix entirely. An `advisor` review caught this before the claim
was relied upon: a green suite **cannot** detect it (the demo test is
Object-only; combat tests use mobs that differ in hp/position, so
`attacker != victim` stays `True` even under value-eq). Lesson now durable in
AGENTS.md: `eq=False` does not propagate to sibling entity dataclasses; each
runtime type needs its own — verified by the new class-level regression guard.

## Next Steps

1. **`Room` identity equality (small follow-up).** Same class as INV-034, lower
   risk (vnum-keyed singletons, but world-load/area tests may compare rooms by
   value). Write a Room identity test mirroring `test_inv034_*`, see it fail,
   flip `mud/models/room.py:Room` to `@dataclass(eq=False)` in its own commit.
   This fully closes divergence class 6 for all three entity types.
2. **Highest-ceiling (deliberate multi-day project):** `diff_harness` Hypothesis
   widening (`tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md`) — the only
   enumeration-independent path to *unknown* divergences.
3. **Standing cross-INV candidate:** mob-trigger ordering (bribe/exit/fight/kill/
   hpcnt); INV tracker consolidation (now 27 rows, past the ~20 soft cap).

> **Push note:** 2.12.78–79 (`199827b4` + this follow-up) are on local `master`, **not
> pushed** — on top of the unpushed 2.12.72–2.12.77 from prior sessions. CHANGELOG/version
> reflect 2.12.79.
