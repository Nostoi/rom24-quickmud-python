# Session Summary — 2026-05-26 — INV tracker consolidation (2.9.41)

## Scope

Trim the cross-file invariants tracker from 25/~20 enforced rows back
toward the AGENTS.md soft budget (~20) by merging documented dual
pairs. The merge is docs-only — each retired row's enforcement test
keeps running under the merged row, and no Python is touched.

## Outcomes

### INV-014 + INV-021 → INV-014 OBJECT-REGISTRY-LIFECYCLE — ✅ MERGED

Both halves pinned the same `mud.models.obj.object_registry`
contract — creation (membership-on-create) and extract (recursive
drain before parent removal). Merged row carries both ROM mechanism
descriptions, both Python enforcement halves (creation + extract),
and both test files (`test_inv014_object_registry_membership.py`,
`test_inv021_object_extract_recursive.py`).

### INV-015 + INV-018 → INV-015 AFFECT-EXPIRY-LIFECYCLE — ✅ MERGED

Both halves pinned the same `mud/affects/engine.py:tick_spell_effects`
per-affect expiry loop — stat-mod un-apply (via `affect_remove` →
`affect_modify(FALSE)`) and wear-off message emission (via
`_lookup_raw_affect_wear_off` for raw AffectData, `effects[name].wear_off_message`
for spell-effects-managed entries). Merged row keeps both test files
(`test_inv015_affect_tick_lifecycle.py`, `test_inv018_wear_off_message_for_raw_affect.py`).

### INV-010 + INV-023 → INV-010 ROOM-PEOPLE-COHERENCE — ✅ MERGED

Both halves pinned the same `Room.add_character` / `Room.remove_character`
mutation pair — bidirectional coherence (every `ch.in_room == R` lives
in `R.people`, vice versa) and area-counter accounting (`area.nplayer`
increment/decrement, `area.empty` reset, `area.age` reset). Merged
row keeps both test files (`test_inv010_room_people_coherence.py`,
`test_inv023_area_nplayer_coherence.py`).

### INV-001 + INV-002 — NOT merged

The 2.9.39 tracker footer documented INV-001 + INV-002 as
"message-delivery duals," but a re-read of the rows shows they
pin unrelated contracts:

- **INV-001 SINGLE-DELIVERY**: `_push_message` returns after async
  send when `connection` exists — broadcast routing.
- **INV-002 PROMPT-CLAMP**: `mud/utils/prompt.py` clamps display
  to `max(0, hit)` after `raw_kill` clamps `hit >= 1` — display
  formatting.

No shared enforcement point. Merge would lose a distinct contract
and dilute the precedent. Left as separate rows.

### Retired IDs section added

New "Retired IDs (consolidated)" subsection between the active
invariants table and the "Stale-row footnotes" section. Each
retired ID (INV-018, INV-021, INV-023) gets a forward pointer to
its merged row plus a note that the original enforcement test
still runs. This keeps historical CHANGELOG entries and commit
messages resolvable without re-numbering anything.

## Files Modified

- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — three merged rows
  in the active table; three retired-ID stubs in new section;
  maintenance footer updated to reflect 22/~20 budget and the new
  consolidation rationale.
- `CHANGELOG.md` — 2.9.41 section.
- `pyproject.toml` — 2.9.40 → 2.9.41.
- `docs/sessions/SESSION_STATUS.md` — overwritten to 2.9.41 snapshot.

## Test Status

All 22 enforcement tests for the six affected IDs still pass:

- `test_inv010_room_people_coherence.py` — 6/6 ✅
- `test_inv014_object_registry_membership.py` — 8/8 ✅
- `test_inv015_affect_tick_lifecycle.py` — 2/2 ✅
- `test_inv018_wear_off_message_for_raw_affect.py` — 2/2 ✅
- `test_inv021_object_extract_recursive.py` — 2/2 ✅
- `test_inv023_area_nplayer_coherence.py` — 2/2 ✅

This is docs-only consolidation — no Python touched, no broader
suite re-run needed. The 2.9.40 baseline (2215 + 2534 = 4749 passed,
4 skipped) carries forward unchanged.

## Next Steps

1. **Continue probe-then-scope at 22/~20**. Recent INV rows
   (INV-023, INV-024, INV-025) each surfaced real production bugs,
   so the methodology is still earning its keep. Soft cap of ~20 is
   advisory; we're not under pressure to consolidate further unless
   a new candidate brings the count back above 25 without a real
   bug.
2. **INV-025 follow-up sweep** (independent track): wire
   `mp_act_trigger_room` into remaining ROM act() callsites
   (do_give, do_drop, do_get, do_put, do_sacrifice, equipment
   commands, position-transition broadcasts). One callsite per
   commit. The contract is already locked at the emote site; the
   sweep widens coverage but cannot regress what INV-025 enforces.
3. **Future consolidation candidates** (don't merge yet — each
   still pins a distinct contract): INV-016 / INV-019 (position
   transition broadcast / silent promotion-on-heal duals on
   `update_pos`); INV-006 / INV-009 (fighting-pointer coherence
   after death / registry-disconnect cleanup on `character_registry`
   membership transitions). Either would free one slot if the
   budget creeps back above 25.
