# Session Summary — 2026-06-01 — INV-025 single-actor spell PERS masking + invis broadcast order

## Scope

Continued the cross-file invariant probe pass (per-file audit tracker exhausted)
on INV-025 / INV-027 PERS masking — the next intended task from the prior
session's `SESSION_STATUS.md` ("convert remaining `handlers.py` callers that bake
`_character_name()` into f-strings to `act_to_room` with `$n` tokens").

Two commits landed:

1. **`24ef1759` (2.12.29)** — committed the *prior* session's finished but
   uncommitted work (INV-025 cancellation wear-off PERS masking + ENTER-018
   portal PERS masking + the shared `act_to_room` helper in `mud/utils/act.py`).
   Tree was dirty at session start; tests were green; committed as-is.
2. **`1c1782c3` (2.12.30)** — this session's work (below).

## Outcomes

### INV-025 / INV-027 — single-actor spell-effect PERS masking — ✅ FIXED (26 sites)

- **Python**: `mud/skills/handlers.py` — 26 `_act_room(room, f"{_character_name(X)} ...", X, exclude=X)`
  sites converted to `act_to_room(room, "$n ...", X, exclude=X)` (the shared helper
  added last session). The module-level `_act_room` (`broadcast_room` +
  `mp_act_trigger_room`) baked the name once with **no** `can_see` check, leaking
  invisible (or dark-room) actor names; `act_to_room` renders `$n` per recipient
  through `act_format` → `_pers` → `can_see_character`.
- **ROM C**: each line verified against its exact `act("$n ...", ch, ..., TO_ROOM)`
  source — floating disc (`magic.c:2874`), gate ×4 (`:2994-3009`), summon
  (`:4497-4500`), teleport (`:4528-4531`), nexus (`:4615-4618`), word-of-recall
  (`act_move.c:1575`), infravision (`:3598`), invis (`:3650`), mass-invis fade
  (`:3837`), change-sex `$mself` (`:1340`), pink outline (`:2822`), purple smoke
  (`:2833`), word of divine power (`:3291`), blinding ray `$s` (`:4089`),
  poison-save (`:3993`), poisoned (`:4008`), blindness-save (`:4098`), calm
  "looks more relaxed" (`:4252`).
- **Fix**: token conversion (`$n`, `$s`, `$mself`); removed the now-dead
  `_character_name`/`caster_name`/`victim_name`/`pet_name`/`possessive`/`reflexive`
  locals and the orphaned `_reflexive_pronoun` helper.
- **Tests**: `tests/integration/test_inv025_spell_self_effect_pers_masking.py` —
  `test_infravision_masks_invisible_target_name`,
  `test_infravision_shows_visible_target_name` (visible-render guard).

### `MAGIC-008` — invis broadcast order — ✅ FIXED

- **Python**: `mud/skills/handlers.py:invis` (~5654).
- **ROM C**: `src/magic.c:3650-3659` — `act("$n fades out of existence.", victim, TO_ROOM)`
  fires **before** `affect_to_char` sets `AFF_INVISIBLE`, then the self `send_to_char`.
- **Gap**: Python applied the affect first, then broadcast — harmless with a baked
  name, but once the line renders through per-recipient PERS it wrongly masked the
  just-invisible target to "someone" (exposed by the masking sweep; two legacy
  invis tests flipped to "someone"). `mass_invis` already broadcast first.
- **Fix**: reordered `invis` to broadcast → apply → self-message.
- **Tests**: `...::TestInvisBroadcastOrder` (invis + mass_invis broadcast-before-affect,
  lit room → real name). Also pinned the unseeded to-hit roll in
  `test_combat_rom_parity.py::test_ac_clamping_for_negative_values` (a pre-existing
  global-RNG-leak flake that surfaced in parallel once the invis tests completed
  instead of erroring).

### Deferred divergences surfaced mid-sweep — FILED (not fixed)

Excluded from the clean single-actor sweep and filed durably:

- `MAGIC-004` — chain_lightning collapses ROM's TO_NOTVICT/TO_CHAR/TO_VICT 3-way
  split and mis-targets the bolt-arc line (`magic.c:1244-1295`).
- `MAGIC-005` — poison_weapon uses invented text/`$n` subject vs ROM
  `act("$p is coated with deadly venom.", ch, obj, TO_ALL)` (`:3981`).
- `MAGIC-006` — plague uses "their skin" vs ROM `$s skin` + baked name (`:3921`).
- `MAGIC-007` — INV-025/INV-027 object-`$p` sweep remainder (acid/fire burns,
  object-invis, portal rises, pick-lock, enchant glows) + `message`-variable
  `_act_room` sites needing per-site review.
- `FIGHT-035` — disarm double-broadcasts the fail line and drops ROM's
  TO_CHAR/TO_VICT/TO_NOTVICT structure + `{5..{x` colour (`fight.c:2245-2255`).
- `FIGHT-036` — dirt-kick blind line uses "their eyes" vs ROM `$s eyes`, baked
  name, no colour (`fight.c:2614`).

## Files Modified

- `mud/skills/handlers.py` — 26 `act_to_room` conversions; invis reorder; dead-var
  + `_reflexive_pronoun` cleanup.
- `tests/integration/test_inv025_spell_self_effect_pers_masking.py` — new (5 tests).
- `tests/test_skills_debuffs.py` — `test_poison_save_prevents_affect` room made lit
  (INSIDE) so the visible victim renders by name (dark-room masking is ROM-correct).
- `tests/test_combat_rom_parity.py` — pinned `number_percent` in the AC-clamping test.
- `docs/parity/MAGIC_C_AUDIT.md` — added MAGIC-004/005/006/007/008 rows.
- `docs/parity/FIGHT_C_AUDIT.md` — added FIGHT-035/036 rows.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-025 "Touched by" trail extended.
- `CHANGELOG.md` — two Fixed entries (sweep + MAGIC-008).
- `pyproject.toml` — 2.12.29 → 2.12.30.

## Test Status

- `tests/integration/test_inv025_spell_self_effect_pers_masking.py` — 5/5.
- Full suite: **5211 passed, 4 skipped** (`pytest`, parallel).
- `ruff check` on changed files: no new findings (5 pre-existing handlers.py
  B007/F841 + 2 pre-existing test B009 unchanged).

## Next Steps

Continue the INV-025/INV-027 PERS-masking pass via the filed gaps. Highest-value
next: `MAGIC-007` (object-`$p` sweep remainder — same invariant, mechanical once
each ROM `act()` format string is verified), then the structural divergences
`MAGIC-004` (chain_lightning) and `FIGHT-035` (disarm), which need ROM
TO_VICT/TO_NOTVICT splits rebuilt, not just token swaps. `CAST-009` (failed-cast
skill improvement) remains OPEN in `MAGIC_C_AUDIT.md`.
