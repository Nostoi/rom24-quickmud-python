# Meta-Audit Taxonomy

> **Purpose**: the planning umbrella for cross-file parity audits.
> The per-file audit (`/rom-parity-audit`) is done. The cross-file
> invariants tracker captures one-off contracts. This doc captures
> **patterns of bug** that span multiple commits — each becomes its
> own dedicated audit doc and burn-down pass.

## TL;DR — Burn-Down Queue

Ordered by **suspected density** (per the user-confirmed priority rule).
Each row's audit produces one markdown file under `docs/parity/audits/`.
Numbers are *probes* until an audit replaces them with *measurements*.

| # | Class | Suspected density | Audit effort | Automation | Next-session deliverable |
|---|-------|-------------------|--------------|------------|--------------------------|
| 1 | BROADCAST_COVERAGE | ~130 commands; 15–25 likely gaps *(probe)* | session (4–6h) | manual + grep | `audits/BROADCAST_COVERAGE.md` (~130 rows, M ❌/⚠️) |
| 2 | ARITHMETIC_BOUNDARY | every `max(1, …)` / `min(cap, …)` / `clamp(…)` site *(probe)* | half-session (2–3h) | grep-scan | `audits/ARITHMETIC_BOUNDARY.md` (~30–60 sites) |
| 3 | GATE_CONSISTENCY | ~5–8 ROM guards × multi-site each *(probe)* | session (4–6h) | hybrid | `audits/GATE_CONSISTENCY.md` (~30–50 rows) |
| 4 | TRIGGER_CALL_SITE_MIGRATION | ~10–15 trigger types × call sites *(probe)* | half-session (2–3h) | manual | `audits/TRIGGER_CALL_SITES.md` (~15–25 rows) |
| 5 | LIFECYCLE_STAGING | uncertain; coordination invariants *(probe)* | session+ | manual | `audits/LIFECYCLE_STAGING.md` (count unknown) |
| 6 | DUPLICATE_IMPLEMENTATIONS | ~5–15 duplicates *(probe)* | 1–2h | grep-scan | `audits/DUPLICATE_IMPLEMENTATIONS.md` (5–15 rows) |
| 7 | PARALLEL_REPRESENTATIONS | mostly closed by INV-012/13/14 *(probe)* | 1h | manual | `audits/PARALLEL_REPRESENTATIONS.md` (small, closed-row record) |
| 8 | MATH_AND_RNG_CHANNEL | low density, mostly enforced *(probe)* | 1h | lint-candidate | `audits/MATH_RNG.md` + ruff rule sketch |

**Exception worth flagging**: #6 (DUPLICATE_IMPLEMENTATIONS) violates the
density-first rule but is *cheap-momentum* — and identifying duplicates
*before* running BROADCAST_COVERAGE means we audit the dispatcher-wired
copy, not the canonical one. Running #6 before #1 is a defensible
deviation; flagged here, not auto-applied.

## Why this taxonomy exists

The per-file audit (43 ROM C files, all P0/P1/P2 at 100%, P3 at 75%+)
validates **structural correspondence**: does Python have a function
with the same name and roughly the same logic as ROM? It cannot
validate **behavioral contracts** that span modules, call sites,
representations, or output channels.

The 20 commits from 2.9.0 → 2.9.20 are evidence: each closed a parity
gap the per-file audit had passed as 100%. They cluster into the eight
classes below. The cross-file invariants tracker
(`docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`) captures individual
INV-NNN contracts but doesn't *taxonomize* them — every INV is filed
reactively after a probe surfaces it. This doc is the proactive
counterpart: the audit doc per class enumerates *all* instances of
the pattern at once.

## How to use this doc

1. Read the TL;DR queue. Pick the top row that isn't done.
2. Jump to that class's detail section below.
3. The detail section gives you a rubric, an audit strategy, and a
   deliverable spec. Run a dedicated session producing the audit doc.
4. The audit doc is now the spec for a burn-down session: one
   gap-closer commit per ❌/⚠️ row (use the existing `rom-gap-closer`
   skill).
5. When the audit doc is empty of ❌/⚠️, mark the queue row done.

The cross-file invariants tracker continues to receive new INVs for
**single-instance** contracts that don't fit any class. A
single-instance is *promoted to a class* when (a) the failure mode
would plausibly recur in code not yet written, (b) a second instance
appears in the wild, or (c) the bug is architecture-level rather than
incidental.

## Bug-class detail

### Class 1: BROADCAST_COVERAGE

**Summary**: Python `def do_X(...) -> str` returns the TO_CHAR
equivalent only. ROM `void do_X (...)` emits 1–4 `act()` calls per
outcome (TO_CHAR / TO_VICT / TO_NOTVICT / TO_ROOM). The non-TO_CHAR
broadcasts must be made via explicit `broadcast_room()` /
`room.broadcast()` / `messages.append()` — easy to omit silently.

**Evidence**:
- 2.9.18 — `do_buy` missing `$n buys $p.` TO_ROOM.
- 2.9.19 — `do_follow → add_follower` missing TO_VICT/TO_CHAR pair.
- 2.9.20 — `do_group` missing TO_VICT + TO_NOTVICT on add and remove.
- INV-016 — spell-damage path missing position-transition broadcast.

**Detection rubric**:
1. Enumerate every `def do_*` under `mud/commands/`.
2. Locate the ROM C citation in the docstring or grep `src/`.
3. Count `act(...)` / `act_new(...)` in the ROM function, bucketed
   by terminal arg: TO_VICT, TO_NOTVICT, TO_ROOM. Ignore TO_CHAR.
4. Count `broadcast_room` / `room.broadcast` / `messages.append`
   on non-`char` recipients in the Python function (follow helpers
   into `mud/net/protocol.py` / `mud/utils/act.py` as needed).
5. Bucket: ✅ MATCH / ⚠️ PARTIAL / ❌ MISSING per the count diff.

**Audit strategy**: manual + grep. The enumeration is mechanical; the
ROM-function read and Python-counterpart count are manual but bounded
(2–5 minutes per command at steady state).

**Deliverable**: `docs/parity/audits/BROADCAST_COVERAGE.md`. Schema:
`# | Command | Python entry | ROM C ref | TO_VICT | TO_NOTVICT | TO_ROOM | Status | Gap ID | Notes`.
Counts shown as `ROM/Python`. Worked sketch already exists at
`docs/parity/COMMAND_BROADCAST_COVERAGE_AUDIT.md` (5 worked rows);
the full audit promotes that draft into the audits/ directory.

**Risks**: helper functions (`_broadcast`, `act_to_room`) can hide
broadcasts behind one layer. Rubric must follow helpers, not just
literal-string-match `act_format` calls.

---

### Class 2: ARITHMETIC_BOUNDARY

**Summary**: Defensive floors that ROM doesn't have — `max(1, level // 2)`,
`min(cap, x)`, `clamp(0, x, max)`. Each is "correct in isolation" but
hides a parity divergence. ROM's raw integer math sometimes legitimately
produces 0 / negative / overflow; Python's floor masks the symptom.

**Evidence**:
- 2.9.15 — `group_gain` NPC level floor: `max(1, level // 2)` inflated
  XP for level-1 NPC contributions by treating their division-floor
  zero as one. ROM emits 0; Python emitted 1, ~10% XP inflation in
  low-level groups.

**Detection rubric**:
1. `grep -rn "max(1, \|max(0, \|min(.*[,)]\|clamp(" mud/` to find
   defensive-floor sites.
2. For each hit, locate the ROM C formula. If ROM doesn't have an
   equivalent guard (no `UMAX(1, ...)`, no `if (x < 1) x = 1;` before
   the formula), the Python guard is divergent.
3. Bucket: ✅ MATCH (ROM has the floor) / ❌ MISSING (Python guards
   but ROM doesn't) / N/A (intentional divergence, cite
   `docs/divergences/`).

**Audit strategy**: grep-scan. Mechanical enumeration; the
ROM-side check is per-site but fast (≤2 minutes each).

**Deliverable**: `docs/parity/audits/ARITHMETIC_BOUNDARY.md`. Schema:
`# | Python site | Guard | ROM C ref | ROM has guard? | Status | Gap ID | Notes`.

**Risks**: some Python guards exist for *implementation* safety (e.g.
preventing ZeroDivisionError) not parity. Each ❌ candidate must be
read in context before filing — guards that prevent crashes ROM
doesn't have are sometimes justified.

---

### Class 3: GATE_CONSISTENCY

**Summary**: A ROM guard (`!IS_NPC`, `can_see`, `IS_AFFECTED(... CHARM)`,
`position == default_pos`) exists at one Python call site but not at
all sibling sites that ROM gates identically.

**Evidence**:
- 2.9.17 — `do_say` had the `!IS_NPC(ch)` SPEECH gate; `do_tell` was
  missing it. The same gate also needs to exist at every future
  agent-driven or scripted-mob path.
- HPCNT-001 — the trigger's firing-rate gate (once per pulse) needed
  to be enforced at every site that could call it.

**Detection rubric**:
1. Enumerate ROM guards worth checking: `!IS_NPC(ch)`, `can_see`,
   `can_see_obj`, `IS_AFFECTED(ch, AFF_CHARM)`, `position`-floor
   checks, `IS_IMMORTAL`, `IS_TRUSTED`. Limit set: ~5–8.
2. For each guard, grep ROM for `if (!IS_NPC` / `if (can_see` etc.,
   listing every call site.
3. For each Python equivalent, verify the same guard exists.
4. Bucket: ✅ MATCH / ❌ MISSING / N/A (intentional).

**Audit strategy**: hybrid. The ROM-side enumeration is grep-scan;
the Python-side check is manual per call site (~3–5 minutes each).

**Deliverable**: `docs/parity/audits/GATE_CONSISTENCY.md`. Schema:
`# | Guard | ROM site | Python site | Python has guard? | Status | Gap ID | Notes`.

**Risks**: ROM sometimes uses *implicit* guards (e.g. caller already
checked `can_see`). Auditor must read the calling context, not just
the function body.

---

### Class 4: TRIGGER_CALL_SITE_MIGRATION

**Summary**: A mob/object trigger is wired into a fallback or
auxiliary Python code path instead of the canonical ROM call site.
The trigger fires (so probes against the call-site directly may
pass), but it fires at the wrong frequency or in the wrong context.

**Evidence**:
- HPCNT-001 (2.9.11) — `mp_hpcnt_trigger` was wired into the
  `_apply_damage` path. ROM fires it from `violence_tick` →
  `multi_hit` post-attack site, once per pulse. Python's wiring made
  it fire N+1 times per multi_hit and on spell-damage paths where
  ROM doesn't fire it at all.

**Detection rubric**:
1. Enumerate ROM trigger types: GREET, ALL_GREET, SPEECH, GIVE,
   BRIBE, ENTRY, EXIT, FIGHT, DEATH, HPCNT, ACT, RANDOM, KILL,
   DELAY (and the object-side equivalents). Limit set: ~12–15.
2. For each trigger type, locate the ROM call site (`mp_*_trigger`).
   Note the *function* that calls it and the *condition* of the call.
3. For each Python equivalent, verify the trigger is wired at the
   matching call site and condition.
4. Bucket: ✅ MATCH / ⚠️ PARTIAL (right site, wrong condition) /
   ❌ MISSING (wrong site or absent).

**Audit strategy**: manual. Each trigger needs a careful
ROM-vs-Python call-graph comparison; not automatable.

**Deliverable**: `docs/parity/audits/TRIGGER_CALL_SITES.md`. Schema:
`# | Trigger | ROM call site | ROM condition | Python call site | Python condition | Status | Gap ID | Notes`.

**Risks**: triggers can also fire from non-obvious paths (e.g.
DEATH from `raw_kill` vs `extract_char`). The ROM-side
enumeration must be thorough.

---

### Class 5: LIFECYCLE_STAGING

**Summary**: A coordination contract spanning modules — tick
ordering, iteration safety during mutation, state cleanup that must
happen in a specific sequence — diverges between ROM and Python.

**Evidence**:
- INV-015 (2.9.7) — affect-tick lifecycle: expired ROM-canonical
  affects had to route through `affect_remove` to fire the right
  cleanup sequence.
- INV-017 (2.9.13) — tick iteration safety: mutating a list mid-loop
  during `char_update` could skip entries.
- INV-019 (2.9.16) — position promotion on heal: heal handlers +
  regen tick + `update_pos` all agree silently by construction.
- 2.9.12 — `die_follower` had to reset the leader chain to prevent
  dangling references after extraction.

**Detection rubric**: harder than the previous classes — no single
grep pattern. Approach:
1. List every per-tick or per-pulse update in `mud/game_loop.py`
   (`char_update`, `obj_update`, `aggr_update`, `area_update`,
   `violence_update`, `weather_update`).
2. For each, walk the ROM equivalent (`update.c`, `act_move.c`) and
   identify (a) iteration discipline, (b) call ordering, (c)
   cleanup-on-extract paths.
3. Compare. Any divergence is a candidate.
4. Bucket: ✅ MATCH / ⚠️ PARTIAL / ❌ MISSING.

**Audit strategy**: manual, multi-session if done thoroughly. May
benefit from being split into sub-audits per tick path.

**Deliverable**: `docs/parity/audits/LIFECYCLE_STAGING.md`. Schema:
`# | Tick path | ROM ref | Python ref | Property | ROM behavior | Python behavior | Status | Gap ID`.

**Risks**: high cost-per-row. Consider scoping to the highest-traffic
tick paths first (`char_update`, `violence_update`) and deferring
weather/area to a later session.

---

### Class 6: DUPLICATE_IMPLEMENTATIONS

**Summary**: Two `def`s for the same primitive exist in different
modules. The command dispatcher routes one; the audit validated
the other; the broadcasts/gates in the validated copy never reach
production.

**Evidence**:
- 2.9.8 — dead `Character.affect_remove` parallel to canonical
  affect handlers in `mud/affects/`.
- 2.9.19 / 2.9.20 — `add_follower` / `stop_follower` / `is_same_group`
  in `mud/characters/follow.py` (canonical, has broadcasts) vs
  `mud/commands/group_commands.py` (silent, dispatcher-wired).
  Closed by adding broadcasts to the silent copies; consolidation
  deferred to its own session.

**Detection rubric**:
1. `grep -rn "^def " mud/ | awk '{print $NF}' | sort | uniq -c |
   awk '$1 > 1'` to enumerate names with >1 `def` site.
2. For each multi-def name, filter out non-primitives (`__init__`,
   `__str__`, dunder methods, intentionally-overloaded helpers).
3. For each genuine duplicate, identify which copy the dispatcher
   or high-traffic call sites route through.
4. Bucket: ✅ MATCH (copies are byte-identical or one delegates to
   the other) / ⚠️ PARTIAL (agree on happy path, differ on edge) /
   ❌ MISSING (diverge meaningfully on a parity-sensitive path).

**Audit strategy**: grep-scan. Mechanical enumeration; comparison
is manual but bounded (<20 candidates expected).

**Deliverable**: `docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md`.
Schema: `# | Primitive | File A | File B | Dispatcher-wired? |
Divergence summary | Status | Gap ID | Consolidation plan`.

**Risks**: mass consolidation can break dispatcher wiring silently.
Each ❌ row's fix should be its own commit with a regression test.

---

### Class 7: PARALLEL_REPRESENTATIONS

**Summary**: Two data shapes coexist for one concept. Code paths
handle one shape but not the other, leading to silent divergence
when the wrong shape flows through.

**Evidence**:
- INV-012 (2.9.0–2.9.2) — `ObjectData` vs `Object`; `Object.location`
  field vs ROM `in_room` / `carried_by` / `in_obj`.
- INV-014 (2.9.3) — registry membership: not every spawn path
  registered the object.
- INV-013 (2.9.4–2.9.5) — `carried_by` symmetry: `equip_object` set
  it but `remove_object` didn't clear it.
- INV-018 (2.9.14) — raw `AffectData` expiry didn't emit `msg_off`
  while ROM-canonical affects did.

**Detection rubric**:
1. Enumerate Python classes/types that have a documented "canonical"
   version and a legacy or alternative shape: `Object`/`ObjectData`,
   `AffectData` raw vs ROM-canonical, `Character` vs `MobInstance`
   (where they diverge).
2. For each, grep for `isinstance(x, LegacyShape)` and
   `hasattr(x, "legacy_attr")` in `mud/`.
3. Each isinstance/hasattr branch is a candidate; verify both
   branches agree on the contract.

**Audit strategy**: manual. Mostly closed by INV-012/13/14, so this
audit is largely a closed-row record of "what was consolidated and
which scattered call sites still reach a legacy shape (if any)."

**Deliverable**: `docs/parity/audits/PARALLEL_REPRESENTATIONS.md`.
Schema: `# | Concept | Canonical | Legacy | Open sites | Status | Notes`.

**Risks**: low — most instances are closed. Audit may be
mostly-empty; that's fine, it's a pinning record.

---

### Class 8: MATH_AND_RNG_CHANNEL

**Summary**: Python uses `//`, `%`, `random.*`, or built-in math
where ROM uses `c_div`, `c_mod`, `rng_mm`, or specific integer
semantics. AGENTS.md already mandates the ROM equivalents; this
audit confirms enforcement.

**Evidence**: AGENTS.md "ROM Parity Rules (CRITICAL)" section
mandates `rng_mm.number_*` and `c_div`/`c_mod`. Historical
violations have been fixed ad hoc; this audit closes the loop with
a structured check.

**Detection rubric**:
1. `grep -rn "import random\|from random\|random\." mud/` —
   any hit outside `mud/utils/rng_mm.py` is a candidate.
2. `grep -rn " // \| % " mud/` — narrow to combat/affect/damage
   paths (where integer semantics matter for parity); pure-Python
   indexing/slicing `//` is fine.
3. For each candidate, verify it's not a legitimate use (e.g.
   list-slice index, percentage display, non-parity-sensitive math).

**Audit strategy**: lint-candidate. The grep can be promoted to a
ruff custom rule with allowlists (e.g. `# noqa: PARITY001` for
deliberate uses). Manual review for each first-pass hit; lint rule
then prevents regressions.

**Deliverable**: `docs/parity/audits/MATH_RNG.md` — initial scan
results + sketch of the proposed ruff rule. The ruff rule itself is
implemented in its own session.

**Risks**: too-broad lint rule could swamp the codebase with false
positives. The allowlist mechanism is essential.

---

## Scope limits — what this taxonomy does NOT cover

The 8-class audit catches **patterns** that can be enumerated
statically. It does not catch:

1. **Subtly-wrong constants/formulas.** A function has the right
   shape and the right ROM citation, but a magic number is off by
   one. The per-file audit and class audit both pass; only
   ROM-vs-Python value diff catches it.
2. **Combinatorial state interactions.** Behaviors that emerge from
   specific play sequences ("charm a mob, drag to a non-PK room,
   attack a player while invisible…"). The state space cannot be
   enumerated.
3. **Missing ROM features we forgot to port.** Whole commands or
   subsystems absent from `mud/`. Per-file audit only checks files
   we know about.
4. **ROM bugs we accidentally fixed.** Parity is bug-for-bug. If
   ROM has a quirk and Python has a "correct" version, that's a
   parity gap even though it's "better."

Closing these requires **Layer 2** — see below.

## Layer 2: bug-for-bug parity

The natural next investment after the audit burn-down is a
**side-by-side execution harness**: compile the original ROM 2.4b6
C source, drive both engines with identical scripted player input
(same seed, same area, same commands), and diff outputs every
tick. Every diff is either a parity bug or a documented
intentional divergence (`docs/divergences/`). Property-based tests
over command sequences scale the comparison.

This is out of scope for any audit in the queue above. It changes
how the project works day-to-day (every Python change runs against
the diff harness in CI) and should be planned as its own
multi-session project once the static-audit burn-down is done.

## Relationship to existing trackers

- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — per-file
  audit, complete. Untouched.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — per-incident
  INV-NNN log. This taxonomy is the **parent** taxonomy; each
  INV-NNN row gets tagged with one of the 8 classes (or "single-
  instance" if none fit). New audit docs cite their owning class.
- `docs/parity/audits/<CLASS>.md` — produced by this taxonomy.
  One per class. Each is a working spec for a burn-down session.

## Open questions

1. **Where does `docs/parity/COMMAND_BROADCAST_COVERAGE_AUDIT.md`
   live now?** It was drafted as a sketch before this taxonomy
   existed. It should move to `docs/parity/audits/` and be the
   starting point for the BROADCAST_COVERAGE class audit.
2. **Should LIFECYCLE_STAGING be split?** It's the highest-effort
   class with the most uncertain density. May benefit from being
   broken into per-tick-path sub-audits (`char_update`,
   `violence_update`, weather/area).
3. **Density estimates are guesses.** The first audit run for each
   class will replace probes with measurements. Re-prioritize the
   queue after the first 2–3 audits to reflect actual hit rates.
4. **Burn-down cadence.** Once an audit doc has N ❌ rows, how many
   gap-closer commits per session? Current pattern is one per
   session ending with a push; if a class has 20 rows, that's 20
   sessions. Cluster them.
