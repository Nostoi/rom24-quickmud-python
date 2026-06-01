# Session Summary — 2026-06-01 — MAGIC-007 object-`$p` PERS masking

## Scope

Continued the cross-file invariant probe pass (per-file audit tracker
exhausted) on the INV-025 / INV-027 PERS-masking sweep — the next intended
task from the prior session's `SESSION_STATUS.md` ("MAGIC-007 — object-`$p`
sweep remainder"). The prior session (2.12.30) converted the 26 char-`$n`-only
single-actor spell room lines from the baked-name module-level `_act_room` to
the shared `act_to_room` helper; this session converts the **object-`$p`**
remainder.

One commit landed: **`84c9e4a0` (2.12.31)**.

## Outcomes

### `MAGIC-007` — object-`$p` spell room lines mask via `can_see_obj` — ✅ FIXED

- **Python**: `mud/skills/handlers.py` — every visible-object `$p` room
  broadcast converted from `_act_room(room, f"...{short_descr}...", actor,
  exclude=...)` (baked name, no visibility check) to
  `act_to_room(room, "$p ..."/"$n ... $p", actor, arg1=obj, exclude=...)`
  (per-recipient `act_format` → `_object_name` → `can_see_object` masking +
  per-NPC `TRIG_ACT`).
- **ROM C**: each line verified against its exact `act("$p ...", ch, obj, NULL,
  TO_ROOM/TO_ALL)` source — acid/fire effect inventory-burn
  (`src/magic.c:3156/3182/3214/3240`), bless object pale-blue + holy-aura
  (`:808/:829`), enchant_armor (`:2358/:2370/:2418/:2427`), enchant_weapon
  (`:2556/:2566/:2614/:2623`), fireproof (`:2785`), recharge (`:4158/:4195`),
  remove_curse object (`:4233`) + per-item `$n's $p` loop (`:4268`), pick-lock
  (`src/act_move.c:907/:945`), portal/nexus (`src/magic2.c:101/:155/:171`).
- **Fix**: token conversion to `$p`/`$n's $p`; the enchant_armor /
  enchant_weapon closures changed signature from a pre-baked `message` to a
  format string. **The enchant_weapon TO_ROOM leg preserves ROM's `:2557`
  `"explodeds!"` typo byte-for-byte** (the TO_CHAR leg at `:2556` reads
  `"explodes!"`) — confirmed by reading ROM source, not "fixed". Caster
  `_send_to_char` legs stay on the baked short_descr (the caster can always see
  a visible object they target).
- **Excluded** (genuinely out of scope, filed durably): object-invis
  `"$p fades out of sight"` (`:3640`, TO_ALL — behaviorally distinct, see
  MAGIC-010), poison-object (`:3946/:3981` → MAGIC-005), plague
  (`:3921` → MAGIC-006), chain_lightning (MAGIC-004).
- **Tests**: `tests/integration/test_magic007_object_pers_masking.py` — fireproof
  with a blind witness masks the object to "Something is surrounded by a
  protective aura." (failed before the fix on the leaked "Ancient scroll"), and
  a sighted-witness visible-render guard. The two-token `$n … $p` path is
  additionally exercised by the existing `tests/integration/test_pick_broadcasts.py`.

### `MAGIC-010` — object-invis `$p` masks the caster too — ❌ FILED (not fixed)

- **ROM C**: `src/magic.c:3640` — `spell_invisibility` object branch sets
  `ITEM_INVIS` via `affect_to_obj` (`:3638`) **before** the
  `act("$p fades out of sight.", ch, obj, NULL, TO_ALL)`. `can_see_obj`
  (`src/handler.c`) returns FALSE for the now-invisible object for any char
  without detect-invis/holylight — so the **caster** AND every witness see
  "Something fades out of sight.", not the object name.
- **Why excluded from MAGIC-007**: unlike the visible-object sites (where the
  baked caster leg is harmless), here the object is genuinely invisible — both
  legs must render `$p`, and that flips ~3 existing test assertions
  (`test_skills_buffs.py:584/585/618/619`,
  `test_act_cap_002_room_broadcast.py:123`) that currently pin the
  ROM-incorrect baked name. Behaviorally distinct → its own gap/test/commit.
- Filed in `docs/parity/MAGIC_C_AUDIT.md` with the `can_see_obj` proof and the
  exact test assertions it will need to update.

### `MAGIC-005` — stale-row correction (not a code change)

- The original row asserted poison_weapon "invents text / wrong `$n` subject".
  The current code already emits ROM-correct `"{obj} is coated with deadly
  venom."` / `"{obj} is infused with poisonous vapors."`. Corrected the row:
  the only remaining divergence is the **same object-`$p` masking** as
  MAGIC-007 (poison-object room legs still go through baked-name `_act_room`).
  Anti-pattern caught: don't relay a written ✅/claim without re-checking source
  (AGENTS.md "ALWAYS re-verify").

## Files Modified

- `mud/skills/handlers.py` — ~16 object-`$p` room legs converted to
  `act_to_room`; enchant_armor/enchant_weapon `_notify_room` closures reshaped
  to take a format string.
- `tests/integration/test_magic007_object_pers_masking.py` — new (2 tests).
- `docs/parity/MAGIC_C_AUDIT.md` — MAGIC-007 → ✅ FIXED (2.12.31, enumerated
  sites + exclusions); added MAGIC-010; corrected the stale MAGIC-005 row.
- `CHANGELOG.md` — Fixed entry (MAGIC-007).
- `pyproject.toml` — 2.12.30 → 2.12.31.

## Test Status

- `tests/integration/test_magic007_object_pers_masking.py` — 2/2.
- Affected area suites (skills buffs/damage/transport/healing, pick_broadcasts,
  inv030 bless, act_cap_002) — 84/84.
- Full suite: **5213 passed, 4 skipped** (`pytest`, parallel; +2 from the new
  test vs the prior 5211).
- `ruff check mud/skills/handlers.py` — 5 pre-existing B007/F841 findings only,
  identical before/after (verified via `git stash`); none introduced.
- `gitnexus_detect_changes` — risk LOW, 0 affected processes, all changes
  confined to `mud/skills/handlers.py` spell handlers.

## Outstanding (next agent)

Continue the INV-025 / INV-027 PERS-masking pass via the filed gaps:

1. **MAGIC-010** — object-invis `$p` masks caster + room (both legs); render
   the caster leg via `act_format(recipient=caster, actor=caster, arg1=obj)`
   and the room leg via `act_to_room`; update the ~3 pinned baked-name test
   assertions to "Something fades out of sight." (ROM-correct).
2. **MAGIC-005** — poison-object room legs (infused/coated) → `act_to_room`
   with `$p` (text is already correct; only masking remains).
3. **MAGIC-006** — plague `their skin` → `$s skin` + `$n` masking.
4. **MAGIC-004** (chain_lightning) and **FIGHT-035** (disarm) — structural
   TO_VICT/TO_NOTVICT splits to rebuild, not token swaps.
5. **FIGHT-036** — dirt-kick `their eyes` → `$s eyes` + colour.

`CAST-009` (failed-cast skill improvement) also remains 🔄 OPEN in
`MAGIC_C_AUDIT.md`.
