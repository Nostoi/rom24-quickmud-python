# `skills.c` — `do_gain` / `do_groups` Focused Audit (trainer & group commands)

- **Date opened:** 2026-06-19 (divergence-sweep probe)
- **ROM source:** `src/skills.c` — `do_gain` (44–250), `do_groups` (~850–920),
  `exp_per_level` (639+), `gn_add`/`group_add`
- **Python module(s):** `mud/commands/remaining_rom.py` (`do_gain`, `do_groups`)
- **Status:** ⚠️ PARTIAL — `do_gain` is substantially un-ported (the core
  "gain a skill/group" path is missing; `gain points` is backwards). Surfaced by
  a probe; the `skills.c` tracker row is ✅ 100% but covers the 37 skill
  **handlers**, not these trainer **commands**.

> **Why this exists:** `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` marks `skills.c` "✅
> Audited 100% — All 37 skills have ROM parity tests." That audit verified the
> spell/skill **effect handlers**. The trainer command `do_gain` and the listing
> command `do_groups` were never audited against ROM and diverge materially.
> This is the third "100%-audited" file in the 2026-06-19 session found to hide
> gaps (after `healer.c` HEALER-005/006 and `board.c` Phase-1 doc-rot). The
> pattern: a file marked 100% on one slice of its surface is not 100% on all of it.

## Gap Table

| ID | Severity | ROM ref | Python ref | Description | Status |
|----|----------|---------|------------|-------------|--------|
| GAIN-001 | CRITICAL | `src/skills.c:174-249` | `mud/commands/remaining_rom.py:253` | `gain <group>` / `gain <skill>` is **not implemented**. ROM looks up the group (`group_lookup`) / skill (`skill_lookup`), validates already-known / class-rating / sufficient `train`, then learns it (`gn_add` for groups — **recursive**; `learned[sn]=1` for skills) and deducts `train -= rating[class]`. Python's final branch returns `"That is not a valid option. Try 'gain list'."` for **any** name — a player cannot gain skills/groups at a trainer. **Feature work, not a one-line fix** — depends on a recursive `gn_add` equivalent (Python has `account_service.add_group` but its recursion + `learned` skill structure must be verified) and the per-`gn` `group_known` representation (Python stores a tuple of names, not ROM's boolean array). **Scope before closing.** | ❌ OPEN |
| GAIN-002 | IMPORTANT | `src/skills.c:149-172` | `mud/commands/remaining_rom.py:240-251` | `gain points` is **backwards on three counts**. ROM: gate `train < 2` → "not ready"; gate `points <= 40` → "There would be no point in that."; then `train -= 2`, **`points -= 1`**, `exp = exp_per_level(ch, points) * level`; message "$N trains you, and you feel more at ease with your skills." Python: same `train < 2` gate, **missing the `points <= 40` gate**, `train -= 2`, **`points += 1`** (wrong direction — `exp_per_level` rises with points, so ROM trades 2 trains to *lower* the point cost / make leveling easier; Python makes it harder), **no exp recalc**, and the wrong message ("you gain a creation point."). | ✅ FIXED — added `points <= 40` guard, flipped `+= 1`→`-= 1`, recompute `char.exp = exp_per_level(char) * level`, message "...feel more at ease with your skills."; `tests/integration/test_do_gain_act_gain_bit.py::test_gain_points_spends_two_trains_to_lower_points_and_recalcs_exp` + `::test_gain_points_refuses_when_points_at_or_below_40` |
| GAIN-003 | IMPORTANT | `src/skills.c:74-131` | `mud/commands/remaining_rom.py:220-227` | `gain list` is a stub — returns "(Group listing not fully implemented)" / "(Skill listing not fully implemented)". ROM lists, in 3-column format, every group/skill the player does **not** know whose `rating[class] > 0` (skills additionally gated to non-spells, `spell_fun == spell_null`). Feature work, same infra gate as GAIN-001. | ❌ OPEN |
| GAIN-004 | MINOR | `src/skills.c:70,137-143,181-244` | `mud/commands/remaining_rom.py:215-251` | Trainer lines use lowercase f-strings (`f"{trainer_name} tells you '...'"`) instead of ROM's `act("$N tells you '...'", …, TO_CHAR)` which first-letter-capitalizes (INV-029, the HEALER-005 act-cap class). Also the no-arg case: ROM is `do_function(trainer, &do_say, "Pardon me?")` — the trainer **says it to the room** via `do_say`, not a TO_CHAR return. Characterize as the act-cap class + a say-to-room nuance; do not let it become a rewrite. | ❌ OPEN |
| GROUPS-001 | CRITICAL | `src/skills.c` `do_groups` | `mud/commands/remaining_rom.py:276-295` | `do_groups` (no-arg) **crashes** for any player who knows groups: `group_known` is a `tuple[str, ...]` (`mud/models/character.py:213`) but the no-arg branch calls `sorted(group_known.keys())` and `group_known[name]` as if it were a dict → `AttributeError: 'tuple' object has no attribute 'keys'`. Empirically reproduced 2026-06-19. The `all` / `<group>` branches use the real `mud.skills.groups` table and are fine; only the no-arg "your known groups" branch has the stale dict assumption. | ✅ FIXED — no-arg branch now iterates the `group_known` name tuple directly; `tests/integration/test_do_groups_known_groups.py` |

## Notes

- GAIN-001 / GAIN-003 are **feature work gated on infrastructure** (`gn_add`
  recursion, `learned` skill map, `group_known` representation). File-and-scope,
  do not half-build in a loop. Recommended next: verify `account_service.add_group`
  recursion + the `learned` structure, then close GAIN-001 (the core path) and
  GAIN-003 (its `list` sibling) together.
- GAIN-002 and GROUPS-001 are clean, self-contained units closed this session.
