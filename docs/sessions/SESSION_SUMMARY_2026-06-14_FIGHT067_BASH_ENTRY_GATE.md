# Session Summary — 2026-06-14 — fight.c bash entry-gate (FIGHT-067)

## Scope

Continued the cross-file / category-error / borrowed-gate divergence sweep
(per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows). The act_obj.c
verb family was exhausted last session (GIVE-003 + RECITE-006 closed,
brandish/zap clean), so this session carried the "first failing gate selects the
player-facing message" lens into the `fight.c` **offensive-skill entry gates** —
specifically `do_bash`, where ROM front-loads an `is_safe` / kill-steal /
charm-friend block that Python omitted.

Method: read the ROM C gate sequence top-to-bottom (`src/fight.c:2359-2419`) →
diff against the Python early-returns for *presence, order, and message* → one
failing test, then the fix.

## Outcomes

### `FIGHT-067` — ✅ FIXED (v2.14.100)

- **Python**: `mud/commands/combat.py:do_bash` (~`:440-443`)
- **ROM C**: `src/fight.c:2405-2419` (do_bash entry gates), `:1018-1124` (is_safe)
- **Gap**: `do_bash` was missing ROM's entire entry-level offensive-target gate
  block — `is_safe(ch,victim)` (`:2405`), kill-steal (`:2408-2413`), and
  charm-friend (`:2415-2419`) — all checked at command entry **before** computing
  chance, applying WAIT_STATE, dazing the victim, or knocking them to RESTING.
- **Confirmed observable**: in a ROOM_SAFE room, forcing the success roll, Python
  still applied 24-pulse attacker WAIT_STATE, set victim `daze`, knocked the
  victim to RESTING, and broadcast "sends you sprawling". Only the HP damage was
  suppressed — downstream and silently — by `apply_damage`'s `is_safe` re-check
  (FIGHT-002, `engine.py:671-678`). A real griefing divergence: a player could
  lag + floor another character in a safe room / town square.
- **Fix**: inserted the ROM gate block after the position check / before the wait
  check in `do_bash`: `is_safe(char, victim)` → `return ""` (silent, consistent
  with FIGHT-002's downstream re-check — the canonical bool `is_safe` emits no
  message); kill-steal → `"Kill stealing is not permitted."`; charm-friend →
  `act_format("But $N is your friend!", recipient=char, actor=char, arg2=victim)`
  (`$N` PERS render, FIGHT-064 precedent). Each line cites the ROM C source.
- **Tests**: 1 new —
  `tests/integration/test_fight067_bash_safe_room_entry_gate.py`
  (ROOM_SAFE + forced success → asserts no attacker lag, no victim daze, no
  knockdown). Verified **red** before the fix (`assert 24 == 0` — WAIT_STATE
  applied in a safe room), **green** after. The 179 bash/fight integration tests
  stayed green.

### Follow-ups filed (not closed) — `docs/parity/FIGHT_C_AUDIT.md`

- **`FIGHT-068`** 🔄 — `do_bash` checks `victim == ch` before
  `position < POS_FIGHTING`, reversing ROM's order (`src/fight.c:2392` precedes
  `:2399`). Observable only when self-bashing while sitting/sleeping: ROM emits
  the "let … get back up first" line, Python emits "bash your brains out". MINOR.
- **`FIGHT-069`** 🔄 — `do_trip` / `do_dirt` entry-level `is_safe` / kill-steal /
  charm gates unverified vs the `do_bash` block just fixed. Likely the same FIGHT-067
  divergence shape; needs the same top-to-bottom gate diff.
- **`FIGHT-070`** 🔄 — FIGHT-067's `is_safe → return ""` is behavior-faithful on
  the lag/daze/knockdown axis but drops ROM's player-facing context message
  ("Not in this room.", shopkeeper, pet, …) because the canonical bool `is_safe`
  emits nothing. Needs a shared message-emitting is_safe (ROM's lines, *no*
  command-specific extras — `_kill_safety_message` bundles do_kill's "beloved
  master" gate, so it is not a drop-in). Affects every entry-gate using bool
  `is_safe`.

## Files Modified

- `mud/commands/combat.py` — added the FIGHT-067 entry-gate block to `do_bash`.
- `tests/integration/test_fight067_bash_safe_room_entry_gate.py` — new test.
- `docs/parity/FIGHT_C_AUDIT.md` — added FIGHT-067 ✅ FIXED row; filed
  FIGHT-068 / FIGHT-069 / FIGHT-070 follow-ups.
- `CHANGELOG.md` — added the 2.14.100 (FIGHT-067) section.
- `pyproject.toml` — 2.14.99 → 2.14.100.

## Test Status

- `pytest -n0 tests/integration/test_fight067_bash_safe_room_entry_gate.py` — 1/1.
- `pytest tests/integration/ -k "bash or fight"` — 179/179.
- Full suite: **5789 passed, 4 skipped** (was 5788; +1 FIGHT-067 test).
- `ruff check .` — clean.
- GitNexus `detect_changes` — scope confined to `do_bash` + the audit doc, 0
  affected processes, LOW risk. Reindexed post-commit.

## Next Steps

The `do_bash` entry gate is closed; the natural continuation is **FIGHT-069**
(apply the identical entry-gate diff to `do_trip` / `do_dirt`, which almost
certainly share the FIGHT-067 omission) and **FIGHT-070** (extract a shared
message-emitting `is_safe` so the offensive-skill entry gates surface ROM's
context lines instead of silently swallowing them). Both are in
`docs/parity/FIGHT_C_AUDIT.md`. Beyond the fight.c offensive-skill family, per
`docs/parity/DIVERGENCE_CLASS_ROSTER.md` the higher-yield open lever remains the
**Hypothesis state-machine → diff_harness widening** (Class 11 / Phase C) —
enumeration-independent (guardrail 3), where most recent FINDING-0xx originated.
