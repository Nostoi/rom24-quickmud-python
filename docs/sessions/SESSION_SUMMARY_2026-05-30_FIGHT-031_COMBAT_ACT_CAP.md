# Session Summary — 2026-05-30 — FIGHT-031 Combat act() Capitalization (INV-029 combat cousin CLOSED)

## Scope

Continuation picking up **Next Task #1** from `SESSION_STATUS.md`: close the
high-traffic **combat** cousin of **INV-029** (ACT-FIRST-LETTER-CAP). ROM
`act_new` (`src/comm.c:2376-2379`) upper-cases the first visible char of *every*
rendered `act()` line. INV-029 (2.11.38) enforced this at the `act_format` +
`imm_commands` chokepoints; FIGHT-025 (2.11.14) had already capped the combat
`dam_message` render chokepoint (`render_for`).

**Key reconciliation:** the handoff named "the goblin misses you" (the
`dam_message` miss line) as the top uncapped combat path — but that path was
**already closed by FIGHT-025**. The *spirit* held (combat act() lines were
still uncapped) at two *other* render boundaries that bypass `render_for`,
which this session closed as **FIGHT-031**.

One code commit landed: `1b69e449` (`fix(parity)`, 2.11.39). The handoff-docs
commit (this summary + `SESSION_STATUS.md` + README refresh) is separate.

## Outcomes

### `FIGHT-031` — combat act() output not capitalized at the render boundaries that bypass `render_for` — ✅ FIXED (2.11.39, `1b69e449`)

- **ROM C**: `src/comm.c:2376-2379` (`act_new` cap, `{`-kludge) applied to the
  `src/fight.c` act() sites — position-change TO_ROOM (`:837-861`), weapon-special
  TO_ROOM (`:614,643,654,663,673`), defense TO_CHAR (`check_parry :1318`,
  `check_shield_block :1345`, `check_dodge :1370`), flaming victim TO_CHAR (`:655`).
- **Python**: `mud/combat/engine.py`
  - **(a) chokepoint** `_broadcast_pos_change` — caps each per-listener
    PERS-rendered line **and** the `canonical` fed to `mp_act_trigger_room` (ROM
    caps `buf` at `:2376` *before* the TRIG_ACT dispatch at `:2384`). Covers all
    4 position-change room broadcasts (mortal/incap/stunned/DEAD) + all 5
    weapon-special room broadcasts.
  - **(b) direct-f-string sites** — `check_parry`/`check_dodge`/`check_shield_block`
    attacker TO_CHAR lines (`{defender} parries/dodges/blocks your attack`) +
    the flaming victim line (`{weapon} sears your flesh.`, push + test-fallback),
    each wrapped in the shared `mud/utils/act.py:capitalize_act_line`.
- **Load-bearing parity check**: each site was verified `act()` vs `send_to_char`
  against `src/fight.c:595-682`. The **POISON victim line** (`:612`) is
  `send_to_char`, NOT `act()`, so it is correctly **left uncapped**. The
  "You…"/"The…"-led act() lines are no-ops (already capital) and left untouched.
- **Safety**: `gitnexus_impact(_broadcast_pos_change)` = **CRITICAL** (27
  impacted, 3 direct callers, **0 affected processes**) — expected, the
  deliberate render-behaviour change identical to INV-029's `act_format` impact;
  the blast radius is a test-assertion sweep. `gitnexus_detect_changes` = **low**,
  0 processes, scope confined to the combat cap sites + docs + swept tests.
- **Tests**: `tests/integration/test_fight_031_combat_act_capitalization.py` (5)
  — `_broadcast_pos_change` room line + DEAD `{R`-kludge + parry/dodge/shield-block.
  Asserts the cap **property** (`[0].isupper()` / `[2].isupper()`), **not** the
  rendered name, so the FIGHT-032 PERS fix won't break them. Verified RED-first
  (all 5 failed lowercase-led, defenses confirmed firing), then GREEN.

### Full-suite assertion sweep (3 stale lowercase asserts, all ROM-faithful caps)

- `tests/test_weapon_special_attacks.py` (2): flaming `"test weapon sears your
  flesh."` → `"Test weapon sears your flesh."`.
- `tests/integration/test_invisibility_combat.py` (1): FIGHT-007 POS_DEAD
  `"someone is DEAD!!"` → `"Someone is DEAD!!"` — the **INV-027 mask + INV-029
  cap composing** into the ROM-correct `{RSomeone is DEAD!!{x`. (The
  `test_weapon_proc_pers.py` room-broadcast asserts already `.lower()` the joined
  string, so they stayed green — genuine, not false-green.)

## Out-of-scope divergences surfaced + filed durably

All in `docs/parity/FIGHT_C_AUDIT.md` Follow-ups (per AGENTS.md routing):

- **`FIGHT-032`** (🔄 OPEN) — the defense TO_CHAR/TO_VICT lines render the
  defender/attacker name from the raw `name` field, not ROM `$N`/`$n`→PERS, so
  an NPC renders its keyword `name` (not `short_descr`) and an invisible
  combatant is not masked to "someone". INV-027 / DAMMSG-001..003 family.
- **`FIGHT-033`** (🔄 OPEN) — WEAPON_FROST/WEAPON_SHOCKING victim lines drop the
  `$p` weapon name (`"The cold touch surrounds you with ice."` vs ROM
  `"The cold touch of $p surrounds you with ice."`; `"You are shocked by the
  weapon."` vs `"You are shocked by $p."`). Text-content divergence, not cap.
- **`FIGHT-034`** (🔄 OPEN) — the AUTOSPLIT per-member line
  (`mud/combat/engine.py:_auto_split`, ROM `act_comm.c:do_split` `act(...TO_VICT)`)
  routes `"$n splits N silver coins…"` through `expand_placeholders`, which does
  raw-name `$n` substitution with no cap and no PERS — both the INV-029 cap and
  the INV-027 mask are missing.

## Files Modified

Code commit `1b69e449` (8 files):

- `mud/combat/engine.py` — cap at `_broadcast_pos_change` (message + canonical);
  `capitalize_act_line` wrap on the 3 defense TO_CHAR f-strings + the flaming
  victim line (push + fallback); top-level `capitalize_act_line` import.
- `tests/integration/test_fight_031_combat_act_capitalization.py` — NEW, 5 tests.
- `tests/test_weapon_special_attacks.py`, `tests/integration/test_invisibility_combat.py`
  — assertion sweep (3 flips + comments).
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-031 row (✅ FIXED); ACT-CAP-001
  follow-up updated (combat half closed); FIGHT-032/033/034 follow-ups filed.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-029 row: combat
  chokepoint (c) added, cousins list refreshed, Touched-by trail extended,
  status cell honesty (combat path now CLOSED; broadcast_room cousin OPEN).
- `CHANGELOG.md` — 2.11.39 section.
- `pyproject.toml` — 2.11.38 → 2.11.39.

Handoff commit (separate): this summary, `SESSION_STATUS.md`, `README.md`
badge/metric refresh (version 2.11.39, tests 5007).

## Test Status

- `tests/integration/test_fight_031_combat_act_capitalization.py` — 5/5 passing.
- Full suite — **5007 passed, 4 skipped, 0 failed** (parallel; 5002 baseline + 5
  new FIGHT-031 tests; the 3 swept assertions stayed at parity count).
- `ruff check` on changed files — All checks passed. (`ruff format --check`
  flags only pre-existing legacy lines in `engine.py` / `test_invisibility_combat.py`
  NOT touched here — left as-is to avoid unrelated churn, per the INV-029 precedent.)

## Next Steps

Cross-file invariants remains the standing pass. Concrete next options:

1. **Close the remaining INV-029 / ACT-CAP-001 cousins** (each its own
   failing-first test + commit):
   - **`broadcast_room`/`broadcast_global`** (`mud/net/protocol.py`) — the
     remaining non-combat act()-broadcast chokepoint named by ACT-CAP-001. Cap at
     the render boundary; re-baseline the (wide) surface of tests asserting
     lowercase room/broadcast strings.
   - **`do_say`/`do_tell`** (`mud/commands/communication.py` build
     `"{6$n says…"` / `"{k$n tells you…"`; `test_tell_parity.py:19` notes the cap
     as a known deferral).
   - Lesser: the wiznet `WIZ_PREFIX` `"{Z--> "` path (prefix-on case only).
2. **`FIGHT-032`/`FIGHT-033`/`FIGHT-034`** — the combat PERS/text/auto-split
   cousins filed this session (each its own commit; FIGHT-032 is INV-027 family).
3. **`VISION-002`** — dark-gate same-room divergence (`vision.py` vs
   `src/handler.c:2638`; `HANDLER_C_AUDIT.md`). Larger scope; failing test first.
   Do NOT fold into the same session as the cousins.

## Outstanding / carried-open

- **INV-029 cousins** (OPEN, tracked): `broadcast_room`/`broadcast_global`,
  `do_say`/`do_tell`, wiznet `WIZ_PREFIX` — see the INV-029 tracker row + ACT-CAP-001.
- **`FIGHT-032`/`033`/`034`** (OPEN) — combat defense PERS / FROST-SHOCKING `$p`
  drop / auto-split cap+PERS (this session's out-of-scope finds).
- **`VISION-002`** (OPEN) — dark-gate same-room divergence.
- Known **xdist flakes**: `test_combat_death.py`, `test_backstab_uses_position_and_weapon`
  (pass in isolation, can flake under some parallel worker groupings; this
  session's full run had **0 failures**).
- pet-shop haggle / "now follows you" wrong-channel (INV-001 family, mailbox-only);
  `Character.pet` stale type annotation; `do_cast` object-targeting legs.

## Commit / push state

- This session: `1b69e449` (FIGHT-031 code) + the upcoming handoff-docs commit.
- **Local-only, NOT pushed** — await the user's say-so before pushing to
  `origin/master`. (`master` was in sync with `origin/master` at session start.)
- One unrelated pre-existing working-tree change left unstaged:
  `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` (present at session start;
  not part of FIGHT-031).
