# Handoff — 2026-06-22 — Death auto-action differential harness

## Current Branch State

- Version: **2.14.208**
- Differential scenarios: **51 / 51 converge**, `KNOWN_DIVERGENCES` empty.
- Latest completed focus: FIGHT-079 PC corpse money + death `PLR_AUTOLOOT` /
  `PLR_AUTOGOLD` differential scenarios.

## What Changed

- FIGHT-079 is closed:
  - non-clan PC corpse: owner set, coins remain on PC.
  - clan PC corpse: owner `NULL`/`None`, half coins in corpse on ROM `> 1`,
    remainder stays on PC.

- New harness meta commands:
  - `__plr_autoloot=0|1`
  - `__plr_autogold=0|1`

- New scenarios:
  - `death_auto_gold`
  - `death_auto_loot`

- New fixed divergence:
  - **FINDING-040 / FIGHT-080**: Python death auto-loot/autogold now emits ROM
    `do_get` lines rather than `"You quickly gather the loot from the corpse."`.

## Verification Already Run

- Focused corpse suite before FIGHT-079 commit: 50 passed.
- Broader focused suite after auto-action work: 154 passed.
- `ruff check .` clean.
- `git diff --check` clean.

## Suggested Next Probe

Add differential coverage for death `PLR_AUTOSAC`, then `PLR_AUTOSPLIT` if the
harness gains a deterministic grouped-PC setup. Re-read ROM `src/fight.c:945-980`
and `src/act_obj.c:1838-1853` before changing behavior; the autosac branch has a
specific interaction with autoloot leaving treasure in the corpse.
