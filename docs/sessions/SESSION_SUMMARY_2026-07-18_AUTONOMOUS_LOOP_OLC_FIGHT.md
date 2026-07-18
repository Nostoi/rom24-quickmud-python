# Session Summary — 2026-07-18 — Autonomous loop (OLC setters + combat recall-oracle)

## Framing

User requested "continue with the next session then loop 15 times for 15
sessions." Per the advisor's reframing (validated against the recon), the well
is nearly dry at 43/43 audited + 102/102 differential, so the honest deliverable
is **genuine iterations, not padded commits**: a mix of real closures, clean
probes, and recall-oracle re-verifications — never a synthesized change to hit a
count (the AURA-001 trap). Read ROM C in `src/` FIRST every iteration. Did **not**
push (operator review still pending on the prior ~19 local commits).

## What landed (15 iterations: 7 closures + 1 fixup + 7 probes)

**Iterations 1-9** ran first; **10-15** on the user's "Resume". Totals:
7 parity closures (OLC_ACT-015/016/017/018/019, FIGHT-104, ENV-005), 1 test
fixup, 7 recall-oracle probes (6 clean/faithful + 1 deep-probe filing), and
4 new OPEN gaps filed durably (OLC_ACT-020/021, ENV-003 re-opened, ENV-006).
Version 2.14.331 → **2.14.338**. Full suite: **6265 passed, 4 skipped, 0
failed**. **Local-only — not pushed** (operator review pending).

### Iterations 1-9 (initial run: 5 closures + 1 fixup + 4 clean probes)

| # | Iteration | Outcome | Commit |
|---|-----------|---------|--------|
| 1 | **OLC_ACT-015** — `redit heal`/`redit mana` bare success message | closure | `3eb836fc` |
| 2 | **OLC_ACT-016** — `redit room`/`redit sector` ROM verbatim `"Sintaxis:"` errors + sector value-leak | closure | `dd951e34` (+ test fixup `53232294`) |
| 3 | **FIGHT-104** — inviso-strip runs BEFORE parry/dodge in `damage()` | **genuine combat find** (recall-oracle) | `80e476b1` |
| 4 | `damage()` epilogue (hurt→immortal-floor→update_pos→pos messages→stop_fighting→death) vs `src/fight.c:820-878` | **clean probe** — faithful, covered | — |
| 5 | **OLC_ACT-017** — oedit `level/weight/cost/material` messages + removed non-ROM `level>=0` guard | closure | `7bb02048` |
| 6 | `is_safe` / `_kill_safety_message` vs `src/fight.c:1018-1124` (INV-050) | **clean probe** — branch-for-branch faithful | — |
| 7 | **OLC_ACT-018** — medit `level/align/hitroll/material` messages + removed non-ROM `level>=1` / `align ±1000` guards | closure | `1d1cce52` |
| 8 | `update_pos` vs `src/fight.c:1380` (hit>0 stand-up, NPC-instant-death, -11/-6/-3 thresholds) | **clean probe** — exact match | — |
| 9 | `set_fighting`/`stop_fighting` vs `src/fight.c:1416`/`stop_fighting` (guard + sleep-strip; order-insensitive reset walk) | **clean probe** — faithful | — |

Iterations 4/6/8/9 form a recall-oracle sweep of the combat `damage()` pipeline
after FIGHT-104: four consecutive clean probes confirm the epilogue, PK-safety,
position, and fighting-state machinery are ROM-faithful. Diminishing returns on
further combat probing — future iterations should target other subsystems.

### Continuation — iterations 10-15 (user "Resume"): 2 closures + 3 clean probes + 1 deep-probe filing

| # | Iteration | Outcome | Commit |
|---|-----------|---------|--------|
| 10 | **OLC_ACT-019** — `aedit security` gates on the **builder's own clearance** (`value > ch->pcdata->security`), not a hardcoded 0-9 | closure — **behavioral permission fix** | `ec025285` |
| 11 | char affect-expiry tick (`tick_spell_effects`) vs `src/update.c:762-785` | **clean probe** (INV-040 order + GL-026 RNG + INV-018 suppression) — surfaced ENV-005 | — |
| 12 | **ENV-005** — `envenom` head-inserts the poison affect (ROM `affect_to_obj`) instead of appending | closure — INV-040/045 object-affect order | `21abbe42` |
| 13 | object affect-decay tick (`_tick_object_affects`) vs `src/update.c:928-961` | **clean probe** (GL-045 RNG + `msg_obj` carrier/room dispatch + suppression) | — |
| 14 | `gain_condition` vs `src/update.c:367` | **clean probe** — faithful (URANGE clamp, `-1` permanent, DRUNK old-value guard) | — |
| 15 | `aedit_builder` toggle grammar / proper-case / IS_BUILDER | **deep probe → enriched OLC_ACT-020 filing** (fix deferred, not rushed) | `<docs>` |

**Continuation highlights:**
- **OLC_ACT-019** is a real OLC **permission** divergence (not cosmetic): Python let any builder set security up to 9 regardless of their own clearance; ROM caps it at the builder's `pcdata.security`. Locked by a security-5-can't-set-6 mutation test.
- **ENV-005** found by an affect-tick recall-oracle probe (iter 11): `do_envenom` appended the poison affect where ROM `affect_to_obj` head-inserts, desyncing the object-affect decay tick's per-affect RNG. Also **re-opened ENV-003** (its "never-walked obj.affected" premise is stale) and filed **ENV-006** (envenom skips `affect_to_obj`'s `value[4]` bit — verify poison-on-hit fires).
- **New OPEN gaps filed durably** this continuation: OLC_ACT-020 (aedit_builder), OLC_ACT-021 (aedit_vnum range-setter semantics), ENV-003 (re-opened), ENV-006. All with concrete fix specs.
- The affect-tick + condition machinery (char & object) is now **verified faithful** — a second swept-clean subsystem after the combat pipeline.

### Highest-value find: FIGHT-104

Recall-oracle re-verification of the load-bearing FIGHT-092 ✅ claim against ROM
C exposed a live divergence. ROM `damage()` strips an invisible attacker's
invisibility (`src/fight.c:763-769`) BEFORE the parry/dodge/shield_block checks
(`:790-800`), so a **parried/dodged/blocked** attacker still "fades into
existence." Python's `apply_damage` placed the inviso-strip AFTER the defense
early-returns — a defended attacker stayed invisible — hidden behind an
incorrect FIGHT-092 comment ("parry/dodge resolve in one_hit before damage()").
That justification is wrong for both engines: `attack_round` defers defenses to
`apply_damage` (engine.py:700-702). Fixed by moving the inviso-strip ahead of the
defense checks; the residual reorder (modifiers before set_fighting) is inert.
Lock: `tests/integration/test_fight104_inviso_strip_before_parry.py` (2).

### OLC setter sweep (OLC_ACT-015..018)

The un-audited inline redit/oedit/medit per-field setters carried English
placeholder messages, leaked the set value (ROM emits bare "X set."), and — for
medit/oedit level & medit align — **non-ROM validation guards that rejected
valid ROM input** (behavioral, not cosmetic). All aligned to ROM verbatim
strings; guards removed. Established that `imm_olc.py` already reproduces ROM's
Spanish `"Sintaxis :"` strings, so the English placeholders were un-audited debt,
not a deliberate convention. Flipped 12 function rows PARTIAL/NEEDS-DEEP-AUDIT →
✅ FIXED.

## Version / tests

- `pyproject.toml`: 2.14.331 → **2.14.336**.
- Full suite: **6258 passed, 4 skipped, 0 failed** (159s parallel) — confirmed
  green after all iterations.
- 12 OLC_ACT function rows flipped ⚠️ PARTIAL / 🔄 NEEDS DEEP AUDIT → ✅ FIXED
  (redit heal/mana/room/sector; oedit level/weight/cost/material; medit
  level/align/hitroll/material). 1 new FIGHT row (FIGHT-104).

## Outstanding — concrete queue for iterations 8-15 (the loop can continue)

1. **aedit setters** (`aedit_security`/`aedit_vnum`/`aedit_lvnum`/`aedit_builder`,
   marked ⚠️ PARTIAL) — likely the same value-leak/placeholder/guard class as
   OLC_ACT-015..018. One coherent sweep (OLC_ACT-019). Verify each against
   `src/olc_act.c:825-978` first.
2. **oedit type/short/long, redit_clan/format/owner** — remaining inline setters
   (NEEDS DEEP AUDIT). Some need `string_append` (interactive editor) — skip
   those (redit_desc/oedit_long), do the simple ones.
3. **FIGHT-098 dedicated C-oracle scenario** — the diffshim binary builds (re-verified
   this session, `make -C src -f Makefile.diffshim diffshim` exit 0). Needs an
   OFF_AREA_ATTACK mob directive + a fled-but-still-fighting char (deferred with
   DB-005's `__mob_census`). Multi-commit harness extension.
4. **More combat recall-oracle probes** — the FIGHT-104 pattern paid off. Candidate
   surfaces: `update_pos` thresholds, `check_parry`/`check_dodge` internals,
   `one_hit` damage calc, weapon-skill `check_improve`. Read `src/fight.c` first.
5. **Recall-oracle on other high-traffic ✅ surfaces** — affect ticks (char_update
   affect expiry / "wears off" ordering), message delivery (INV-001).

## Deferred by design (unchanged)

DESC-001 (latent), OLC spell-name lookup (skill-by-index registry),
DB2-004/005 (theoretical multi-line fread), medit dice/AC string-storage
(OLC_ACT-010b).
