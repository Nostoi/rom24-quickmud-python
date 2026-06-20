# Session Summary — 2026-06-20 — social_table/INV-052 + CAST-013 (per-spell min position)

## Scope

Continuation of the prior `/loop` table-diff session (per-file audit tracker is
drained; the active pass is systematic ROM↔Python static-table diffs + cross-file
invariants). Two items landed:

1. **`social_table` diff → INV-052** (the prior session's #1 candidate).
2. **CAST-013** — per-spell `minimum_position` (the prior session's #2 candidate,
   previously tagged "HIGH-blast-radius → FILE, do not fix autonomously"; the user
   explicitly authorized the fix this turn, so it was verified-then-fixed).

Picked up the **#1 next-intended task** from `SESSION_STATUS.md`: the
`social_table` diff (`area/social.are` ⇄ `data/socials.json`), which the prior
session left INCONCLUSIVE because a naive line-parser of `social.are` is wrong
(variable-length records, `$` NULL sentinels, `#` early-terminators).

Built a **faithful parser** replicating ROM `src/db2.c:load_socials` +
`src/db.c:fread_word`/`fread_to_eol`/`fread_string_eol` (leading-whitespace strip,
trailing-whitespace preserve, `$`→NULL, `#`→early-terminate) and did a full
244-social × 8-field join. Result: the table is **byte-clean** except one
systematic pattern — **384 fields are ROM-NULL (`$`) vs JSON `""`**, with ZERO
content differences. That pattern turned out to be a real (if subtle) behavioral
divergence in the act-delivery layer, closed as **INV-052**.

## Outcomes

### `INV-052` — ✅ ENFORCED (ACT-EMPTY-DISCARD) — new cross-file invariant

- **ROM C**: `src/comm.c:2240-2244 act_new` — `if (format == NULL || format[0]
  == '\0') return;` is the function's *first* statement, BEFORE the per-recipient
  loop, so it suppresses both delivery AND the per-NPC `mp_act_trigger`/`TRIG_ACT`
  dispatch (`src/comm.c:2384-2385`). Sibling `act_new` sub-contract to INV-025
  (trigger dispatch), INV-027 (PERS masking), INV-029 (first-letter cap).
- **Divergence**: ROM-NULL social slots (the `$` sentinel) load as `""` in
  `data/socials.json`. Python's `act_to_room`/`socials._act_to_char` rendered
  `act_format("")` → `""` and `push_message(recipient, "")` delivered a **spurious
  blank line**; `act_to_room` additionally fired `TRIG_ACT` on the empty message.
  Empirically reproduced: a no-arg `kiss` (`others_no_arg` is ROM-NULL) sent every
  room bystander an empty line; ROM sends nothing.
- **Fix**: `act_new`-faithful empty-guard at the TOP (before loop/push/trigger) of
  the two delivery boundaries the socials path uses —
  `mud/utils/act.py:act_to_room` (closes the room side for ALL ~101 callers) and
  `mud/commands/socials.py:_act_to_char` (social TO_CHAR/TO_VICT). A
  `push_message`-level guard was rejected (advisor): it would fix the blank line
  but leave the spurious `TRIG_ACT` (downstream of the trigger dispatch).
- **Scope honesty**: covers all room broadcasts + the socials directed-line class.
  A general sweep of direct single-recipient `push_message`/`send_to_char_buffered`
  empty-variable sites *outside* socials is an un-done, low-yield follow-up (most
  pass literals/guaranteed-non-empty buffers) — spelled out in the INV status cell
  so "ENFORCED" isn't misread as "every act() empty everywhere is guarded."
- **Blast radius**: `act_to_room` is CRITICAL by caller-count (101), but the change
  is a pure additive guard mirroring ROM exactly — it can only suppress empties
  ROM also suppresses. Full suite green confirms the behavioral delta is narrow.
- **Tests**: `tests/integration/test_inv052_act_empty_discard.py` (4 — act_to_room
  empty→no delivery, act_to_room empty→no TRIG_ACT, socials._act_to_char empty→no
  delivery, end-to-end `kiss` no-arg → no blank line to bystander).

### `CAST-013` — ✅ FIXED (per-spell minimum casting position)

- **ROM C**: `src/magic.c:341-345` — `do_cast` gates on
  `ch->position < skill_table[sn].minimum_position` → "You can't concentrate
  enough." (field `src/merc.h:1951`; per-spell `POS_*` in `const.c` skill_table).
- **Divergence**: Python `do_cast` (`mud/commands/combat.py:911`) used a **flat**
  `char.position < Position.FIGHTING` for every spell. Since the `cast` command
  gate is `POS_FIGHTING` (INTERP-031), the caster is FIGHTING(7) or STANDING(8)
  by the time the per-spell gate runs, so the observable effect was exactly:
  **a fighting character could cast `POS_STANDING` utility/buff spells** (armor,
  bless, every detect_*, charm person, create_*, cure disease/poison — 55 spells)
  that ROM blocks. Offensive (`POS_FIGHTING`, 72 spells) were already correct.
- **Fix (2.14.199)**:
  - `Skill.minimum_position: Position` (default **FIGHTING** — advisor's safe
    backstop: identical to the old flat gate, so an unmapped spell can never
    regress an offensive cast; only a mapped STANDING spell newly blocks).
  - `ROM_SKILL_MIN_POSITION` in `metadata.py`, derived from `const.c` via
    `parse_skill_table` (POS_* token → `Position` enum, never a hardcoded int) +
    hand-added cancellation/harm=FIGHTING (the CONST-009 parser-skipped pair).
  - `parse_skill_table` now emits `minimum_position`; `registry.load` sets it.
  - `do_cast` gates on `skill.minimum_position`.
  - **`data/skills.json` intentionally NOT regenerated** (advisor): a regen drops
    cancellation/harm and clobbers CONST-008's `target=friendly`.
- **Scope**: do_cast only — matches ROM (obj_cast_spell / scroll-wand-staff do
  NOT check position; mob AI casting doesn't go through do_cast's gate).
- **Tests**: `test_spell_casting.py::TestCast013PerSpellMinPosition` (13 —
  fighting blocked on STANDING spell, fighting allowed on FIGHTING spell,
  standing allowed on STANDING spell, a parser-derived completeness anti-drift
  guard, **and 9 hardcoded independent anchors** spanning STANDING/FIGHTING/
  RESTING so the completeness guard isn't circular — it derives both sides from
  the parser, so the anchors independently pin the parser's column extraction).
- **Audit**: `docs/parity/MAGIC_C_AUDIT.md` row `CAST-013` ✅ FIXED.

## Clean negative (verified, no further gap)

- **`social_table` is byte-clean.** 244 socials, all 8 fields, full faithful join:
  no missing/extra socials, no name dups, zero content differences. The only
  divergence was the NULL-vs-`""` representation, neutralized by INV-052. This
  resolves the prior session's INCONCLUSIVE `social_table` item — it is now a
  CLEAN NEGATIVE save for the one act-layer fix.

## Files Modified

INV-052:
- `mud/utils/act.py` — INV-052 empty-guard at top of `act_to_room`.
- `mud/commands/socials.py` — INV-052 empty-guard at top of `_act_to_char`.
- `tests/integration/test_inv052_act_empty_discard.py` — new (4 tests).
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — new INV-052 row + scope-honest status.

CAST-013:
- `mud/commands/combat.py` — `do_cast` gates on `skill.minimum_position`.
- `mud/models/skill.py` — `Skill.minimum_position: Position` field.
- `mud/skills/metadata.py` — `ROM_SKILL_MIN_POSITION` (const.c-derived) + `_POS_BY_NAME`.
- `mud/skills/registry.py` — `registry.load` sets `skill.minimum_position`.
- `mud/scripts/convert_skills_to_json.py` — `parse_skill_table` emits `minimum_position`.
- `tests/integration/test_spell_casting.py` — `TestCast013PerSpellMinPosition` (13 tests).
- `docs/parity/MAGIC_C_AUDIT.md` — new `CAST-013` row (✅ FIXED).

Shared:
- `CHANGELOG.md` — Fixed entries (CAST-013, INV-052).
- `pyproject.toml` — 2.14.197 → **2.14.199** (INV-052 at .198, CAST-013 at .199).

## Test Status

- `test_inv052_act_empty_discard.py` — 4/4; `TestCast013PerSpellMinPosition` — 13/13.
- Full suite: **5992 passed, 4 skipped** (was 5984/4 at session start; +8 across
  the two new test surfaces). `ruff check`/`ruff format` clean on all touched files.
- GitNexus reindexed exit-0 (only the 2 documented harmless C-header scope
  failures `recycle.h`/`olc.h`; zero Python failures).

## Next Steps / Outstanding

The low-risk data/registration veins remain drained. Remaining candidates, in
priority order:

1. **INTERP-028** (🔄 OPEN, MINOR) — duplicate `bs` registration (alias on
   `backstab` + standalone `Command("bs", …)`). Cosmetic, no observable
   divergence.
2. **Per-spell `min_position`** — ✅ **CLOSED this session as CAST-013 (2.14.199)**.
   do_cast now gates on each spell's own `minimum_position` (const.c-derived);
   the prior "HIGH-blast-radius → FILE don't fix" tag is retired (the change is a
   strictly parity-correcting per-spell value substitution, verified by the full
   suite). No further action.
3. **INV-052 follow-up (low-yield)** — general sweep of direct single-recipient
   `push_message`/`send_to_char_buffered` empty-variable sites outside socials.
   Re-open with a per-site gap only if a scenario/golden surfaces a blank-line
   leak; do not grind a full audit speculatively.
4. **Risk posture (advisor)**: when a behavioral divergence needs logic changes in
   a HIGH-blast-radius core path (combat/movement/dispatch), file it, don't fix
   autonomously. Pure additive guards that mirror a single ROM function exactly
   (like INV-052 / INTERP-034) are the exception — they are strictly
   parity-correcting and safe despite wide caller counts.
