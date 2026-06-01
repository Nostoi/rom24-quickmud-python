# Session Summary — 2026-06-01 — INV-025/INV-027 PERS-masking sweep (MAGIC-010, MAGIC-005, MAGIC-006, FIGHT-036)

## Scope

Continued the cross-file invariant probe pass (per-file audit tracker
exhausted) on the INV-025 / INV-027 PERS-masking sweep — picking up the filed
gap queue from the prior session's `SESSION_STATUS.md` (MAGIC-007 had just
closed the visible-object `$p` remainder). This session closed the next four
queued divergences, each a single failing-test-first gap-closer commit:

1. **MAGIC-010** — object-invisibility `$p` masks the caster too.
2. **MAGIC-005** — poison-object room legs mask via `can_see_obj`.
3. **MAGIC-006** — plague room line `$s skin` + `$n` PERS.
4. **FIGHT-036** — dirt-kick blind room line `$s eyes` + `$n` PERS + `{5..{x`.

Four commits landed: `f50ce63f` (2.12.32), `d70ce1e0` (2.12.33),
`2ed4924c` (2.12.34), `b6a3ad8a` (2.12.35).

## Outcomes

### `MAGIC-010` — object-invis `$p` masks caster + already-invisible early-out — ✅ FIXED (2.12.32)

- **ROM C**: `src/magic.c:3620-3641` — `spell_invisibility` object branch sets
  `ITEM_INVIS` via `affect_to_obj` (`:3638`) **before** `act("$p fades out of
  sight.", ch, obj, NULL, TO_ALL)` (`:3640`). `TO_ALL` includes the caster, and
  the object is invisible at render time, so `can_see_obj` masks `$p` to
  "Something" for the caster AND every witness without detect-invis/holylight.
- **Python**: `mud/skills/handlers.py:invis` object branch. Both legs now render
  `$p` per-recipient — caster via `act_format("$p fades out of sight.",
  recipient=caster, actor=caster, arg1=obj)`, room via `act_to_room(...,
  arg1=obj, exclude=caster)`. Dropped the dead `message`/`capitalize_act_line`
  locals.
- **Advisor catch (folded in)**: the same-branch "already invisible" early-out
  (`:3627`, `act("$p is already invisible.", ch, obj, NULL, TO_CHAR)`) shared
  the `can_see_obj` root cause → `_send_to_char(caster, act_format("$p is
  already invisible.", ...))`.
- **Tests**: `tests/integration/test_magic010_object_invis_pers_masking.py` (3 —
  caster+witness mask to "Something", detect-invis witness sees the short_descr,
  already-invisible early-out masks). Updated pinned baked-name assertions in
  `test_skills_buffs.py` (584/585/618/619 → "Something fades out of sight.",
  589 → "Something is already invisible."). Corrected the now-stale comment in
  `test_act_cap_002_room_broadcast.py:113-118` (that test asserts `.isupper()`
  only — "Something …" still passes; the audit row had over-stated it as a
  blocker).

### `MAGIC-005` — poison-object room legs mask via `can_see_obj` — ✅ FIXED (2.12.33)

- **ROM C**: `src/magic.c:3946` (`"$p is infused with poisonous vapors."`,
  food/drink) and `:3981` (`"$p is coated with deadly venom."`, weapon) — both
  `act(..., TO_ALL)`.
- **Python**: `mud/skills/handlers.py:poison` — both room legs converted from
  baked-name `_act_room` to `act_to_room("$p ...", caster, arg1=obj,
  exclude=caster)`. Poison does NOT set `ITEM_INVIS` (unlike MAGIC-010), so the
  caster `_send_to_char` leg keeps the baked short_descr (the caster targeted a
  visible object) — weapon leg capped per ACT-CAP-002, food leg uncapped, both
  unchanged (MAGIC-007 precedent). Existing assertions `test_skills_debuffs.py`
  153/154/190/191 still pass.
- **Tests**: `tests/integration/test_magic005_poison_object_pers_masking.py` (3 —
  blind witness masks weapon + food to "Something …", sighted witness sees the
  short_descr).

### `MAGIC-006` — plague room line `$s skin` + `$n` PERS masking — ✅ FIXED (2.12.34)

- **ROM C**: `src/magic.c:3921` — `act("$n screams in agony as plague sores
  erupt from $s skin.", victim, NULL, NULL, TO_ROOM)`.
- **Python**: `mud/skills/handlers.py:plague` — room leg converted from baked
  `_act_room(f"{name} ... their skin.")` to `act_to_room("$n screams in agony as
  plague sores erupt from $s skin.", target, exclude=target)`. `$n` masks an
  invisible victim to "Someone"; `$s` renders the gendered possessive
  (his/her/its).
- **Tests**: `tests/integration/test_magic006_plague_pronoun_masking.py` (3 —
  male→"his", female→"her", invisible victim→"Someone"). Updated
  `test_skills_debuffs.py::test_plague_applies_affect_and_messages` "their"→"its"
  (a sexless test character defaults to `Sex.NONE` → "its", the ROM-faithful
  neuter — `_possessive_pronoun` maps an *unset* sex attribute to "their", but
  `Character.sex` defaults to `Sex.NONE`=0 → "its").

### `FIGHT-036` — dirt-kick blind room line `$s eyes` + `$n` PERS + `{5..{x` — ✅ FIXED (2.12.35)

- **ROM C**: `src/fight.c:2614` — `act("{5$n is blinded by the dirt in $s
  eyes!{x", victim, NULL, NULL, TO_ROOM)`.
- **Python**: `mud/skills/handlers.py:dirt_kicking` — room leg converted from
  baked `_act_room(f"{victim_name} ... their eyes!")` to `act_to_room("{5$n is
  blinded by the dirt in $s eyes!{x", victim, exclude=victim)`. `$n` masks an
  invisible victim; `$s` gendered; `{5..{x` colour preserved (act_format passes
  non-`$` chars verbatim, `capitalize_act_line` honours the leading `{`-kludge).
- **Tests**: `tests/integration/test_fight036_dirt_kick_pronoun_masking.py` (3 —
  male→"his", female→"her", invisible victim→"Someone"; asserts presence not
  `[-1]` because the damage broadcast follows the blind line).
- **GitNexus note**: the MCP server disconnected mid-gap (the background reindex
  restarts it). Impact analysis fell back to grep per AGENTS.md — `dirt_kicking`
  has one caller (`do_dirt`, `combat.py:1033`); message-only change; the
  dirt-kick suites (113) + full suite (5225) confirm no regression.

## Files Modified

- `mud/skills/handlers.py` — `invis`, `poison`, `plague`, `dirt_kicking` room/
  caster legs converted to `act_format`/`act_to_room`; added `act_format` to the
  `mud.utils.act` import.
- `tests/integration/test_magic010_object_invis_pers_masking.py` — new (3).
- `tests/integration/test_magic005_poison_object_pers_masking.py` — new (3).
- `tests/integration/test_magic006_plague_pronoun_masking.py` — new (3).
- `tests/integration/test_fight036_dirt_kick_pronoun_masking.py` — new (3).
- `tests/test_skills_buffs.py` — invis baked-name assertions → "Something".
- `tests/test_skills_debuffs.py` — plague "their"→"its".
- `tests/integration/test_act_cap_002_room_broadcast.py` — stale comment fix.
- `docs/parity/MAGIC_C_AUDIT.md` — MAGIC-010/005/006 → ✅ FIXED; **filed MAGIC-011**.
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-036 → ✅ FIXED; **filed FIGHT-037**.
- `CHANGELOG.md` — 4 Fixed entries.
- `pyproject.toml` — 2.12.31 → 2.12.35.
- `README.md` — synced version badge/line 2.12.11 → 2.12.35 and test count
  5130/5107 → 5225 passing (commit `772cf681`, after the original handoff
  commit). Audit-coverage numbers left as-is (40 audited + 3 N/A = 43, matches
  the tracker).

## Push state

All 7 commits pushed to `origin/master` (`9ce58ae4..772cf681`). Working tree
clean, in sync with origin. This was a complete, shipped session — not a
mid-stream handoff.

## Test Status

- Each new integration file — 3/3.
- Affected unit suites (`test_skills_buffs`, `test_skills_debuffs`,
  `test_skills_combat`, `test_skill_combat_rom_parity`) — green.
- Full suite: **5225 passed, 4 skipped** (`pytest`, parallel). Progression:
  5213 at session start → 5216 (MAGIC-010 +3) → 5225 (+3 MAGIC-005, +3 MAGIC-006,
  +3 FIGHT-036). +12 tests total across the four new files.
- `ruff check mud/skills/handlers.py` — 5 pre-existing B007/F841 only, identical
  before/after; none introduced.
- GitNexus `detect_changes` confirmed LOW/0-affected-processes scope for
  MAGIC-010/005/006; FIGHT-036 verified by grep fallback (MCP disconnected).

## Outstanding (next agent)

The INV-025 / INV-027 PERS-masking queue now has only the **structural** gaps
left (TO_VICT/TO_NOTVICT splits to rebuild, not token swaps):

1. **MAGIC-004** — `chain_lightning` TO_NOTVICT/TO_VICT split.
2. **FIGHT-035** — `disarm` fail-line double-broadcast + TO_CHAR/TO_VICT/
   TO_NOTVICT structure + `{5..{x` colour.
3. **FIGHT-037** (filed this session) — dirt-kick TO_VICT/victim-self legs drop
   `{5..{x` colour; Python invents a caster "You kick dirt…" line ROM never
   emits (`src/fight.c:2616/2618`; success branch has no caster message).
4. **MAGIC-011** (filed this session) — poison **food/drink** caster leg is not
   capitalized (`handlers.py:poison` ~6546, `src/magic.c:3946`). ROM
   `act(TO_ALL)` caps for every recipient incl. the caster ("Loaf of bread is
   infused…"); Python emits lowercase. A missed site under the CLOSED
   ACT-CAP-002 invariant (the weapon leg above it *is* capped). Surfaced by
   advisor review while closing MAGIC-005.
5. **CAST-009** — failed-cast skill improvement (🔄 OPEN in `MAGIC_C_AUDIT.md`).
6. **TRAIN-005** — remains open per prior status.

> **Repo hygiene note for the next push:** `README.md` is stale — badge/Version
> "2.12.11" and "Test Suite: 5107 passed" vs current 2.12.35 / 5225. It was
> already 20+ patch-versions behind before this session (not introduced here).
> Per AGENTS.md Repo Hygiene, refresh README version/badge/test-count (and
> confirm AGENTS.md tracker pointers) **before pushing** to keep README /
> AGENTS / SESSION_STATUS in agreement. Nothing was pushed this session — all
> commits are local on `master`.
