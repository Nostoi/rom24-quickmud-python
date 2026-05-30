# Session Summary — 2026-05-30 — ACT-CAP-001 broadcast_room (INV-029 room-broadcast cousin CLOSED)

## Scope

Continuation of the same day's FIGHT-031 work, picking up **Next Task #1** from
`SESSION_STATUS.md`: close the remaining ACT-CAP-001 chokepoint —
`mud/net/protocol.py:broadcast_room`, the Python `act(TO_ROOM)` delivery
boundary for ~64 command/skill/movement callers, which delivered its baked
string verbatim (uncapped). ROM `act_new` (`src/comm.c:2376-2379`) caps the
first visible char of every `act()` line.

One code commit landed: `4bc1acf4` (`fix(parity)`, 2.11.40). The handoff-docs
commit (this summary + `SESSION_STATUS.md` + README refresh) is separate.

## Outcomes

### `ACT-CAP-001` (broadcast_room half) — ✅ FIXED (2.11.40, `4bc1acf4`)

- **ROM C**: `src/comm.c:2376-2379` (`act_new` cap) applied to the
  `act(..., TO_ROOM)` lines that route through `broadcast_room` — movement
  (`src/act_move.c:197,384`), doors, wear/drop/get, spell room broadcasts, etc.
- **Python**: `mud/net/protocol.py:broadcast_room` — cap the message **once at
  function entry** via the shared `mud/utils/act.py:capitalize_act_line`.
  `broadcast_room` is a *terminal* delivery primitive (its argument IS the
  delivered line, one baked string for all recipients), so the cap is applied
  once, not per-recipient (unlike `_broadcast_pos_change`'s PERS render).
  Idempotent on already-capped callers.
- **Scope discipline** (advisor-confirmed): `broadcast_global` is **NOT** capped
  — it is mixed (channels are `act()`, but ROM weather is `send_to_char`,
  `src/update.c weather_update`); a blanket cap there would wrongly cap weather.
  Two parallel helpers were checked: `spec_funs.py:_broadcast_room` already caps
  (it routes through `act_format`); `ai/__init__.py:_broadcast_room` is dead code.
- **Safety**: `gitnexus_impact(broadcast_room)` = **CRITICAL** (64 direct
  callers, **0 affected processes**) — expected, the deliberate render-behaviour
  change identical to INV-029/FIGHT-031; the blast radius is a test sweep.
  `gitnexus_detect_changes` = **low**, 0 processes, scope = `broadcast_room` +
  swept tests + docs.
- **Tests**: `tests/integration/test_act_cap_001_broadcast_room.py` (3) — plain
  line + `{`-kludge + already-capital no-op, asserting the cap *property* not the
  rendered name (`broadcast_room` does no PERS masking — a separate
  INV-027-family divergence). Verified RED-first (2 fail, the no-op passes),
  then GREEN.

### Full-suite sweep (9 stale lowercase room-leg asserts → ROM-correct caps)

Each verified individually as a sentence-start cap (object/NPC short_descr leads
the `act(TO_ROOM)` line), not a logic regression:

- `tests/test_skills_buffs.py` (3): invis `"mysterious gem fades out of sight."`
  ×2 + fireproof `"ancient scroll is surrounded by a protective aura."` → capped.
- `tests/test_skills_debuffs.py` (2): poison `"serrated dagger is coated with
  deadly venom."` + `"loaf of bread is infused with poisonous vapors."` → capped.
- `tests/test_skills_transport.py` (2): portal + nexus `"a shimmering portal
  rises up from the ground."` → capped.
- `tests/test_skills_healing.py` (1): remove_curse `"cursed sword glows blue."` → capped.
- `tests/integration/test_healer_command_parity.py` (1): NPC healer `"a healer
  utters the words 'energizer'."` → capped.

**Per-failure judgment caught a false re-baseline** (advisor's "no bulk-sed"
discipline): the invis *wear-off* reappear line `"mysterious gem fades into
view."` is broadcast by `game_loop._broadcast_object_wear_off` via
`_message_room` (NOT `broadcast_room`), so it stays **lowercase** — reverted
that one assertion and filed `_message_room` under ACT-CAP-002.

**The TO_ALL caster/witness split**: object spells (invis/poison/remove_curse/
portal/nexus) mirror ROM `act("$p …", ch, obj, NULL, TO_ALL)` — which caps for
*everyone* — but the Python handlers split it into `_send_to_char(caster,
message)` (uncapped) + `broadcast_room(room, message, exclude=caster)` (now
capped). So the re-baselined tests assert **caster-lowercase / witness-
capitalized** per spell, with comments pointing at ACT-CAP-002.

## Out-of-scope divergence surfaced + filed durably

- **`ACT-CAP-002`** (🔄 OPEN, `docs/parity/FIGHT_C_AUDIT.md`) — three parallel
  uncapped room-broadcast siblings: (a) `mud/models/room.py:Room.broadcast`
  (~20 callers — death lines, "$n is zapped", mob actions, practice/level,
  reconnect/link-lost), (b) `mud/game_loop.py:_message_room` (object wear-off),
  (c) the **TO_ALL caster legs** `_send_to_char(caster, message)` in the
  object-spell handlers; plus (d) dead `ai/__init__.py:_broadcast_room`.

## Files Modified

Code commit `4bc1acf4` (11 files):

- `mud/net/protocol.py` — `broadcast_room` caps the message at entry; top-level
  `capitalize_act_line` import.
- `tests/integration/test_act_cap_001_broadcast_room.py` — NEW, 3 tests.
- `tests/test_skills_buffs.py`, `tests/test_skills_debuffs.py`,
  `tests/test_skills_transport.py`, `tests/test_skills_healing.py`,
  `tests/integration/test_healer_command_parity.py` — 9-assertion sweep + comments.
- `docs/parity/FIGHT_C_AUDIT.md` — ACT-CAP-001 → broadcast_room CLOSED;
  ACT-CAP-002 filed.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-029 row: chokepoint (d)
  broadcast_room added, cousins refreshed (broadcast_global deferred, ACT-CAP-002).
- `CHANGELOG.md` — 2.11.40 section.
- `pyproject.toml` — 2.11.39 → 2.11.40.

Handoff commit (separate): this summary, `SESSION_STATUS.md`, `README.md`
badge/metric refresh (version 2.11.40, tests 5010).

## Test Status

- `tests/integration/test_act_cap_001_broadcast_room.py` — 3/3 passing.
- Full suite — **5010 passed, 4 skipped, 0 failed** (parallel; 5007 baseline + 3
  new tests; the 9 swept assertions stayed at parity count).
- `ruff check` on changed files — the only flags are **pre-existing** (UP038 in
  `send_to_char`, B009 `getattr` in debuffs, I001 imports in transport) on lines
  not touched here; the repo carries ~1828 pre-existing ruff findings. My new
  import passes I001. Left pre-existing lint as-is (INV-029/FIGHT-031 precedent).

## Next Steps

Cross-file invariants remains the standing pass. Concrete next options:

1. **`ACT-CAP-002`** — the parallel room-broadcast primitives (`Room.broadcast`,
   `_message_room`) + the TO_ALL caster legs. `Room.broadcast` is the
   highest-value (most callers); cap at its entry like `broadcast_room`, plus
   cap the shared `message` at each object-spell handler's build site so the
   caster leg matches ROM `act(TO_ALL)`. Re-baseline the caster-side asserts the
   ACT-CAP-001 sweep left lowercase.
2. **`do_say` / `do_tell`** (`mud/commands/communication.py`) — the remaining
   INV-029 cousin (`test_tell_parity.py:19` notes the cap as a known deferral).
3. **`broadcast_global`** — per-channel cap (NOT a blanket chokepoint; weather is
   `send_to_char`).
4. **`FIGHT-032`/`033`/`034`** — combat PERS / FROST-SHOCKING `$p` / auto-split.
5. **`VISION-002`** — dark-gate same-room divergence. Larger scope; failing test first.

## Outstanding / carried-open

- **ACT-CAP-002** (OPEN) — `Room.broadcast` / `_message_room` / TO_ALL caster legs.
- **INV-029 cousins** (OPEN): `do_say`/`do_tell`, `broadcast_global` (mixed),
  wiznet `WIZ_PREFIX`.
- **`FIGHT-032`/`033`/`034`** (OPEN) — combat cousins from the FIGHT-031 session.
- **`VISION-002`** (OPEN) — dark-gate same-room divergence.
- Known **xdist flakes**: `test_combat_death.py`,
  `test_backstab_uses_position_and_weapon` (pass in isolation; this session's
  full runs had 0 failures).
- pet-shop haggle / "now follows you" wrong-channel (INV-001 family);
  `Character.pet` stale type annotation; `do_cast` object-targeting legs.

## Commit / push state

- This session (ACT-CAP-001 leg): `4bc1acf4` (code) + the upcoming handoff-docs
  commit. Earlier today: `1b69e449` (FIGHT-031 code) + `7151e2fd` (FIGHT-031 handoff).
- **Local-only, NOT pushed** — await the user's say-so before pushing to
  `origin/master`.
- One unrelated pre-existing working-tree change left unstaged:
  `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` (present at session start).
