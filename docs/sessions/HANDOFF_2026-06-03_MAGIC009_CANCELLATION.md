# Handoff — 2026-06-03 — MAGIC-009: cancellation missing per-effect dispel roll

## TL;DR for the next agent

`spell_cancellation` (the `cancellation` spell) strips **every** active spell
effect from its target **unconditionally**. ROM rolls a per-effect
`check_dispel`/`saves_dispel` chance for each effect, so cancellation can (and
usually does, against high-level effects) **fail per effect**. The Python port
is too strong and ignores caster level entirely. This is a real gameplay/parity
bug, filed as **MAGIC-009** (`❌ OPEN`) in
[`docs/parity/MAGIC_C_AUDIT.md`](../parity/MAGIC_C_AUDIT.md).

Use the **`rom-gap-closer`** skill with gap ID `MAGIC-009`.

## ROM source of truth

- `src/magic.c` `spell_cancellation` (≈1033-1203): after the PC/NPC target gate,
  it runs, for each dispellable spell:
  ```c
  if (check_dispel (level, victim, skill_lookup ("armor"))) found = TRUE;
  ...
  ```
  (`level` is `caster level + 2`, set at the top.)
- `src/magic.c` `check_dispel` (≈231-261):
  ```c
  bool check_dispel(int dis_level, CHAR_DATA *victim, int sn) {
      if (is_affected(victim, sn)) {
          for (af = victim->affected; af; af = af->next) {
              if (af->type == sn) {
                  if (!saves_dispel(dis_level, af->level, af->duration)) {
                      affect_strip(victim, sn);
                      // send skill_table[sn].msg_off to victim
                      return TRUE;
                  } else
                      af->level--;   // failed dispel weakens the effect
              }
          }
      }
      return FALSE;
  }
  ```
- `src/magic.c` `saves_dispel` (≈243-252): `save = 50 + (spell_level - dis_level)*5`,
  `+5` to `spell_level` if `duration == -1` (permanent), clamped `URANGE(5, save, 95)`,
  returns `number_percent() < save`.

**Critical nuance (this is what was misread):** the ROM comment
`/* unlike dispel magic, the victim gets NO save */` means cancellation skips the
**upfront `saves_spell`** (the wholesale wisdom save that `spell_dispel_magic`
grants the victim). It does **NOT** mean the per-effect `saves_dispel` rolls are
skipped — those still run inside `check_dispel`. Don't repeat the misread.

## Python state (the bug)

- `mud/skills/handlers.py:1868` `cancellation(caster, target)`.
- The inner helper `_cancel_effect` (≈1901) does:
  ```python
  def _cancel_effect(effect_name: str) -> bool:
      effect = target.spell_effects.get(effect_name)
      if effect is None:
          return False
      removed = target.remove_spell_effect(effect_name)   # <-- UNCONDITIONAL, no roll
      if removed and removed.wear_off_message:
          target.send_to_char(f"{removed.wear_off_message}\n\r")
      return bool(removed)
  ```
- `level = caster.level + 2` is computed at ≈1877 but **unused** — currently
  carried with `# noqa: F841  # MAGIC-009` as the breadcrumb. The fix makes it
  used; remove the noqa.

## The fix (infra already exists)

`check_dispel` is **already implemented and ROM-faithful** in
`mud/affects/saves.py` and is the proven pattern used by `dispel_magic`
(`mud/skills/handlers.py:3526`), `cure_blindness` (2707), `cure_poison` (2818),
`slow` (5019). It does the `saves_dispel` roll, removes + sends the wear-off
message on success, and does `effect.level -= 1` on a failed dispel. Only
`cancellation` diverged.

Replace `_cancel_effect`'s body with a delegation to `check_dispel`:
```python
def _cancel_effect(effect_name: str) -> bool:
    return check_dispel(level, target, effect_name)
```
(`check_dispel` is already imported at `handlers.py:9`.) This:
- uses `level` (drop the `# noqa: F841` at ≈1877),
- performs the per-effect `saves_dispel` roll,
- removes the **duplicate** wear-off send (`check_dispel` already sends it — the
  current `_cancel_effect` would otherwise double-send),
- preserves the existing `act_to_room(...)` lines that fire on a successful
  `_cancel_effect(...)` for blindness/calm/charm/etc.

Watch for: a couple of cancellation effects may have bespoke handling
(`change_sex`, `charm_person`) — verify each `if _cancel_effect("X"): ... act_to_room(...)`
block still reads correctly when removal is now conditional. The `found` flag and
the final "Ok." / "Spell failed." messaging should be unchanged.

## Tests — three existing assertions encode the misread (must be rewritten)

`tests/test_spell_cancellation_rom_parity.py`:
- `test_cancellation_no_save` (≈114): level-1 caster vs a level-5 effect, asserts
  `result is True`. With ROM `check_dispel`, `save = URANGE(5, 50+(5-3)*5, 95) = 60`,
  so it **fails ~60%** of the time — the assertion is non-ROM. Rewrite to control
  RNG (below) and assert the ROM outcome.
- `test_cancellation_removes_multiple_effects` (≈73): asserts
  `len(spell_effects) == 0`. Only true if all `saves_dispel` rolls fail. Rewrite
  with controlled RNG (force all dispels to succeed, or assert per-effect).
- `test_cancellation_level_bonus` (≈103): probabilistic; make deterministic.

**Deterministic RNG control:** `saves_dispel` (`mud/affects/saves.py`) calls
`rng_mm.number_percent()`. Either:
- `monkeypatch.setattr(mud.affects.saves.rng_mm, "number_percent", lambda: 1)`
  → roll 1 < save → **save succeeds → effect NOT removed** (test the failure leg), or
- `... lambda: 100` → roll 100 ≥ save → **dispel succeeds → effect removed**.

Write the RED test first (per `rom-gap-closer`): e.g. low-level caster, force
`number_percent → 1`, assert a high-level effect **survives** cancellation and
`result is False`. It fails today (unconditional strip removes it); passes after
the fix. Then realign the 3 legacy tests above to ROM behavior. A test asserting
non-ROM behavior is a bug in the **test** (AGENTS.md).

## Done-criteria checklist

- [ ] RED test added (cancellation respects `saves_dispel`), fails before fix.
- [ ] `_cancel_effect` routes through `check_dispel`; `level` used; noqa removed.
- [ ] 3 legacy `test_spell_cancellation_rom_parity.py` tests realigned to ROM (RNG-controlled).
- [ ] Full suite green (`pytest`).
- [ ] `dispel_magic` parity unaffected (it already used `check_dispel`; run its tests).
- [ ] `MAGIC-009` row in `MAGIC_C_AUDIT.md` flipped to `✅ FIXED (<version>)`.
- [ ] CHANGELOG `Fixed` entry + `pyproject.toml` version bump.
- [ ] `gitnexus_impact(cancellation)` before editing; `detect_changes` before commit.

## Other open items from this session (lower priority)

- **GL-034** (`UPDATE_C_AUDIT.md`, OPEN) — ROM auto-quits at most one idle PC per
  `char_update` tick (`ch_quit` single-pointer, last-wins); Python quits all
  candidates. Low impact.
- **GL-035** (`UPDATE_C_AUDIT.md`, OPEN) — connected-player idle **autoquit** needs
  async descriptor teardown the synchronous tick can't do; INV-038 gated autoquit
  to link-dead chars. Connected idlers still void to limbo (ROM-correct), just
  don't auto-quit.
- **test-fixtures-lint** (`.pre-commit-config.yaml`, `stages: [manual]`) — style
  lint, ~617 legacy test sites; re-enable on the commit stage once migrated, or
  rework to lint only changed files.

## Repo state at handoff

- Version `2.12.91`; `ruff check .` and `ruff format --check .` fully clean.
- pre-commit active in-clone (5 commit-stage hooks: ruff, ruff-format,
  validate-area-parity, equipment-key-convention, attribute-convention).
  Other clones need `pip install pre-commit && pre-commit install`.
- Full suite green (5373 passed / 4 skipped at last run).
