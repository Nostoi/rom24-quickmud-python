# Session Summary — 2026-06-19 — /loop gap-closer: WEAR-012, LOOK-008, LOOK-009 (harness-found divergences)

## Scope

A self-paced `/loop` gap-closer session ("close the next gap via
`/rom-gap-closer`, repeat until 5, then handoff"). Picked up from the
diff-harness widening session earlier today
(`SESSION_SUMMARY_2026-06-19_DIFF_HARNESS_CONTAINER_BULK_SACRIFICE_WEARALL.md`),
whose only pre-documented open gap was WEAR-012. With the per-file audit tracker
exhausted, gaps 2+ had to be **surfaced** via continued differential probing
(harness vs. live ROM C oracle) before they could be closed — the same
enumeration-independent loop that found WEAR-012. Closed **3 genuine ROM
divergences**, each verified against the live C oracle; stopped at 3/5 because
genuine divergences are getting scarce (most probes now converge clean) and
guardrail 3 forbids manufacturing gaps to hit a count.

## Outcomes

### `WEAR-012` / FINDING-034 — ✅ FIXED (gap 1)

- **ROM C**: `src/act_obj.c:1401-1695` (`wear_obj`), `1712-1723` (`do_wear` "all")
- **Python**: `mud/commands/equipment.py` (`_wear_obj`, `_wear_all`, `_dispatch_wield`)
- **Gap**: `wear all` silently skipped lights, weapons, and HOLD items — ROM
  calls `wear_obj(ch, obj, FALSE)` over every carried `WEAR_NONE` item; Python's
  `_wear_all` was a parallel reimplementation that `continue`d past all three.
- **Fix**: extracted a shared `_wear_obj(ch, obj, fReplace)` mirroring ROM;
  `do_wear <item>` calls it with `fReplace=True` (force-replace, behavior-
  preserving), `_wear_all` with `fReplace=False` (occupied slots skipped
  silently per ROM `remove_obj`).
- **Tests**: `test_wear_all_equips_light_weapon_and_hold` (integration) +
  `test_generated_wear_all_matches_live_c` (xfail removed; converges vs C).
  Commit `25e1829c`, v2.14.139.

### `LOOK-008` / FINDING-035 — ✅ FIXED (gap 2)

- **ROM C**: `src/act_info.c:1183-1212` (`do_look` object resolution)
- **Python**: `mud/world/look.py` (`_look_obj`, `look`)
- **Gap**: `look`/`examine` on an object showed the `description` AND the first
  extra-description unconditionally. ROM is keyword-gated and mutually
  exclusive: an ED whose keyword matches the lookup arg is shown alone; only a
  bare name match (no ED match) shows the description. Surfaced by `examine
  coins` on a money pile emitting both "A lot of silver is here." and the
  "silver" ED.
- **Fix**: `_look_obj` now takes the lookup keyword and applies ROM's
  instance-ED → prototype-ED → name(description) priority; `look()` callers
  thread `args`.
- **Tests**: `test_examine_object_extra_descr_is_keyword_gated` (integration) +
  `test_generated_examine_money_pile_matches_live_c` (C oracle). Commit
  `f748a821`, v2.14.140.

### `LOOK-009` / FINDING-036 — ✅ FIXED (gap 3)

- **ROM C**: `src/act_info.c:447-454` (`show_char_to_char_1`)
- **Python**: `mud/world/look.py` (`_look_char`)
- **Gap**: looking at a description-less character rendered the name/short_descr,
  not the objective pronoun. ROM uses `act("You see nothing special about $M.")`
  → `$M` = him/her/it. `look <sexless char>` emitted "...about Tester." where
  ROM emits "...about it."
- **Fix**: render the line via `act_format("You see nothing special about $M.",
  recipient=char, actor=char, arg2=victim)`.
- **Tests**: `test_look009_no_descr_renders_objective_pronoun_not_name`
  (integration; sexless→"it", male→"him") +
  `test_generated_look_at_self_no_descr_matches_live_c` (C oracle). Commit
  `10327a59`, v2.14.141.

## Process correction (important — verification flaw caught)

The gap-2 (LOOK-008) `_look_obj` keyword-gating broke
`test_runtime_bugs_2026_04_30::test_look_obj_handles_dict_extra_descr` (it called
`_look_obj` with no keyword, expecting the ED unconditionally). **The gap-2
full-suite check MASKED this**: the command was `pytest -q 2>&1 | tail -12`, so
the reported "exit 0" was `tail`'s exit code, not pytest's — a failing pipeline's
exit code is the last stage's. The gap-3 full-suite run (redirected to a file,
exit captured directly) caught it. The test was updated to pass the ED keyword
"marble" (preserves its dict-ED-parsing intent, ROM-faithful) in commit
`10327a59`. **Lesson: never read a `pytest | tail` exit code as the test result —
capture pytest's exit directly** (`pytest > f 2>&1; echo $?`). The f748a821 commit
message's "full suite green" claim was therefore wrong at the time; corrected and
re-verified at gap 3.

## Files Modified

- `mud/commands/equipment.py` — shared `_wear_obj(ch, obj, fReplace)` dispatch (WEAR-012)
- `mud/world/look.py` — `_look_obj` keyword-gating (LOOK-008), `_look_char` `$M` pronoun (LOOK-009)
- `tests/integration/test_equipment_system.py` — `test_wear_all_equips_light_weapon_and_hold`
- `tests/integration/test_do_examine_command.py` — `test_examine_object_extra_descr_is_keyword_gated`
- `tests/integration/test_look007_look_at_char_broadcast.py` — `test_look009_...`
- `tests/integration/test_runtime_bugs_2026_04_30.py` — dict-ED test updated for keyword-gating
- `tests/test_diff_harness_generated.py` — 3 new C-oracle scenarios (wear_all, examine_money, look_self)
- `docs/parity/ACT_OBJ_C_AUDIT.md` — WEAR-012 ✅ FIXED
- `docs/parity/ACT_INFO_C_AUDIT.md` — LOOK-008, LOOK-009 ✅ FIXED
- `tools/diff_harness/FINDINGS.md` — FINDING-034/035/036 ✅ RESOLVED
- `CHANGELOG.md`, `pyproject.toml` — 2.14.138 → 2.14.141

## Test Status

- Full suite (exit captured directly): **5852 passed, 4 skipped, PYTEST_EXIT=0**
  (252–284s). ruff clean. Each gap also verified converging against the live ROM
  C oracle via `tests/test_diff_harness_generated.py` (now 26 scenarios, all green).
- `gitnexus detect_changes` LOW risk, 0 affected processes on every commit.

## Next Steps

Loop stopped at **3/5** gaps — a deliberate, honest stop: genuine harness-findable
divergences on the probed surfaces (look/examine/wear/get/drop/sacrifice/container
/money) are largely closed out; most new probes now converge clean, and guardrail
3 forbids manufacturing gaps to reach a count. To continue hunting gaps 4–5, probe
**unexamined command surfaces** next (each is a fresh divergence-discovery target):
`score`/`who`/`where`/`weather`/`time`, social commands, combat/death output,
group/follow messaging, `give`/`put`-into-mob edge cases. Author a throwaway probe
(C-oracle vs pyreplay) per surface; close any real divergence via `/rom-gap-closer`,
file any cross-file root cause as the next INV-NNN. **6 commits v2.14.139-141 on
master, NOT pushed** — `git push` if sharing (versions/CHANGELOG current). Reminder
(guardrail 3): a clean sweep means "this known surface is locked," never "close to
ROM parity."
