# Session Summary — 2026-06-20 — INV-052 + CAST-013 + INTERP-028 (table/contract sweep)

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

### `INTERP-028` — ✅ FIXED (duplicate `bs` registration)

- **ROM C**: `src/interp.c:238,240` — two cmd_table rows: `{"backstab",
  do_backstab, POS_FIGHTING, …, 1}` (shown) and `{"bs", do_backstab,
  POS_FIGHTING, …, 0}` (hidden), BOTH → `do_backstab`.
- **Divergence**: Python registered `bs` both as an alias of `backstab` AND as a
  standalone `Command("bs", do_bs, …)` (the standalone overwrote the alias in
  `COMMAND_INDEX`), routing through a needless `do_bs` wrapper.
- **Fix (2.14.200)**: removed `bs` from `backstab`'s aliases; pointed the
  standalone hidden `bs` row at `do_backstab` directly (`show=False`,
  `POS_FIGHTING`), mirroring ROM's two rows; deleted the dead `do_bs` wrapper
  (`remaining_rom.py`) + its import. No behavioral change (both already reached
  backstab) — cleanup + ROM-faithful show flags, collision removed.
- **Tests**: `test_interp_dispatcher.py::test_interp_028_bs_is_hidden_backstab_alias_no_collision`
  (both → do_backstab; backstab shown / bs hidden; both POS_FIGHTING; no dual
  registration). `test_all_commands.py` + full interp suite green.

### INV-052 follow-up sweep — ✅ DONE (clean negative, no code change)

- Audited all 43 direct single-recipient `push_message` / `send_to_char_buffered`
  / `_send_to_char_sync` sites outside socials. Every one is safe: it either
  (a) passes a **constant non-empty literal** template to `act_format`,
  (b) already **guards `if formatted:`/`if message:`** before delivery, or
  (c) routes through `act_to_room`/`_act_to_room` (now INV-052-guarded at the
  boundary). The socials path was the **unique** site feeding a data-derived
  (possibly-`""`) string into the act layer. Recorded in the INV-052 row.

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

INTERP-028:
- `mud/commands/dispatcher.py` — `bs` no longer a `backstab` alias; standalone
  hidden `bs` row → `do_backstab`; `do_bs` import removed.
- `mud/commands/remaining_rom.py` — deleted the dead `do_bs` wrapper.
- `tests/integration/test_interp_dispatcher.py` — INTERP-028 test.
- `docs/parity/INTERP_C_AUDIT.md` — row `INTERP-028` ✅ FIXED.

INV-052 follow-up:
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-052 row records the
  43-site sweep as a clean negative.

Shared:
- `CHANGELOG.md` — Fixed entries (INTERP-028, CAST-013, INV-052).
- `pyproject.toml` — 2.14.197 → **2.14.200** (INV-052 @.198, CAST-013 @.199,
  INTERP-028 @.200).

## Test Status

- `test_inv052_act_empty_discard.py` — 4/4; `TestCast013PerSpellMinPosition` —
  13/13; `test_interp_028_…` — 1/1.
- Full suite: **6002 passed, 4 skipped** (was 5984/4 at session start; +18 across
  the new test surfaces: INV-052 +4, CAST-013 +13, INTERP-028 +1). `ruff check`/
  `ruff format` clean on all touched files;
  `test_all_commands.py` green (the pre-existing `tap` false-positive is a
  `test_all_commands` probe artifact — `tap` IS registered as a `sacrifice`
  alias — not a parity bug).
- GitNexus reindexed clean earlier; the MCP server disconnected late in the
  session, so the final pre-commit check used `git diff` review (changes scoped
  to the intended symbols) — reindex on next session start.

## Next Steps / Outstanding

All three of this session's candidates are now CLOSED:
- **INTERP-028** ✅ FIXED (2.14.200) — `bs`/`backstab` dual registration removed.
- **CAST-013** ✅ FIXED (2.14.199) — per-spell `minimum_position`.
- **INV-052 follow-up** ✅ DONE — 43-site direct-push sweep, clean negative.

The per-file audit is fully drained and the cross-INV / per-file passes are now
enumeration-*dependent* (they only confirm contracts someone already named).

**Next session START HERE → expand the differential harness (`tools/diff_harness/`).**
Per `DIVERGENCE_CLASS_ROSTER.md` guardrail #3, the only enumeration-INDEPENDENT
check — the one that finds divergences nobody predicted — is differential execution
vs the ROM C oracle.

Harness maturity (verified 2026-06-20): **41 committed scenarios, all 41 converge**
(`KNOWN_DIVERGENCES` empty; the stale "4 scenarios" comment in the smoke test
predates this). Already covered: movement, melee + spell combat, shops
(buy/sell/insufficient/keeper-broke), the full mob-trigger set, char_update regen
(15 variants), affects, money, aggression, drink/eat. Leverage is in NEW scenarios
on **genuinely un-exercised surfaces** (grep-verified, 0 scenarios touch these):
doors (`open`/`close`/`lock`/`pick`), containers (`put`/get-from/nesting), character
advancement (`practice`/`train`/`gain`), death→corpse→auto-loot→`sacrifice`,
equipment cycle (`wield`/`wear all`/`remove`), group/`follow`, and a cast-position
scenario to lock CAST-013 differentially.

1. **Build the shim (one-time):** `cd src && make -f Makefile.diffshim diffshim`
   (additive; ROM `src/*.c` unchanged), then `python3 -m tools.diff_harness.capture
   --all`. Read `tools/diff_harness/README.md` first.
2. **Author 2–3 new scenarios** from the un-exercised list above; capture goldens;
   `pytest tests/test_differential_smoke.py` to replay.
3. **A divergence is a FINDING, not a golden to overwrite** — triage, record in
   `FINDINGS.md`, route to `/rom-gap-closer` or a new INV-NNN, fix Python/data.
4. **Triage existing open `FINDINGS.md` items** — LOW/cosmetic output-format
   divergences (`look`/`examine`/`wear all`) surfaced but not closed.

Secondary (do NOT lead with these): GitNexus MCP reconnect/reindex at session
start; the `test_all_commands.py` `tap` false-positive (harness artifact —
resolves to `sacrifice`, not a parity bug); cross-INV probe / signed-math (class 7)
only if the harness work stalls.

**Risk posture (advisor)**: HIGH-blast-radius behavioral logic changes → file,
don't fix. Exception (proven 3× — INV-052, CAST-013, INTERP-034): a change
mirroring one ROM function/value exactly is strictly parity-correcting and safe.
