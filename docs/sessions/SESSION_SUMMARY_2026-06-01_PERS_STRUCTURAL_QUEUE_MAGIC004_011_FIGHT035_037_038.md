# Session Summary — 2026-06-01 — INV-025/INV-027 structural queue drain (MAGIC-011, FIGHT-037, FIGHT-035, FIGHT-038, MAGIC-004)

## Scope

Continued the cross-file invariant probe pass (per-file audit tracker exhausted)
on the INV-025 / INV-027 PERS-masking sweep, picking up the prior session's
`SESSION_STATUS.md` "Outstanding" queue — which was down to the **structural**
gaps (TO_CHAR/TO_VICT/TO_NOTVICT splits, colour, mid-sentence PERS) plus two
small filed ones. This session closed all of them, each a failing-test-first
gap-closer commit:

1. **MAGIC-011** — poison food/drink caster line capitalization (ACT-CAP-002 miss).
2. **FIGHT-037** — dirt-kick victim legs colour/PERS + drop invented caster line.
3. **FIGHT-035** — disarm TO_CHAR/TO_VICT/TO_NOTVICT split + double-broadcast fix.
4. **FIGHT-038** — NOREMOVE disarm skill-improvement TRUE (surfaced closing FIGHT-035).
5. **MAGIC-004** — chain_lightning `$n`/`$N` per-recipient PERS masking.

Five commits landed: `f7f177df` (2.12.36), `63e58ab4` (2.12.37),
`6eb93eda` (2.12.38), `01fa68ea` (2.12.39), `04f118e8` (2.12.40).

**Recurring finding:** three of the five audit rows had **materially wrong ROM
references or scope** that only surfaced on reading the C source (the AGENTS.md
re-verify discipline). All three were corrected in their audit docs. See the
"ROM-ref accuracy" note under Outstanding.

## Outcomes

### `MAGIC-011` — poison food/drink caster line capitalized — ✅ FIXED (2.12.36)

- **ROM C**: `src/magic.c:3946` `act("$p is infused with poisonous vapors.", ch,
  obj, NULL, TO_ALL)`; `act_new` caps `buf[0]`/`buf[2]` for **every** recipient
  incl. `ch` (`src/comm.c:2376-2379`).
- **Python**: `mud/skills/handlers.py:poison` food caster leg (~6561) wrapped in
  `capitalize_act_line`, matching the sibling weapon leg (`:3981`). A missed site
  under the closed ACT-CAP-002 invariant (INV-029).
- **Tests**: `tests/integration/test_magic011_poison_food_caster_caps.py` (2).
  Re-baselined `test_skills_debuffs.py:190` and
  `test_magic005_poison_object_pers_masking.py:113` ("loaf"→"Loaf").

### `FIGHT-037` — dirt-kick victim legs colour/PERS + no invented caster line — ✅ FIXED (2.12.37)

- **ROM C**: `src/fight.c:2611-2631` (`do_dirt` success) — `:2616` TO_VICT
  `"{5$n kicks dirt in your eyes!{x"`, `:2618` `send_to_char("{5You can't see a
  thing!{x\n\r", victim)`; the success branch sends the kicker **no** self line.
- **Python**: `mud/skills/handlers.py:dirt_kicking` — TO_VICT via `act_format`
  (`$n` masks invisible kicker, `{5..{x`), victim self-line coloured, invented
  `"You kick dirt in …'s eyes!"` caster line removed (the kicker only sees the
  `:2614` blind line via FIGHT-036's `act_to_room`). Dead name locals removed.
- **Tests**: `tests/integration/test_fight037_dirt_kick_victim_legs.py` (4).

### `FIGHT-035` — disarm TO_CHAR/TO_VICT/TO_NOTVICT split — ✅ FIXED (2.12.38)

- **ROM C**: fail path `src/fight.c:3211-3215` (`do_disarm`, THREE legs),
  NOREMOVE `:2244-2248`, success `:2252-2255` (`disarm` helper). Every
  TO_NOTVICT leg excludes **both** ch and victim.
- **Python**: `mud/skills/handlers.py:disarm` — rebuilt all three paths.
  TO_CHAR/TO_VICT via `act_format` (PERS `$n`/`$N`, `$S` gendered possessive for
  the "won't budge" line, `{5..{x`, restored "DISARMS" caps); TO_NOTVICT via
  `act_to_room(actor=caster, exclude=victim)` so the caster is auto-excluded AND
  the victim excluded — neither actor double-receives; bystanders get it once.
  Fixes the real bug: the prior code excluded only one actor, so the other
  double-received the third-person room line. Dead name locals removed.
- **ROM-ref correction**: the audit row cited `:2245-2255` for the fail path; the
  real skill-roll fail is `do_disarm:3211-3215`. Corrected in `FIGHT_C_AUDIT.md`.
- **Tests**: `tests/integration/test_fight035_disarm_act_structure.py` (4 — fail
  TO_NOTVICT excludes both actors, invisible-caster `$n` mask, success
  colour/caps/exclusion, NOREMOVE `$S` possessive + caster exclusion).
  Re-baselined `test_skills_combat.py:164` ("disarms you"→"DISARMS you…").

### `FIGHT-038` — NOREMOVE disarm credits skill improvement TRUE — ✅ FIXED (2.12.39)

- **ROM C**: `src/fight.c:3202-3217` — `do_disarm` only enters the success branch
  on a made roll and unconditionally calls `check_improve(ch, gsn_disarm, TRUE,
  1)` (`:3206`). The NOREMOVE case lives inside `disarm()` (`:2242-2249`), which
  returns, so control falls back to `:3206` — a won't-budge disarm is still
  credited TRUE.
- **Python**: `mud/skills/handlers.py:disarm` NOREMOVE branch (~3391) changed
  `check_improve(..., False, 1)` → `True`.
- **Gap origin**: pre-existing; surfaced by advisor review while closing FIGHT-035
  and filed durably (AGENTS.md out-of-scope-bug routing) before being closed.
- **Tests**: `tests/integration/test_fight038_disarm_noremove_improve.py` (1).

### `MAGIC-004` — chain_lightning `$n`/`$N` per-recipient PERS masking — ✅ FIXED (2.12.40)

- **ROM C**: `src/magic.c:1234-1307` — first strike `:1244` TO_ROOM
  `"A lightning bolt leaps from $n's hand and arcs to $N."` (excludes only `ch`;
  the victim IS a recipient — `TO_ROOM`, not TO_NOTVICT), `:1246` TO_CHAR, `:1248`
  TO_VICT, bounce `:1270` TO_ROOM `"The bolt arcs to $n!"`, caster-hit `:1295`.
- **Python**: `mud/skills/handlers.py:chain_lightning` — converted the 5
  token-bearing legs to `act_to_room`/`act_format`. Tokens are mid-sentence, so a
  masked actor renders **lowercase** "someone". No-token legs left as-is. Dead
  name locals removed.
- **ROM-ref + scope correction**: the audit row over-stated this as a structural
  "3-way split collapse" with a `TO_NOTVICT` first strike — the real ROM is
  `TO_ROOM` and the Python already had three legs; the only divergence was the
  baked names. Severity downgraded MEDIUM→LOW. Corrected in `MAGIC_C_AUDIT.md`.
- **Tests**: `tests/integration/test_magic004_chain_lightning_pers_masking.py`
  (4 — first-strike room/vict mask invisible caster, first-strike room masks
  invisible victim, bounce masks invisible bounce target).

## Files Modified

- `mud/skills/handlers.py` — `poison`, `dirt_kicking`, `disarm`, `chain_lightning`
  message legs converted to `act_format`/`act_to_room`; dead name locals removed.
- `tests/integration/test_magic011_poison_food_caster_caps.py` — new (2).
- `tests/integration/test_fight037_dirt_kick_victim_legs.py` — new (4).
- `tests/integration/test_fight035_disarm_act_structure.py` — new (4).
- `tests/integration/test_fight038_disarm_noremove_improve.py` — new (1).
- `tests/integration/test_magic004_chain_lightning_pers_masking.py` — new (4).
- `tests/integration/test_magic005_poison_object_pers_masking.py` — re-baseline (1 line).
- `tests/test_skills_debuffs.py` — re-baseline (poison food "Loaf").
- `tests/test_skills_combat.py` — re-baseline (disarm "DISARMS you").
- `docs/parity/MAGIC_C_AUDIT.md` — MAGIC-011/004 → ✅ FIXED (+ ROM-ref corrections).
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-037/035 → ✅ FIXED; **filed + closed FIGHT-038** (+ ROM-ref correction).
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-029 ACT-CAP-002 missed-leg trail (MAGIC-011).
- `CHANGELOG.md` — 5 Fixed entries.
- `pyproject.toml` — 2.12.35 → 2.12.40.

## Test Status

- Each new integration file green (15 new tests total: 2+4+4+1+4).
- Affected unit suites (`test_skills_combat`, `test_skills_debuffs`,
  `test_skills_damage`, `test_skill_combat_rom_parity`,
  `test_spell_damage_additional_rom_parity`) — green.
- Full suite: **5240 passed, 4 skipped** (`pytest`, parallel).
- `ruff check` — only the 5 pre-existing B007/F841 in `handlers.py`; new test
  files clean.
- GitNexus `detect_changes` confirmed LOW/0-affected-processes for every gap.

## Push state

All 5 commits committed to local `master` (`f7f177df..04f118e8`). **Not pushed.**
Working tree clean. Before pushing: see the README hygiene note below.

## Outstanding (next agent)

The INV-025 / INV-027 PERS-masking structural queue is now **drained** — all of
MAGIC-004, FIGHT-035, FIGHT-037, MAGIC-011 (the prior session's queue) plus the
discovered FIGHT-038 are closed. Remaining from the broader backlog:

1. **CAST-009** — failed-cast skill improvement (🔄 OPEN in `MAGIC_C_AUDIT.md`).
2. **TRAIN-005** — remains open per prior status.
3. Continue the cross-file-invariants pass on a fresh candidate area (affect
   ticks, position transitions, mob script triggers, group/follower chain).

> **ROM-ref accuracy warning for the next agent:** THREE of the five audit rows
> closed this session had ROM references or scope descriptions that were
> materially wrong (FIGHT-035 cited the NOREMOVE branch for the fail path;
> MAGIC-004 claimed a `TO_NOTVICT` 3-way-collapse that didn't exist — real ROM is
> `TO_ROOM` and the legs were already present). All three were caught only by
> reading the C source, per the AGENTS.md re-verify discipline. **Distrust the
> remaining ⚠️/❌ rows' ROM line numbers and bug descriptions until re-checked
> against `src/` — they were written during a fast INV-025 exclusion sweep and
> several over-state the divergence.**

> **Repo hygiene note for the next push:** verify `README.md` Version/badge/test
> count before pushing (per AGENTS.md Repo Hygiene). Current state: version
> 2.12.40, full suite 5240 passed / 4 skipped. Confirm README + AGENTS tracker
> pointers + this `SESSION_STATUS.md` agree in the same commit.
