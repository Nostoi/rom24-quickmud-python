# Session Status — 2026-06-20 — Differential harness: death lifecycle + FIGHT-078

## Current State

- **Active focus**: Expanding the differential harness (`tools/diff_harness/`) —
  the only enumeration-*independent* parity oracle now that the per-file audit
  tracker is drained (`DIVERGENCE_CLASS_ROSTER.md` guardrail #3).
- **Last completed** (this session): authored the **`death_corpse_loot_sacrifice`**
  scenario on the zero-coverage death/corpse/loot/sacrifice surface. It surfaced a
  real engine divergence on first capture:
  - **FIGHT-078 / FINDING-038** — NPC `make_corpse` minted a money object on
    `gold > 0 or silver > 0`; ROM gates the NPC corpse's money on `ch->gold > 0`
    alone (`src/fight.c:1473`), so a silver-but-no-gold mob drops a phantom
    `"N silver coins"` object ROM never creates. Fixed → NPC gate is `gold > 0`.
  - **FIGHT-079** filed (⏸ deferred) — PC corpse drops full coins; ROM drops half
    (non-clan only). Higher blast radius, zero test coverage, not harness-exercised.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-20_DIFF_HARNESS_DEATH_LIFECYCLE.md](SESSION_SUMMARY_2026-06-20_DIFF_HARNESS_DEATH_LIFECYCLE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.203 |
| Tests | 6010 passing (4 skipped) |
| Differential scenarios | 46 / 46 converge (`KNOWN_DIVERGENCES` empty) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Differential harness widening |

## Next Intended Task

**Continue widening the differential harness.** Now-deplumbed targets (this
session confirmed the trainers exist and are `__mload`-able with zero plumbing):

- **Advancement — train / gain.** `__mload` midgaard 3007 (ACT_TRAIN) for
  `train str/hp/mana` + the no-arg session display; `__mload` newthalos 9500-9503
  (ACT_GAIN) for `gain convert` / `gain points` / `gain list`. All deterministic
  counter math (no RNG). Differential CONFIRM is more likely than catch (the
  surface is heavily audited) but it locks it. `practice <skill>` still needs a
  partial-skill shim meta — `make_test_char` skips `group_add`, so the default char
  knows no skills; add a `__learn_pct=<skill>=<pct>` meta or defer.
- **FIGHT-079** — PC corpse half-coin gate (`src/fight.c:1483-1495`). Own
  gap-closer commit; needs a PC-victim corpse-money test (the harness can't inspect
  the driver's own corpse).
- **Death lifecycle, deeper** — auto-loot / auto-gold needs a PLR-flag-set meta;
  the new scenario covers the manual corpse→get→sacrifice path only.

Method (reinforced): bracket spawns with `__seed`; set mob wealth explicitly
post-spawn (`__mob_gold`/`__mob_silver`) — boot-rolled wealth is NOT bit-matched
C⇄Python; capture per-scenario (`--scenario`), never `--all`; a divergence is a
FINDING (FINDINGS.md → `/rom-gap-closer` local or new INV-NNN cross-file → fix
Python/data, **never** overwrite the golden). Build/regen needs the shim
(`cd src && make -f Makefile.diffshim diffshim`; built).

Secondary / housekeeping (do NOT lead with these):
- `test_all_commands.py` `tap` alias false-positive (low).
- Cross-file INV probe / signed-math (class 7) — diminishing returns; fall back
  here only if harness work stalls.
- **Risk posture**: HIGH-blast-radius behavioral changes → file, don't fix (see
  FIGHT-079). Adding harness scenarios is read-only on the engine (test data only);
  a small engine fix (like FIGHT-078) is fine when impact is LOW and a guard test
  locks it.
