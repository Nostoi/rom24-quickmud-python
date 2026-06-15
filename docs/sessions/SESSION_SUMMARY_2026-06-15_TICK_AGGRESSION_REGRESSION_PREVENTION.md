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

### (b) diff_harness `aggression_onset` scenario — ✅ SHIPPED (v2.14.117 plumbing, **corrected to a load-bearing fixture in v2.14.118**, commit 55134261 + this commit)

- **Scenario**: `tools/diff_harness/scenarios/aggression_onset.json` — mloads
  AGGRESSIVE mob **2302** ("the Cave Dweller", **level 15**, `ABF` =
  NPC|SENTINEL|AGGRESSIVE) into an idle **level-1** PC's room (3008), seed 777,
  one `__aggr_update` pulse. (Snapshot key is `oldstyle`, the first keyword of
  its `player_name` line `oldstyle dweller cave creature~`.)
- **Why a level-15 mob vs a level-1 PC (the fixture that actually guards
  FIGHT-077)**: the deleted gate was `victim_level < char_level - 10`
  (char=attacker mob, victim=PC), so it fires *only* when the mob is >10 levels
  above the player. L15-mob-vs-L1-PC → `1 < 15-10=5` → True → the bug would mark
  the PC safe and the mob would refuse to attack. The original fixture (mob 3704
  L1 vs PC L5) gave `5 < 1-10=-9` → False — the gate never fired, so that
  scenario passed identically with or without the bug and locked nothing. This
  is the actual field repro (Cave Dweller vs a level-1 PC).
- **Golden**: `tests/data/golden/diff/aggression_onset.golden.json` — C-engine
  ground truth: PC → `FIGHTING`, hp 20→13, mob → `FIGHTING`, output
  "The Cave Dweller's pierce decimates you." (+ "That really did HURT!" wimpy
  warning) on the socket.
- **New step-handlers** added to BOTH engines (mirrored):
  - C shim: `src/diff_shim/diffmain.c` `__aggr_update` → `aggr_update()`
    (ROM `src/update.c:1077`, non-static so reachable without touching read-only
    ROM source).
  - Python: `tools/diff_harness/pyreplay.py` `__aggr_update` →
    `mud.ai.aggressive_update`.
- **RNG draw-order parity**: the minimal scenario (one seed, one mload, one
  pulse) consumes only the identical mob-spawn path before the aggression coin
  `number_bits(1)`; seed 777 fired the coin. Python replay matches the C golden
  exactly — the scenario **passes** (not skip, not xfail).
- **Negative control verified**: temporarily re-adding the deleted gate to
  `safety.py:is_safe` makes the Python replay **diverge** from the C golden
  (`step 3 · output · C=["The Cave Dweller's pierce decimates you.", …] py=[]` —
  the mob fails to attack). This proves the guard fails when the bug is present,
  which the v2.14.117 fixture did **not** do.
- **Guard scope (re-verified against the call path, not assumed)**: the pulse
  routes `aggr_update → multi_hit → apply_damage → engine.py:_push_message`,
  which never enters `spec_funs.py`. So this scenario locks **(1) the FIGHT-077
  fix** (a reintroduced `is_safe` level-gate — negative-control-proven above) and
  **(2) tick-time delivery of the resulting combat message to the socket** (the
  `_push_message` path), both mechanically against the immutable C trace. It does
  **not** exercise the spec-fun path, so **SPEC-017's
  `spec_funs.py:_append_message → push_message` fix is NOT guarded by this
  scenario** — reverting SPEC-017 leaves this replay green. And SPEC-017 *cannot*
  be guarded by any diff_harness scenario (the harness collapses the socket and
  mailbox channels; it is a Python-only channel-routing divergence with no ROM C
  counterpart) — its correct lock is the committed Layer-A grep-guard. See Next
  Steps item 0 for the full rationale.

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
- `pyproject.toml` — 2.14.115 → 2.14.116 (guard) → 2.14.117 (scenario plumbing)
  → 2.14.118 (scenario fixture corrected to a load-bearing FIGHT-077 guard).
- `tools/diff_harness/scenarios/aggression_onset.json` — corrected fixture
  (mob 2302 L15 / PC L1; was mob 3704 L1 / PC L5) + regenerated golden.

## Test Status

- `pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py -n0` —
  68 passed (41 scenarios incl. `aggression_onset` + unit tests).
- `tests/test_message_delivery_convention.py` — green (guard + orphan check).
- `ruff check tools/diff_harness/pyreplay.py` — clean.
- Full suite not re-run this session (changes are additive harness/test only; no
  `mud/` production code touched after v2.14.115's 5812-passing baseline).

## Next Steps

Regression-prevention trio complete (FIGHT-077 locked; SPEC-017 doc + Layer-A
guard shipped). Open follow-ups, in priority order:

0. **SPEC-017 — Layer-A is the correct lock; a diff_harness C-oracle is
   infeasible (evaluated and rejected).** A spec-fun scenario was considered and
   does **not** work: the harness runs a disconnected test char with no event
   loop, so `push_message` (fixed) falls back to the *same* `char.messages`
   mailbox the bug (`messages.append`) wrote to (`messaging.py:56-58`), and
   `pyreplay.py:51-52` drains that mailbox into the snapshot — so both paths
   produce a byte-identical trace (green-regardless, non-load-bearing). Deeper,
   SPEC-017 is a **Python-only channel-routing divergence** (async socket vs
   mailbox) with **no ROM C counterpart** — ROM has a single
   `write_to_buffer → socket` channel, so there is nothing to diff. SPEC-017's
   correct verification layer is its committed **Layer-A grep-guard** + the
   AGENTS.md doc rule (which it has). A Python-vs-Python delivery test would need
   harness surgery (simulate a connected PC; capture the socket channel apart
   from the mailbox) for marginal gain — deferred as a harness limitation, not an
   owed parity guard. (Harness-blindness to channel routing is a concrete
   instance of guardrail 3: the diff harness is enumeration-independent only for
   behavior it can *observe*, and it collapses delivery channels.)
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
