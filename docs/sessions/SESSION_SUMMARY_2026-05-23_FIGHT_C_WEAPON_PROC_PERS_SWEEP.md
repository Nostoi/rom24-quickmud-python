# Session Summary — 2026-05-23 — `fight.c` weapon-proc PERS sweep (FIGHT-009..013)

## Scope

Direct continuation of the earlier FIGHT-004..008 position-change
PERS sweep. Closed all five weapon special-attack TO_ROOM broadcasts
in `process_weapon_special_attacks` using the same
`_broadcast_pos_change` helper (extended to accept `**extra`
template kwargs for ROM's `$p` weapon name). Five gaps closed in
five TDD commits; one of them (FIGHT-012) carried a second
wording divergence on top of the PERS gap.

## Outcomes

### `FIGHT-009` — ✅ FIXED — WEAPON_POISON TO_ROOM PERS (2.8.61 / `59655b1`)

- **ROM C**: `src/fight.c:614-615` — `act("$n is poisoned by the venom on $p.", victim, wield, NULL, TO_ROOM)`.
- **Python**: `mud/combat/engine.py` poison branch in `process_weapon_special_attacks`.
- **Fix**: Extended `_broadcast_pos_change` to accept `**extra` template kwargs (so weapon name `$p` can substitute alongside victim PERS `$n`). Template: `"{name} is poisoned by the venom on {weapon}."`.
- **Test**: `tests/integration/test_weapon_proc_pers.py::TestWeaponProcBroadcastPers::test_fight_009_poison_broadcast_uses_pers_for_invisible_victim` (new test file).

### `FIGHT-010` — ✅ FIXED — WEAPON_VAMPIRIC TO_ROOM PERS (2.8.62 / `3dc14f9`)

- **ROM C**: `src/fight.c:643` — `act("$p draws life from $n.", victim, wield, NULL, TO_ROOM)`.
- **Fix**: Template `"{weapon} draws life from {name}."`.
- **Test**: `::test_fight_010_vampiric_broadcast_uses_pers_for_invisible_victim`.

### `FIGHT-011` — ✅ FIXED — WEAPON_FLAMING TO_ROOM PERS (2.8.63 / `22e0c43`)

- **ROM C**: `src/fight.c:654` — `act("$n is burned by $p.", victim, wield, NULL, TO_ROOM)`.
- **Fix**: Template `"{name} is burned by {weapon}."`.
- **Test**: `::test_fight_011_flaming_broadcast_uses_pers_for_invisible_victim`.

### `FIGHT-012` — ✅ FIXED — WEAPON_FROST TO_ROOM PERS + ROM-true wording (2.8.64 / `f9a566c`)

- **ROM C**: `src/fight.c:663` — `act("$p freezes $n.", victim, wield, NULL, TO_ROOM)`.
- **Fix**: Two divergences in one IMPORTANT gap. (a) PERS gap on `$n`. (b) Wording — ROM puts the weapon first (`"the sword freezes Alice."`); Python previously emitted `"Alice is frozen by the sword."` (subject/object inverted). Template `"{weapon} freezes {name}."` fixes both.
- **Test**: `::test_fight_012_frost_broadcast_uses_pers_and_rom_wording`.

### `FIGHT-013` — ✅ FIXED — WEAPON_SHOCKING TO_ROOM PERS (2.8.65 / `d93a88a`)

- **ROM C**: `src/fight.c:673-674` — `act("$n is struck by lightning from $p.", victim, wield, NULL, TO_ROOM)`.
- **Fix**: Template `"{name} is struck by lightning from {weapon}."`.
- **Test**: `::test_fight_013_shocking_broadcast_uses_pers_for_invisible_victim`. Closes the FIGHT-009..013 cluster.

## Helper evolution

`_broadcast_pos_change(victim, template, **extra)` — extended in
FIGHT-009 to accept arbitrary template kwargs. Still mirrors ROM
`act(..., TO_ROOM)` with PERS substitution on `$n`; weapon names
(ROM `$p`) pass through verbatim since they aren't `can_see`-gated.
Now used by 9 broadcast sites:

- Position-change broadcasts (FIGHT-004..008): MORTAL/INCAP/STUNNED/DEAD.
- Weapon-proc broadcasts (FIGHT-009..013): poison/vampiric/flaming/frost/shocking.

## Files Modified

- `mud/combat/engine.py` — generalized `_broadcast_pos_change` helper; refactored all 5 weapon-proc broadcasts to use it; FROST wording corrected.
- `tests/integration/test_weapon_proc_pers.py` — **new file** — 5 tests for FIGHT-009..013, with a `_setup_room_and_chars` fixture helper.
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-009..013 gap rows flipped from 🔄 OPEN to ✅ FIXED with test/commit references.
- `CHANGELOG.md` — `[2.8.61]` → `[2.8.65]` sections.
- `pyproject.toml` — 2.8.60 → 2.8.65.

## Test Status

- Targeted (`tests/integration/test_weapon_proc_pers.py`): 5/5 passing.
- Existing weapon-proc tests (`tests/test_weapon_special_attacks.py`): 12/12 passing (one previously-flaky test, `test_weapon_flaming_fire_damage`, now consistently passes — appears to have been order-sensitive; not investigating further as it's not in scope).
- Full suite at 2.8.65: **4637 passed, 4 skipped** (+5 vs 2.8.60; zero regressions).

## Commits this session

| Hash | Version | Subject |
|------|---------|---------|
| `59655b1` | 2.8.61 | fix(parity): fight.c FIGHT-009 — WEAPON_POISON broadcast routes through PERS |
| `3dc14f9` | 2.8.62 | fix(parity): fight.c FIGHT-010 — WEAPON_VAMPIRIC broadcast routes through PERS |
| `22e0c43` | 2.8.63 | fix(parity): fight.c FIGHT-011 — WEAPON_FLAMING broadcast routes through PERS |
| `f9a566c` | 2.8.64 | fix(parity): fight.c FIGHT-012 — WEAPON_FROST broadcast PERS + ROM wording |
| `d93a88a` | 2.8.65 | fix(parity): fight.c FIGHT-013 — WEAPON_SHOCKING broadcast routes through PERS |

Plus this handoff commit.

## Next Steps

Combat-message PERS surfaces now fully closed for position-change
broadcasts (FIGHT-004..008) and weapon-proc broadcasts
(FIGHT-009..013). Remaining `_broadcast_room` calls in
`mud/combat/engine.py`:

1. **Line 252** (`dam_message.messages.room`) — pre-rendered string
   from `mud/combat/messages.py:dam_message` (ROM
   `src/fight.c:2035-2233`). This is the per-hit damage-tier
   broadcast surface — hundreds of `act()` lines, the
   highest-volume PERS leak in combat. **Recommended next target**
   if continuing the combat sweep; would be a multi-session arc.
2. **Line 956** (`do_sacrifice`) — single `_broadcast_room` call
   with `expand_placeholders("$n sacrifices $N to Mota.", attacker,
   corpse)`. PERS gap on attacker. Would be a single-gap close
   (FIGHT-014). Quick warm-up.
3. **PMOTE-001** — `do_pmote` greenfield port on the `act_comm.c`
   shelf. ~50 lines of C with per-recipient second-person
   substitution + apostrophe/possessive handling.

Recommendation: take a beat and push. Then either start
`dam_message` as a fresh session (it's a large surface) or knock
off FIGHT-014 (sacrifice) as a 10-minute warm-up first.

## Operational follow-ups

- `log/orphaned_helps.txt` still tracked + drifting on every test run. Repo hygiene commit overdue.
- GitNexus index stale (last indexed `de1893f`). Re-run `npx gitnexus analyze --skip-agents-md` before the next session that needs `gitnexus_impact`.
- Local commits `59655b1..d93a88a` (5 fixes) + this handoff not pushed yet — waiting on explicit user push approval.
