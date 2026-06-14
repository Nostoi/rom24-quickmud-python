# Session Summary — 2026-06-14 — fight.c do_kill charm-order (FIGHT-074)

## Scope

Continued the cross-file / category-error / borrowed-gate divergence sweep in
the `fight.c` offensive-skill **entry gates**, picking up directly from FIGHT-071
(`do_dirt`/`do_trip` charm gate). FIGHT-074 was filed there as the remaining
member of the kill/dirt/trip charm-order trio: `do_kill` still routed its
charmed-attacker-vs-master check through `_kill_safety_message` with the bundled
`"$N is your beloved master."` gate checked at the **top** of the helper, before
the is_safe body and before do_kill's separate kill-steal gate. This session
closed that slice and made `_kill_safety_message` a pure ROM `is_safe()` mirror.

Method: re-read ROM `do_kill` (`src/fight.c:2758-2819`) top-to-bottom to confirm
the gate order is is_safe (2794) → kill-steal (2797) → charm (2803); confirmed
the Python helper checked charm first; wrote three test assertions (two red — one
per order discriminator — plus a green guard), verified red, then the fix.

## Outcomes

### `FIGHT-074` — ✅ FIXED (v2.14.103)

- **Python**: `mud/commands/combat.py:_kill_safety_message`, `do_kill`
  (also `do_dirt`/`do_trip` call sites)
- **ROM C**: `src/fight.c:2794-2807` (do_kill is_safe → kill-steal → charm)
- **Gap**: `do_kill` called `_kill_safety_message(char, victim)` with the default
  `include_charm=True`, so the helper emitted do_kill's
  `"$N is your beloved master."` at the **top** (before its is_safe body) and
  before do_kill's separate kill-steal gate. Two observable divergences:
  1. **Charm pre-empts is_safe** — a charmed PC targeting its master in a
     ROOM_SAFE room saw "… is your beloved master." where ROM emits
     "Not in this room." (is_safe is checked first, `:2794`).
  2. **Charm pre-empts kill-steal** — a charmed PC whose master was already
     fighting an ungrouped third party saw the charm line where ROM emits
     "Kill stealing is not permitted." (kill-steal is checked first, `:2797`).
- **Root cause (borrowed-gate shape)**: ROM's `is_safe()` contains **no** charm
  check — each offensive verb appends its own charm gate at its own position.
  Python had collapsed do_kill's charm into the shared helper (FIGHT-071 added an
  `include_charm` flag so do_dirt/do_trip could opt out, but do_kill kept the
  bundled, mis-ordered gate).
- **Fix (2.14.103, Option B — full removal)**: removed the `include_charm`
  parameter and the charm branch from `_kill_safety_message` entirely, making it
  a pure ROM `is_safe()` mirror (no charm). `do_kill` now applies its own charm
  gate **after** its kill-steal block (`src/fight.c:2803-2807`); do_dirt/do_trip
  call the helper with no kwarg and keep the trailing charm gates FIGHT-071 gave
  them. (Option B was forced, not optional: kill-steal lives in the command
  *between* is_safe and charm, so charm cannot stay in the helper and still land
  after kill-steal.) Completes the kill/dirt/trip charm-order trio.
- **Tests**: 3 new — `tests/integration/test_fight074_kill_charm_order.py`
  (charmed-master in safe room → safe line; charmed-master being kill-stolen →
  kill-steal line; charmed-master when both pass → beloved-master guard). The
  first two verified **red** (both returned "A dark wizard is your beloved
  master.") before the fix; the third was a green guard that the message survives
  moving the gate out of the helper. All **green** after.

## Files Modified

- `mud/commands/combat.py` — `_kill_safety_message` lost `include_charm` + charm
  branch (pure is_safe mirror); `do_kill` gained a trailing charm gate after
  kill-steal; `do_dirt`/`do_trip` call sites drop the `include_charm=False` kwarg.
- `tests/integration/test_fight074_kill_charm_order.py` — new (3 tests).
- `docs/parity/FIGHT_C_AUDIT.md` — flipped FIGHT-074 → ✅ FIXED.
- `CHANGELOG.md` — added the 2.14.103 (FIGHT-074) section.
- `pyproject.toml` — 2.14.102 → 2.14.103.

## Test Status

- `pytest -n0 tests/integration/test_fight074_kill_charm_order.py` — 3/3.
- `pytest -n0 .../test_fight071_dirt_trip_charm_gate.py` — 3/3 (unchanged-behavior
  guard after the call-site edits).
- `pytest tests/integration/ -k "bash or fight or dirt or trip or kill"` —
  294 passed, 1 skipped.
- `ruff check` — clean. Pre-commit hooks (ruff, equipment-key, char.inventory)
  all passed.
- GitNexus `detect_changes` — scope confined to `_kill_safety_message` + `do_kill`
  + `do_dirt` + `do_trip` + the audit doc, 0 affected processes, LOW risk.
  Reindexed post-commit.

## Outstanding (open fight.c rows — for the next agent)

- **`FIGHT-070`** — extract a shared message-emitting `is_safe` so the entry gates
  surface ROM's context lines ("Not in this room.", shopkeeper, pet, …) instead
  of silently swallowing them via the bool `is_safe`. Structural; affects every
  bool-`is_safe` entry gate (do_bash now).
- **`FIGHT-072` / `FIGHT-073`** — do_dirt `victim==ch`-before-BLIND order swap +
  BLIND `$E` pronoun message (literal "They're already blinded." vs ROM
  `act("$E's already been blinded.")`). MINOR, act()-render class.
- **`FIGHT-068`** — analogous do_bash `victim==ch`/position order swap.

## Next Steps

The charm-gate slice is now closed for the whole kill/dirt/trip trio. Natural
continuations: FIGHT-070 (shared message-emitting is_safe — the highest-leverage
structural one), then the MINOR act()-render pair FIGHT-072/073 and the FIGHT-068
order swap. Beyond the fight.c offensive-skill family, per
`docs/parity/DIVERGENCE_CLASS_ROSTER.md` the higher-yield open lever remains the
**Hypothesis state-machine → diff_harness widening** (Class 11 / Phase C),
enumeration-independent (guardrail 3).
