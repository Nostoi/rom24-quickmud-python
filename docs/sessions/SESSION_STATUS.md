# Session Status — 2026-06-02 — INV-025 socials `$n` PERS class CLOSED + TO_NOTVICT bug (2.12.56)

## Current State

- **Active mode**: cross-file invariants. **The INV-025 socials `$n` PERS
  class is now CLOSED** — the last room-broadcast `$n`-baking mechanism in
  `mud/commands/`. `mud/commands/socials.py:perform_social` rendered every
  social line via `expand_placeholders` + `room.broadcast(exclude=char)`: no
  per-recipient `$n`/`$N` PERS masking (an invisible socialer leaked its name to
  unaided witnesses, INV-027), no TRIG_ACT to NPC bystanders (INV-025), and — a
  genuine behavioral bug riding along — it delivered `others_found` to the
  **victim**, though ROM `act(others_found, ch, NULL, victim, TO_NOTVICT)`
  (`src/interp.c:648`) excludes the victim (who must receive only `vict_found`,
  `TO_VICT`).
- **This session — one commit (local, NOT pushed):**
  - **2.12.56 / `145a87ad`** — converted the social room broadcasts
    (`others_no_arg`/`others_auto` TO_ROOM; `others_found` TO_NOTVICT with
    `exclude=victim`) to the shared `act_to_room` helper, and the directed lines
    (`char_*` TO_CHAR, `vict_found` TO_VICT, the NPC auto-react echo/slap, and
    the not-found literal) to a new `socials._act_to_char` helper (per-recipient
    PERS via `act_format` + single-delivery `push_message` + TRIG_ACT to NPC
    recipients), mirroring ROM `act_new` (`src/comm.c:2230-2385`).
    `expand_placeholders` is retained for its other production caller
    (`commands/imc.py`). New test
    `tests/integration/test_inv025_socials_pers_sweep.py` (invisible-actor
    masking + TO_NOTVICT victim-exclusion); flipped
    `test_socials.py::test_social_with_target_excludes_actor_from_broadcast`
    from the bug-encoding `len(bob.messages) == 2` to ROM-correct
    `== ["Alice smiles at you."]`. Carries the version bump +
    CHANGELOG/tracker updates.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-02_INV025_SOCIALS_PERS.md](SESSION_SUMMARY_2026-06-02_INV025_SOCIALS_PERS.md)
  (prior: [INV025_COMMAND_BROADCAST_DOORS_PERS](SESSION_SUMMARY_2026-06-02_INV025_COMMAND_BROADCAST_DOORS_PERS.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.56 |
| Tests | **full suite green: 5308 passed, 4 skipped** (`pytest`, ~96s parallel) |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 25 enforced |
| Open correctness gaps | **None known in the INV-025 `$n`-broadcast class** — every `mud/commands/` room-broadcast that bakes `$n` is now converted to per-recipient PERS + TRIG_ACT. |

## Next Intended Task

The INV-025 `$n` room-broadcast sweep across `mud/commands/`,
`mud/combat/`, `mud/world/`, `mud/skills/`, and now socials is
**complete**. Remaining cross-file-invariants candidates (probe-then-scope):

1. **Mob script trigger ordering** — TRIG_ENTRY / TRIG_GREET / TRIG_GIVE /
   TRIG_BRIBE fire-order vs ROM (`src/mob_prog.c`, `mob_cmds.c`).
2. **Position transitions** — sleeping/resting/sitting/standing/fighting edges.
3. **Group / follower chains** — `add_follower`/`die_follower`/`stop_follower`.

Method: pick a candidate not yet covered by an INV row, run a 5-minute probe
(read ROM C contract → read Python equivalent → write one failing test for the
contract), then either close as a gap (single commit) or file as the next free
INV-NNN.

> **Push note:** everything through 2.12.48 is on `master`; **2.12.49–56** are
> committed locally but **NOT yet pushed**. README/CHANGELOG/version all reflect
> 2.12.56. GitNexus reindex was kicked off after this commit.
