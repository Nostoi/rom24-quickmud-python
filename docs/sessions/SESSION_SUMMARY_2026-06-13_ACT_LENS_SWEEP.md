# Session Summary — 2026-06-13 — act()/PERS-rendering lens sweep (MAGIC-025..044, FIGHT-065/066, MOBCMD-020/021)

## Scope

Continuation of the autonomous ROM-parity loop. Picked up mid-MAGIC-025 and ran the
**act()-rendering lens** — find any TO_CHAR/TO_ROOM/TO_VICT message that bakes a
keyword `name` / `victim.name` / lowercase `short_descr` / literal pronoun instead
of routing through ROM's `act()` (`$n`/`$N`/`$p`/`$S`/`$e`/`$E` codes, per-recipient
PERS masking, buf[0] capitalization) — systematically across **spell handlers →
combat → commands → mob_cmds**, plus two spurious-output cases and a
position-transition verification pass.

Shipped **24 ROM-parity gaps**, each via failing-test-first → fix → green → audit
row flip → CHANGELOG → version bump → commit → push → reindex. Suite grew 5733 →
5778 passing; version 2.14.68 → 2.14.92.

## Outcomes

### Spell handlers — `mud/skills/handlers.py` (MAGIC-025..044)

`$N`/`$n` PERS conversions (NPC short_descr capitalized, invisible→"someone"):
fly/infravision/pass_door (025), protection siblings already done, slow/stone_skin
(031), sanctuary (032), detect_evil/good/hidden/invis/magic (034),
curse/dispel_evil/good TO_CHAR (035), plague (028), giant_strength/haste,
charm_person `$n`+`$N` (039).

`$p` object-name capitalization: bless-obj/continual_light/fireproof/poison-weapon
(026), envenom-skill dict-return (029).

TO_ROOM / actor-topology + `$S` possessive: dispel TO_ROOM "protected by $S evil"
with actor-exclusion (036), demonfire "demons of Hell" TO_ROOM-includes-victim
(037/038), cure_blindness/cure_poison (040), chill_touch (041), faerie_fog reveal
(042), envenom room broadcasts (043), blindness room broadcast (044).

**Spurious-output (ROM is silent — removed invented Python lines):** faerie_fire
duplicate (027), sleep reject gates (030).

**know_alignment (033):** rewrote to ROM's single `act("$N …")` (7 alignment tiers),
removed the invented "You …" self-variant, preserved ROM's literal "evil!." typo.

**MAGIC-022 enumerated baked-name batch FULLY CLOSED** (023..029 + FIGHT-065).

### Combat — `mud/combat/engine.py`

- **FIGHT-065** — `disarm` skill-handler "no weapon" → ROM literal "Your opponent is
  not wielding a weapon." (not a `$N` bake).
- **FIGHT-066** — `attack_round` parry/dodge/shield-block defense-return strings →
  `pers()`+cap (was a latent baked `victim.name`; all `multi_hit` callers discard
  the return and the real player line is already pushed correctly inside
  check_parry/dodge/shield_block — FIGHT-031/032 — so it was never delivered).

### Mob programs — `mud/mob_cmds.py`

- **MOBCMD-020** — `do_mpechoaround`/`do_mpechoat` cap buf[0] (ROM `act()` TO_NOTVICT/
  TO_VICT).
- **MOBCMD-021** — `do_mpasound` caps buf[0] (ROM `act()` per adjacent room).
- All four ROM `act()` sites in `mob_cmds.c` now covered (mpecho already correct via
  `room.broadcast`; mpgecho/mpzecho correctly uncapped — ROM uses raw `send_to_char`).

## Verification findings (no code change — recorded to steer future work)

- **act()-lens vein EXHAUSTED** across spell handlers, combat, commands, mob_cmds —
  fresh greps for baked-name broadcast patterns return empty.
- **`colour_spray`'s colour-coded "You spray red, blue, yellow light…" messages are
  a QuickMUD enhancement with NO ROM equivalent** (`spell_colour_spray` only calls
  `damage()` + `spell_blindness`) — do NOT convert (would invent ROM behavior).
- **Position-transition messages + `update_pos` CONFIRMED ROM-faithful** — `update_pos`
  matches `fight.c:update_pos` line-for-line; the 4 position messages + HURT/BLEEDING
  default-case feedback match `damage()` `fight.c:835-869` exactly.

## Files Modified

- `mud/skills/handlers.py` — MAGIC-025..044 (act_format / act_to_room / capitalize_act_line)
- `mud/combat/engine.py` — FIGHT-066 defense-return PERS
- `mud/mob_cmds.py` — MOBCMD-020/021 buf[0] cap + `capitalize_act_line` import
- `tests/integration/test_magic025..044_*.py`, `test_fight065/066_*.py`,
  `test_mobcmd020/021_*.py` — new failing-test-first regressions
- Re-baselined: `test_skills_*.py`, `test_spell_*.py`, `test_skills_detection.py`,
  `test_utility_spells_parity.py`, `test_skills_damage.py`,
  `test_mobprog_program_flow.py` (PERS/cap/typo/topology adjustments)
- `docs/parity/MAGIC_C_AUDIT.md`, `FIGHT_C_AUDIT.md`, `MOB_CMDS_C_AUDIT.md` — gap rows
- `CHANGELOG.md`, `pyproject.toml` (2.14.68→2.14.92), `docs/sessions/SESSION_STATUS.md`

## Test Status

- Full suite: **5778 passed / 4 skipped** (v2.14.92).
- Each gap verified RED→GREEN; full suite green after every commit.

## Next Steps

The act()/buf[0]-cap divergence class is comprehensively swept. Next veins (see
SESSION_STATUS "Next Intended Task"):
1. **Mob memory / hunt** — `src/fight.c` ATTACK_BACK + hunt/track loop vs the Python
   AI tick (not yet probed).
2. **act()-lens in remaining command render paths** — info/look/who/score (display
   formatting, likely not act() sites — verify).
3. Continue the cross-file invariants probe-then-scope on a fresh divergence class
   from `docs/parity/DIVERGENCE_CLASS_ROSTER.md`.
