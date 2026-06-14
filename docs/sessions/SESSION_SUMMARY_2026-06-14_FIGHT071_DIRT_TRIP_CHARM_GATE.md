# Session Summary — 2026-06-14 — fight.c dirt/trip charm gate (FIGHT-071)

## Scope

Continued the cross-file / category-error / borrowed-gate divergence sweep in
the `fight.c` offensive-skill **entry gates**, picking up directly from FIGHT-069
(`do_dirt`/`do_trip` kill-steal gate, closed last unit). FIGHT-071 was filed
there as the natural follow-up: the same two commands route their charmed-
attacker-vs-master check through `_kill_safety_message` — `do_kill`'s is_safe
composite — which emits do_kill's charm string in do_kill's position, not the
per-command string/position ROM uses. This session closed that charm slice.

Method: read both ROM functions top-to-bottom again (`src/fight.c:2489-2548`
do_dirt charm path, `:2641-2709` do_trip charm path) plus `_kill_safety_message`
and `do_kill` → prove the charm gate is a *per-command* gate (different message
and position in each verb), not a member of the shared is_safe composite → three
test assertions (one red per divergence), then the fix.

## Outcomes

### `FIGHT-071` — ✅ FIXED (v2.14.102)

- **Python**: `mud/commands/combat.py:_kill_safety_message`, `do_dirt`, `do_trip`
- **ROM C**: `src/fight.c:2544-2548` (do_dirt charm), `:2705-2709` (do_trip charm)
- **Gap**: `do_dirt`/`do_trip` routed their charmed-attacker check through
  `_kill_safety_message`, which always returned do_kill's
  `act("$N is your beloved master.")` at the **top** of the helper (before the
  is_safe body). Two divergences:
  1. **Wrong message** — ROM `do_dirt` charm is
     `act("But $N is such a good friend!")`; the helper emitted "beloved master".
  2. **Wrong order** — the helper checks charm before its is_safe body, and the
     whole call runs before `do_trip`'s flying/position/`victim==ch` checks; ROM
     `do_trip` checks charm **last** (after flying/position/self), so a charmed PC
     tripping a *flying* master should hear the flying line, not the charm line.
- **Root cause (borrowed-gate shape)**: ROM's `is_safe()` contains **no** charm
  check — each offensive verb (`do_kill`/`do_dirt`/`do_trip`/`do_bash`) appends
  its own charm gate with its own string and position. Python collapsed do_kill's
  charm into the shared helper, so `do_dirt`/`do_trip` inherited do_kill's wording
  and placement.
- **Fix (2.14.102)**: added `include_charm: bool = True` to
  `_kill_safety_message` (do_kill keeps the default → **byte-identical**, verified
  LOW impact). `do_dirt`/`do_trip` now call it with `include_charm=False` and
  carry their own charm gate: `do_dirt` after the FIGHT-069 kill-steal block
  (`"But $N is such a good friend!"`), `do_trip` after the `victim==ch` check
  (`"$N is your beloved master."`) — so the flying/position/self lines fire first.
  Mirrors the FIGHT-067 `do_bash` per-command-gate pattern.
- **Tests**: 3 new — `tests/integration/test_fight071_dirt_trip_charm_gate.py`
  (do_dirt good-friend message; do_trip flying-before-charm **order** via a
  charmed PC tripping a flying NPC master; do_trip beloved-master message). The
  first two verified **red** (both returned "… beloved master." / charm-before-
  flying) before the fix; the third was a green guard that the message stays
  correct after moving the gate. All **green** after.

## Out-of-scope divergences filed (FIGHT_C_AUDIT.md, 🔄 OPEN)

Found while reading ROM `do_dirt`/`do_kill` for this gap — filed durably per the
AGENTS.md out-of-scope routing (local divergences → `<FILE>_C_AUDIT.md`):

- **`FIGHT-072`** — `do_dirt` checks `victim == ch` before `AFF_BLIND`
  (`src/fight.c:2522-2532` has BLIND first). Sibling of FIGHT-068. MINOR
  (self-dirt-kick while blind).
- **`FIGHT-073`** — `do_dirt` BLIND message is literal `"They're already
  blinded."` vs ROM `act("$E's already been blinded.")` (`:2524`). act()-render
  class (cf. TRIP-001/FIGHT-064). MINOR.
- **`FIGHT-074`** — `do_kill`'s charm "beloved master" (via the default
  `include_charm=True`) is still checked **before** is_safe body + kill-steal;
  ROM order is is_safe → kill-steal → charm. do_dirt/do_trip are now correct;
  do_kill is the remaining member on the bundled (mis-ordered) charm. MINOR.

## Files Modified

- `mud/commands/combat.py` — `_kill_safety_message` gained `include_charm`;
  `do_dirt`/`do_trip` pass `include_charm=False` + carry their own charm gate.
- `tests/integration/test_fight071_dirt_trip_charm_gate.py` — new (3 tests).
- `docs/parity/FIGHT_C_AUDIT.md` — flipped FIGHT-071 → ✅ FIXED; filed
  FIGHT-072 / FIGHT-073 / FIGHT-074.
- `CHANGELOG.md` — added the 2.14.102 (FIGHT-071) section.
- `pyproject.toml` — 2.14.101 → 2.14.102.

## Test Status

- `pytest -n0 tests/integration/test_fight071_dirt_trip_charm_gate.py` — 3/3.
- `pytest tests/integration/ -k "bash or fight or dirt or trip or kill"` —
  291 passed, 1 skipped.
- `ruff check .` — clean. Pre-commit hooks (ruff, equipment-key, attribute) all
  passed.
- GitNexus `detect_changes` — scope confined to `_kill_safety_message` + `do_dirt`
  + `do_trip` + the audit doc, 0 affected processes, LOW risk. Reindexed
  post-commit.

## Next Steps

The charm-gate slice is closed for `do_dirt`/`do_trip`. Natural continuations in
`docs/parity/FIGHT_C_AUDIT.md`:

- **`FIGHT-074`** — bring `do_kill` onto the same charm-last ordering (move the
  charm check in `_kill_safety_message` after the is_safe body and have `do_kill`
  apply charm after its kill-steal gate). Completes the kill/dirt/trip charm-order
  trio.
- **`FIGHT-070`** — extract a shared message-emitting `is_safe` so the entry gates
  surface ROM's context lines ("Not in this room.", shopkeeper, pet, …) instead
  of silently swallowing them. Structural; affects every bool-`is_safe` entry gate.
- **`FIGHT-072` / `FIGHT-073`** — do_dirt BLIND order swap + `$E` pronoun message
  (small, MINOR, act()-render class). **`FIGHT-068`** — analogous do_bash
  `victim==ch`/position order swap.

Beyond the fight.c offensive-skill family, per
`docs/parity/DIVERGENCE_CLASS_ROSTER.md` the higher-yield open lever remains the
**Hypothesis state-machine → diff_harness widening** (Class 11 / Phase C) —
enumeration-independent (guardrail 3), where most recent FINDING-0xx originated.
