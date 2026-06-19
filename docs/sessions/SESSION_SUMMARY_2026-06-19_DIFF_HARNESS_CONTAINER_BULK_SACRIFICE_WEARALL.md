# Session Summary — 2026-06-19 — diff-harness non-mobprog widening: container-lock / bulk-loops / sacrifice / wear-all (FINDING-034)

## Scope

Continued the active mode — **divergence-class sweep, Layer C** (per-file audit
tracker exhausted; enumeration-independent `tools/diff_harness/` widening against
the live ROM C oracle, `DIVERGENCE_CLASS_ROSTER.md` guardrail 3). Picked up the
surveyed-but-not-done non-mobprog command candidates the prior
`SESSION_SUMMARY_2026-06-19_DIFF_HARNESS_EXAMINE_COMPARE.md` handoff left:
container open/close/lock/unlock (OBJECT branch), `get all`/`drop all`/`wear all`
bulk loops, and `sacrifice`. Run as a ~1h self-paced `/loop` session, local
commits only (not pushed). Three scenarios locked clean against C; the fourth
(`wear all`) surfaced a **real parity divergence** — the session's primary win.

## Outcomes

### Container lock cycle (OBJECT branch) — ✅ LOCKED (clean)

- **ROM C**: `src/act_move.c:388-413, 496-516, 626-656, 761-791`
  (`do_open`/`do_close`/`do_lock`/`do_unlock` ITEM_CONTAINER arm)
- **Python**: `mud/commands/doors.py` (container branches)
- **What**: structurally distinct from the already-covered door (EXIT) arm —
  container keys off `value[1]` CONT_* flags + `value[2]` (key vnum), door arm
  off `exit_info` + `pexit->key`. Desk drawer (vnum 3130, protos
  `ABCD`=CLOSEABLE|PICKPROOF|CLOSED|LOCKED, no ITEM_TAKE → referenced in-room via
  `get_obj_here` room fallback) + wooden key (3122) drive a 7-branch sweep:
  lack-key → locked-open guard → unlock → open → not-closed guard → close → lock.
- **Tests**: `test_generated_container_lock_cycle_matches_live_c` — converges on
  first pass, no divergence. C-oracle per-step output confirmed each branch fired
  (triage guard vs. false-green). Commit `a60fc400`, v2.14.135.

### `get all` / `drop all` bulk-loop forms — ✅ LOCKED (clean)

- **ROM C**: `src/act_obj.c` `do_get` (233-253) / `do_drop`
- **What**: pins the bulk room-loop at the loop level (existing scenarios cover
  only per-item `get <obj>`). Sword (3021) + dagger (3020); interleaved `look`
  snapshots assert INV-039/class-13 head-insert LIFO order holds both directions
  (room `[dagger, sword]` ⇄ carry `[sword, dagger]`).
- **Tests**: `test_generated_get_all_drop_all_matches_live_c` — converges first
  pass. C confirmed loop order (get: dagger then small sword; drop: reverse).
  Commit `2a02c8fe`, v2.14.136.

### `sacrifice` object-extraction lifecycle — ✅ LOCKED (clean)

- **ROM C**: `src/act_obj.c:1765-1862` `do_sacrifice` (divergence **class 10** —
  object extraction)
- **Python**: `mud/commands/obj_manipulation.py:365` (SAC-001..006)
- **What**: reward `silver = UMAX(1, level*3)` capped at cost, **no `number_*`**
  on any branch (verified against C — this resolves the RNG-bracket question the
  prior handoff flagged; no `__seed` needed). Self-sac decline → not-found →
  successful room-target sacrifice (small sword 3021, low cost caps reward at 1,
  also hitting the singular `one silver coin` branch) → `look` confirming
  `extract_obj` removal → post-extraction not-found.
- **Tests**: `test_generated_sacrifice_lifecycle_matches_live_c` — converges
  first pass. Commit `4764d454`, v2.14.137.

### `wear all` — ❌ DIVERGENCE FOUND → FINDING-034 / WEAR-012 (filed, xfail)

- **ROM C**: `src/act_obj.c:1712-1723` (`do_wear` "all" loop)
- **Python**: `mud/commands/equipment.py:452-514` (`_wear_all`)
- **Divergence** (step `wear all`):
  - C: `['You light a torch and hold it.', 'You wear a scale mail jacket on your torso.']`
  - py: `['You wear a scale mail jacket on your torso.']` — torch never held.
- **Root cause**: ROM `wear all` calls `wear_obj(ch, obj, FALSE)` unconditionally
  over every carried `WEAR_NONE` item (lights → WEAR_LIGHT, weapons → wield,
  HOLD-flag → WEAR_HOLD). Python's `_wear_all` is a **parallel reimplementation**
  that `continue`s past weapons (line 479), HOLD items (481), and lights
  (`_get_wear_location → None`, 486). The single-item `do_wear <item>` path
  handles all three correctly — only the bulk loop bypasses the dispatch.
- **Filed durably** (a divergence is a finding, not a golden to overwrite):
  - **FINDING-034** (❌ OPEN) in `tools/diff_harness/FINDINGS.md` — full diff,
    all three skip sites, severity MEDIUM, and fix design.
  - **WEAR-012** (❌ OPEN) in `docs/parity/ACT_OBJ_C_AUDIT.md` — gap row for the
    closer.
- **Tests**: `test_generated_wear_all_matches_live_c` committed as
  `@pytest.mark.xfail(strict=True)` — auto-flips to a hard failure when fixed.
  Commit `8215cd1d`, v2.14.138.

## Files Modified

- `tests/test_diff_harness_generated.py` — +4 scenarios (3 passing, 1 xfail)
- `tools/diff_harness/FINDINGS.md` — FINDING-034 added (OPEN)
- `docs/parity/ACT_OBJ_C_AUDIT.md` — WEAR-012 row added (OPEN)
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — Class-11/13 ledger: 3 widening
  entries (container-lock, bulk-loop, sacrifice)
- `CHANGELOG.md` — Added (×3 scenarios) + Found (FINDING-034) entries
- `pyproject.toml` — 2.14.134 → 2.14.138

## Test Status

- `pytest -n0 tests/test_diff_harness_generated.py` — **23 passed, 1 xfailed**.
- `pytest -n0 tests/test_diff_harness_generated.py tests/test_differential_smoke.py
  tests/test_diff_harness_unit.py` — 89 passed (run before the wear-all find).
- `ruff check .` — clean. `gitnexus detect_changes` — LOW risk, 0 affected
  processes on each commit (test + docs + version only, no production code).
- Full suite not re-run this session (changes are test/doc-only; the harness
  scenarios are the verification).

## Next Steps

**Primary: close WEAR-012 / FINDING-034 via `/rom-gap-closer`.** The fix is a
real core-equipment refactor (deferred deliberately — it surfaced unattended near
the session deadline). Do **NOT** loop `do_wear` in `_wear_all`: `do_wear <item>`
passes `fReplace=TRUE` (force-replace), but ROM `wear all` passes `fReplace=FALSE`
(skip occupied slots silently). The faithful port extracts a shared
`wear_obj(ch, obj, fReplace)` mirroring `src/act_obj.c` (ITEM_LIGHT-first
dispatch, then weapon/wear-flag/HOLD branches, honoring `fReplace`); `do_wear
<item>` calls it with `True`, `_wear_all` with `False`. `_wear_all` has a single
caller — the real surface is the not-yet-existing shared `wear_obj`. When it
lands, `test_generated_wear_all_matches_live_c` auto-flips from xfail to pass.

**Then continue non-mobprog widening** (still active mode): `wear all`'s
dual-wield arm (two weapons), `examine` MONEY/CORPSE branches, `look in` a closed
container. **Guardrail 3 reminder**: a clean sweep means "this known surface is
locked," never "close to ROM parity."

**Not pushed** — 4 local commits v2.14.135-138 on master. If pushing: `git push`
(version already bumped, CHANGELOG current).
