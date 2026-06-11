# Session Summary — 2026-06-10 — FIGHT-052 _kill_safety_message NPC guard ordering

## Scope

Continuation from v2.13.97 (FIGHT-051 closed). Active pass: cross-file invariants.
Also probed the INV-044 candidate (`stop_fighting` both-sides invariant) — confirmed it is
already ✅ ENFORCED as INV-006 with full tests in
`tests/integration/test_inv006_fighting_pointer_coherence.py`. Session closed FIGHT-052 instead:
`_kill_safety_message` in `mud/commands/combat.py` had its NPC-attacker-vs-PC guards in the
wrong order vs ROM `is_safe` (charmed-mob check before safe-room, ROM has safe-room first).

## Outcomes

### INV-044 probe — `stop_fighting` both-sides invariant — ALREADY ENFORCED (INV-006)

GitNexus surfaced `tests/integration/test_inv006_fighting_pointer_coherence.py` during the
probe. INV-006 (FIGHTING-POINTER-COHERENCE) is ✅ ENFORCED with tests covering:
- `test_stop_fighting_both_clears_all_attackers`
- `test_stop_fighting_both_false_only_clears_self`
- `test_stop_fighting_npc_with_negative_hp_ends_at_dead_not_default_pos`

No new invariant needed. INV-044 slot remains free.

### FIGHT-052 `_kill_safety_message` NPC-attacker guard ordering — ✅ FIXED (2.13.98)

- **Python**: `mud/commands/combat.py:_kill_safety_message`
- **ROM C**: `src/fight.c:1083-1093`
- **Gap**: In the `if IS_NPC(ch)` branch, ROM checks safe-room (`:1083`) BEFORE the
  charmed-mob guard (`:1087`). `_kill_safety_message` had the order inverted — charmed-mob
  first, safe-room second. Corner case: charmed NPC in a safe room attacking a PC whose master
  is not fighting that PC → ROM returns "Not in this room."; Python returned
  "Players are your friends!" (wrong message). Attack was blocked either way, but the message
  was wrong.
- **Fix**: Swapped the two checks in the `if getattr(attacker, "is_npc", False)` branch —
  safe-room moved before charmed-mob, with ROM citation comments on both lines.
- **Impact analysis**: HIGH blast radius (3 direct callers: `do_kill`, `do_dirt`, `do_trip`).
  Change is a pure reorder of two existing checks — no behavior added or removed except in the
  corner case. `gitnexus_detect_changes` confirmed LOW risk after fix.
- **Tests**: `tests/integration/test_fight052_kill_safety_npc_guard_order.py` — **1/1 passing**
  - `test_fight052_charmed_npc_in_safe_room_returns_safe_room_message` — confirmed wrong message
    before fix, correct message after.

## Files Modified

- `mud/commands/combat.py` — FIGHT-052: swapped safe-room / charmed-mob guard order in
  `_kill_safety_message` NPC-attacker branch
- `tests/integration/test_fight052_kill_safety_npc_guard_order.py` — new file, 1 test
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-052 filed and flipped ✅ FIXED (2.13.98)
- `CHANGELOG.md` — `[2.13.98]` Fixed entry for FIGHT-052
- `pyproject.toml` — 2.13.97 → 2.13.98

## Test Status

- `pytest tests/integration/test_fight052_kill_safety_npc_guard_order.py -v` — **1/1 passing**
- `pytest tests/integration/test_fight04*.py tests/integration/test_fight05*.py` — **41/41 passing**
- Full suite: not re-run this session

## Next Steps

Cross-file invariants pass continues. Next free INV ID: **INV-044** (still free).

1. **Probe `do_flee` / `do_recall` stop-fighting contract** — both call `stop_fighting(ch, True)`
   after the action. Check ROM C `do_flee` (`:3094-3095`) and `do_recall` (`:1699`) to confirm
   the Python calls match (both=True vs both=False) and the position after stop-fighting is
   correct.

2. **FIGHT-053 candidate** — `_murder_safety_check` in `murder.py` does NOT check safe-room
   for the victim-is-PC path (PC-vs-PC clan/level block). ROM `do_murder` calls `is_safe`
   which checks safe-room at the top level (before the victim-is-PC branch). The safe-room
   check in `_murder_safety_check` is only in the room-is-None guard. Verify: can a clanmed PC
   murder another clanmed PC in a safe room via `do_murder`? Quick read of the code confirms
   `_murder_safety_check` has a ROOM_SAFE check (line 116), so this may already be covered.
   Confirm before filing.

3. **Divergence class sweep** — consider running `/rom-divergence-sweep` to check the current
   state of the DIVERGENCE_CLASS_ROSTER.md and see if any classes have moved from open to close.
