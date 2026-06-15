# Session Summary — 2026-06-15 — Tick-aggression regression-prevention trio (FIGHT-077 / SPEC-017 follow-up)

## Scope

Follow-up to the FIGHT-077 + SPEC-017 fixes (v2.14.115). Those two commits
restored tick-driven behavior (aggressive mobs attacking; spec-fun flavor
reaching idle connected players), but the *root-cause classes* — a fabricated
`is_safe` gate silently over-blocking, and mailbox-only delivery being invisible
to an idle PC — had no mechanical guard against reintroduction. This session
landed the three-part regression-prevention package the user authorized ("Go
ahead and do those things"): a Layer-A static grep-guard, an AGENTS.md doc rule,
and a diff_harness C-oracle scenario.

## Outcomes

### (a) Layer-A grep-guard for message-delivery — ✅ SHIPPED (v2.14.116, commit 5e7ca15c)

- **Test**: `tests/test_message_delivery_convention.py` — static scanner over
  `mud/` forbidding `<entity>.messages.append(...)` and the two-step
  `m = getattr(x, "messages"); m.append(...)` bypass outside the single-delivery
  chokepoint.
- **Allowlist**: 7 genuine chokepoints/accessors (`_LEGITIMATE`) + 14 frozen
  INV-001 debt sites (`_INV001_DEBT`), with an orphan check that fails if a
  closed entry isn't removed (self-cleaning ratchet).
- Same idiom as `test_rng_determinism.py` / `test_equipment_key_convention.py`
  (Layer-A in `DIVERGENCE_CLASS_ROSTER.md`).

### (c) AGENTS.md doc rule — ✅ SHIPPED (v2.14.116, commit 5e7ca15c)

- AGENTS.md "Message Delivery (Architectural Divergence)" now cites the guard so
  the standard (connected PCs receive via `push_message`, mailbox is test/
  disconnected fallback only) is enforced going forward.

### (b) diff_harness `aggression_onset` scenario — ✅ SHIPPED (v2.14.117, commit 55134261)

- **Scenario**: `tools/diff_harness/scenarios/aggression_onset.json` — mloads
  AGGRESSIVE mob 3704 ("the aggressive monster", level 1, `ABF` =
  NPC|SENTINEL|AGGRESSIVE, not WIMPY) into an idle level-5 PC's room (3008),
  seed 777, one `__aggr_update` pulse.
- **Golden**: `tests/data/golden/diff/aggression_onset.golden.json` — C-engine
  ground truth: PC → `FIGHTING`, hp 20→16, mob → `FIGHTING`, output
  "The aggressive monster's claw injures you." on the socket.
- **New step-handlers** added to BOTH engines (mirrored):
  - C shim: `src/diff_shim/diffmain.c` `__aggr_update` → `aggr_update()`
    (ROM `src/update.c:1077`, non-static so reachable without touching read-only
    ROM source).
  - Python: `tools/diff_harness/pyreplay.py` `__aggr_update` →
    `mud.ai.aggressive_update`.
- **RNG draw-order parity**: the minimal scenario (one seed, one mload, one
  pulse) consumes only the identical mob-spawn path before the aggression coin
  `number_bits(1)`; seed 777 fired the coin on the first capture. Python replay
  matches the C golden exactly — the scenario **passes** (not skip, not xfail).
- Locks the FIGHT-077 fix (a reintroduced `is_safe` level-gate) and the SPEC-017
  tick-time socket-delivery contract (a regression to mailbox-only delivery)
  mechanically against the immutable C trace.

## Files Modified

- `src/diff_shim/diffmain.c` — new `__aggr_update` C step-handler (additive
  harness shim; ROM `src/*.c` untouched). C binary rebuilt via
  `make -f Makefile.diffshim diffshim`.
- `tools/diff_harness/pyreplay.py` — new `__aggr_update` Python step-handler.
- `tools/diff_harness/scenarios/aggression_onset.json` — new scenario.
- `tests/data/golden/diff/aggression_onset.golden.json` — new C golden.
- `tests/test_message_delivery_convention.py` — new Layer-A guard (commit 5e7ca15c).
- `AGENTS.md` — Message Delivery section cites the guard (commit 5e7ca15c).
- `CHANGELOG.md` — Added entries for the guard and the scenario.
- `pyproject.toml` — 2.14.115 → 2.14.116 (guard) → 2.14.117 (scenario).

## Test Status

- `pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py -n0` —
  68 passed (41 scenarios incl. `aggression_onset` + unit tests).
- `tests/test_message_delivery_convention.py` — green (guard + orphan check).
- `ruff check tools/diff_harness/pyreplay.py` — clean.
- Full suite not re-run this session (changes are additive harness/test only; no
  `mud/` production code touched after v2.14.115's 5812-passing baseline).

## Next Steps

Regression-prevention trio complete. Open follow-ups unchanged from the
FIGHT-077/SPEC-017 summary, in priority order:

1. **INV-001 debt burndown** — 14 frozen `_INV001_DEBT` sites in the guard, each
   an INV-001 "Touched by" row; migrate to `push_message` one at a time (clean
   ROM-confirmed fix, TDD, ROM citation, delete its allowlist line). Candidates:
   `thief_skills.py:253`, `connection.py:766/787`, `dispatcher.py:1201`,
   `communication.py:29`, `magic_items.py:319`, `skills/handlers.py` (4 sites),
   `skills/registry.py` cluster.
2. **Vestigial dual-channel in `process_weapon_special_attacks`**
   (`mud/combat/engine.py`) — latent INV-001 footgun, not yet a stable ID.
3. **DELETE-002 🔄 OPEN**, **STEAL-015 🔄 OPEN**, **INV-050 bool-retirement**,
   `mud/entrypoint.py` dead code — as previously tracked.
4. Per `DIVERGENCE_CLASS_ROSTER.md`: Hypothesis state-machine → diff_harness
   widening (Class 11 / Phase C) remains the higher-yield enumeration-independent
   lever.
