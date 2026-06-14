# Session Summary — 2026-06-14 — fight.c dirt/trip kill-steal gate (FIGHT-069)

## Scope

Continued the cross-file / category-error / borrowed-gate divergence sweep into
the `fight.c` offensive-skill **entry gates**, picking up directly from FIGHT-067
(`do_bash` entry-gate block, closed last unit). FIGHT-069 was filed there as the
natural follow-up: verify `do_dirt` / `do_trip` against the same ROM entry-gate
sequence. This session closed the kill-steal slice of that follow-up.

Method: read both ROM functions top-to-bottom (`src/fight.c:2489-2639` do_dirt,
`:2641-2754` do_trip) plus `_kill_safety_message` and `do_kill` → prove the
kill-steal gate lives **outside** the `is_safe` composite → one failing test,
then the fix.

## Outcomes

### `FIGHT-069` — ✅ FIXED (v2.14.101)

- **Python**: `mud/commands/combat.py:do_dirt`, `do_trip`
- **ROM C**: `src/fight.c:2537-2542` (do_dirt kill-steal), `:2678-2683`
  (do_trip kill-steal)
- **Gap**: both `do_dirt` and `do_trip` rejected a kill-steal in ROM —
  `IS_NPC(victim) && victim->fighting != NULL && !is_same_group(ch, victim->fighting)`
  → `"Kill stealing is not permitted."` — but Python only called
  `_kill_safety_message(ch, victim)`, which is `do_kill`'s **is_safe composite**.
  That helper bundles the is_safe messages + the charm "beloved master" gate, but
  **not** the kill-steal check — `do_kill` re-adds kill-steal *separately* at
  `combat.py:141`. `do_dirt` / `do_trip` inherited the helper's omission, so a
  player could dirt-kick or trip a mob a third party was already fighting and
  steal the kill — a real griefing divergence the borrowed gate silently allowed.
- **Root cause (borrowed-gate shape)**: the kill-steal gate is a sibling of, not
  a member of, the is_safe composite. `do_kill` knows this and re-adds it;
  `do_dirt` / `do_trip` borrowed only the composite and never re-added the
  sibling.
- **Fix**: added the kill-steal block to each function immediately after the
  `_kill_safety_message` call, matching ROM's gate position (between is_safe and
  the charm/flying/position checks). Each cites the ROM C source and the
  `combat.py:141` precedent for why it sits outside the helper.
- **Tests**: 1 new — `tests/integration/test_fight069_dirt_trip_kill_steal_gate.py`
  (NPC victim already `fighting` an ungrouped third party → both `do_dirt` and
  `do_trip` must return `"Kill stealing is not permitted."`). Verified **red**
  before the fix (`do_trip` returned `"You trip Mark and they go down!"`),
  **green** after.

### Follow-ups still open — `docs/parity/FIGHT_C_AUDIT.md`

- **`FIGHT-068`** 🔄 — `do_bash` `victim == ch` / `position < POS_FIGHTING`
  order swap (self-bash while sitting). MINOR.
- **`FIGHT-070`** 🔄 — bool `is_safe → return ""` swallows ROM's player-facing
  context message ("Not in this room.", shopkeeper, pet, …). Needs a shared
  message-emitting is_safe; affects every entry gate using bool `is_safe`.
- **`FIGHT-071`** 🔄 — `do_dirt` / `do_trip` charm-friend message + gate **order**
  still diverge: ROM's charm lines are `"$N is such a good friend!"` (do_dirt) and
  `"$N is your beloved master."` (do_trip), at different positions than do_kill's
  `_kill_safety_message` "beloved master" line, which is what the helper currently
  emits for all three. FIGHT-069 fixed only the kill-steal omission, not the charm
  message/order divergence the shared helper introduces.

## Files Modified

- `mud/commands/combat.py` — added the FIGHT-069 kill-steal gate to `do_dirt`
  and `do_trip`.
- `tests/integration/test_fight069_dirt_trip_kill_steal_gate.py` — new test.
- `docs/parity/FIGHT_C_AUDIT.md` — flipped FIGHT-069 → ✅ FIXED; filed FIGHT-071
  follow-up.
- `CHANGELOG.md` — added the 2.14.101 (FIGHT-069) section.
- `pyproject.toml` — 2.14.100 → 2.14.101.

## Test Status

- `pytest -n0 tests/integration/test_fight069_dirt_trip_kill_steal_gate.py` — 2/2.
- `pytest tests/integration/ -k "bash or fight or dirt or trip"` — 226/226.
- Full suite: **5791 passed, 4 skipped** (was 5789; +2 FIGHT-069 tests).
- `ruff check .` — clean.
- GitNexus `detect_changes` — scope confined to `do_dirt` + `do_trip` + the audit
  doc, 0 affected processes, LOW risk. Reindexed post-commit.

## Next Steps

The kill-steal omission is closed across the bash/dirt/trip family. The natural
continuation is **FIGHT-071** (reconcile the `do_dirt` / `do_trip` charm-friend
message + gate order against ROM — the shared `_kill_safety_message` helper emits
`do_kill`'s "beloved master" line where ROM wants per-command charm strings at
different positions) and **FIGHT-070** (extract a shared message-emitting
`is_safe` so the offensive-skill entry gates surface ROM's context lines instead
of silently swallowing them). Both are in `docs/parity/FIGHT_C_AUDIT.md`. Beyond
the fight.c offensive-skill family, per `docs/parity/DIVERGENCE_CLASS_ROSTER.md`
the higher-yield open lever remains the **Hypothesis state-machine → diff_harness
widening** (Class 11 / Phase C) — enumeration-independent (guardrail 3), where
most recent FINDING-0xx originated.
